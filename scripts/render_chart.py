#!/usr/bin/env python3
"""Render MCP chart/analysis responses as self-contained offline HTML."""

import argparse
import json
from pathlib import Path


def render(payload, output):
    if payload.get("isError"):
        raise ValueError("MCP_ERROR_RESPONSE")
    payload = payload.get("structuredContent") or payload
    if "content" in payload and "chart_config" not in payload:
        payload = json.loads(
            next(c["text"] for c in payload["content"] if c.get("type") == "text")
        )
    charts = payload.get("charts") or ([payload] if "chart_config" in payload else [])
    if not charts:
        raise ValueError("NO_CHART_CONFIG: call generate_chart first")
    document = {
        "charts": charts,
        "report": payload.get("report"),
        "run_id": payload.get("run_id"),
    }
    data = (
        json.dumps(document, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    assets = Path(__file__).resolve().parents[1] / "assets"
    template = (assets / "chart_viewer.html").read_text()
    engine = (assets / "echarts.min.js").read_text()
    html = template.replace("/*__ECHARTS__*/", engine).replace(
        "/*__PAYLOAD__*/null", data
    )
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with output.open("x", encoding="utf-8") as handle:
        output.chmod(0o600)
        handle.write(html)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        help="JSON from generate_chart or completed get_analysis",
    )
    parser.add_argument(
        "--output", required=True, help="New HTML path, normally in workspace/"
    )
    args = parser.parse_args()
    path = Path(args.input)
    if path.stat().st_size > 10 * 1024 * 1024:
        parser.error("INPUT_TOO_LARGE")
    try:
        output = render(json.loads(path.read_text()), args.output)
    except FileExistsError:
        parser.error("OUTPUT_EXISTS: choose a new filename")
    except (ValueError, KeyError, StopIteration):
        parser.error("INVALID_CHART_RESPONSE")
    print(output)


if __name__ == "__main__":
    main()
