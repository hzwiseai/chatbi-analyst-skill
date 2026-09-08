"""Credentials stay in client code; only business data reaches stdout/tools."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import uuid

import httpx
from dotenv import dotenv_values
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MUTATIONS = {"text2sql", "execute_query", "start_analysis", "resume_analysis"}
TOOLS = {
    "get_connection_info",
    "list_resources",
    "get_semantic_context",
    "text2sql",
    "execute_query",
    "get_query_result",
    "generate_chart",
    "start_analysis",
    "get_analysis",
    "resume_analysis",
    "cancel_analysis",
}


class ClientError(Exception):
    pass


def config_dir():
    return Path(
        os.getenv("CHATBI_CONFIG_DIR", str(Path.home() / ".config" / "chatbi-mcp"))
    )


def local_connection_config():
    """Read only the explicit config or this portable Skill's .env, never cwd."""
    explicit = os.getenv("CHATBI_ENV_FILE")
    skill_dir = Path(__file__).resolve().parents[2]
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ClientError("ENV_FILE_NOT_FOUND")
    elif (skill_dir / "SKILL.md").is_file():
        path = skill_dir / ".env"
    else:
        return {}
    # Passwords can contain literal ${...}; never interpolate or execute .env.
    values = dotenv_values(path, interpolate=False)
    return {
        key: value
        for key, value in values.items()
        if key in {"CHATBI_SERVER_URL", "CHATBI_USERNAME", "CHATBI_PASSWORD"}
        and value is not None
    }


def secure_write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@dataclass
class Connection:
    url: str
    username: str
    password: str

    def __post_init__(self):
        parts = urlsplit(self.url)
        local = parts.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            (parts.scheme != "https" and not (parts.scheme == "http" and local))
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
        ):
            raise ClientError("INVALID_SERVER_URL")
        self.url = self.url.rstrip("/")
        if not self.username or not self.password:
            raise ClientError("CONFIGURATION_REQUIRED")

    @property
    def fingerprint(self):
        return hashlib.sha256((self.url + "\n" + self.username).encode()).hexdigest()

    @classmethod
    def load(cls):
        local = local_connection_config()
        try:
            config = json.loads((config_dir() / "config.json").read_text())
        except FileNotFoundError:
            config = {}
        url = os.getenv(
            "CHATBI_SERVER_URL", local.get("CHATBI_SERVER_URL", config.get("url", ""))
        )
        username = os.getenv(
            "CHATBI_USERNAME", local.get("CHATBI_USERNAME", config.get("username", ""))
        )
        password = os.getenv(
            "CHATBI_PASSWORD", local.get("CHATBI_PASSWORD", config.get("password", ""))
        )
        return cls(url, username, password)


class ChatBIClient:
    def __init__(self, connection: Connection, http_factory=None):
        self.connection = connection
        self.lock = asyncio.Lock()
        self.credential = ""
        self.expires_at = 0.0
        self.http_factory = http_factory or (
            lambda: httpx.AsyncClient(
                timeout=30, follow_redirects=False, trust_env=False
            )
        )

    async def credential_for_request(self):
        async with self.lock:
            if self.credential and self.expires_at > time.time() + 30:
                return self.credential
            async with self.http_factory() as http:
                login = await http.post(
                    self.connection.url + "/api/mcp/login",
                    json={
                        "username": self.connection.username,
                        "password": self.connection.password,
                    },
                )
                if login.status_code != 200:
                    raise ClientError("LOGIN_FAILED")
                data = login.json()
                if data.get("protocol_version") != "1":
                    raise ClientError("INCOMPATIBLE_SERVER")
                self.credential = data["session_credential"]
                self.expires_at = time.time() + int(data["expires_in_seconds"])
            return self.credential

    def httpx_factory(self, headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            auth=auth,
            follow_redirects=False,
            trust_env=False,
        )

    @asynccontextmanager
    async def session(self):
        credential = await self.credential_for_request()
        async with self.httpx_factory(
            headers={"Authorization": "Bearer " + credential},
            timeout=httpx.Timeout(360),
        ) as http:
            async with streamable_http_client(
                self.connection.url + "/mcp/chatbi", http_client=http
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    async def list_tools(self):
        async with self.session() as session:
            tools = (await session.list_tools()).tools
            return [t for t in tools if t.name in TOOLS]

    async def call(self, name, arguments):
        if name not in TOOLS:
            raise ClientError("UNKNOWN_TOOL")
        if any(
            k in arguments
            for k in (
                "user_id",
                "org_id",
                "role",
                "session_credential",
                "password",
                "server_url",
                "authorization",
            )
        ):
            raise ClientError("IDENTITY_ARGUMENT_FORBIDDEN")
        arguments = dict(arguments)
        if name in MUTATIONS:
            arguments.setdefault("request_id", uuid.uuid4().hex)
        # Never blindly retry tool calls: they may already have executed.
        async with self.session() as session:
            return await session.call_tool(name, arguments)

    async def disconnect(self):
        if not self.credential:
            return False
        credential = self.credential
        async with self.http_factory() as http:
            response = await http.delete(
                self.connection.url + "/api/mcp/session",
                headers={"Authorization": "Bearer " + credential},
            )
            if response.status_code != 200:
                raise ClientError("DISCONNECT_FAILED")
        self.credential, self.expires_at = "", 0
        return True
