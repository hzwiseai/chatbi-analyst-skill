from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys

from .client import ChatBIClient, Connection, ClientError, config_dir, secure_write


async def serve(client):
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server

    server = Server("chatbi")

    @server.list_tools()
    async def list_tools():
        return await client.list_tools()

    @server.call_tool()
    async def call_tool(name, arguments):
        try:
            return await client.call(name, arguments)
        except Exception:
            # No traceback/URLs/headers from the HTTP transport in tool content.
            raise ValueError(
                "CHATBI_CONNECTION_FAILED; run chatbi-mcp configure to reconnect"
            ) from None

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


async def run(args):
    if args.command == "configure":
        connection = Connection(
            input("服务器地址 [http://localhost:5390]：").strip()
            or "http://localhost:5390",
            input("用户名：").strip(),
            getpass.getpass("密码："),
        )
        client = ChatBIClient(connection)
        result = await client.call("get_connection_info", {})
        if result.isError:
            raise ClientError("CONNECTION_CHECK_FAILED")
        secure_write(
            config_dir() / "config.json",
            {
                "url": connection.url,
                "username": connection.username,
                "password": connection.password,
            },
        )
        return {"status": "configured", "username": connection.username}
    client = ChatBIClient(Connection.load())
    if args.command == "serve":
        await serve(client)
        return None
    if args.command == "disconnect":
        revoked = await client.disconnect()
        return {"status": "disconnected" if revoked else "no_active_session"}
    if args.command == "list-tools":
        return {"tools": [t.model_dump(mode="json") for t in await client.list_tools()]}
    if args.command == "doctor":
        result = await client.call("get_connection_info", {})
    else:
        arguments = json.loads(args.args_json)
        if not isinstance(arguments, dict):
            raise ClientError("ARGUMENTS_MUST_BE_OBJECT")
        result = await client.call(args.tool, arguments)
    return result.model_dump(mode="json")


def main():
    parser = argparse.ArgumentParser(
        description="ChatBI MCP client; credentials never belong in tool arguments."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("configure", "doctor", "disconnect", "list-tools"):
        commands.add_parser(command)
    serving = commands.add_parser("serve")
    serving.add_argument("--transport", choices=["stdio"], default="stdio")
    call = commands.add_parser("call")
    call.add_argument("tool")
    call.add_argument("--args-json", default="{}")
    try:
        result = asyncio.run(run(parser.parse_args()))
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, default=str))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        code = str(exc) if isinstance(exc, ClientError) else "CHATBI_CONNECTION_FAILED"
        print(
            json.dumps(
                {
                    "error": code,
                    "action": "Check local configuration with chatbi-mcp configure",
                }
            ),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
