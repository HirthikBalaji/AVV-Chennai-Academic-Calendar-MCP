"""
Entry point for Amrita Vishwa Vidyapeetham, Chennai Academic Calendar AY2026-27 Server.
Supports both MCP Server mode (stdio / SSE) and FastAPI OpenAPI REST API mode.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uvicorn
import yaml

from fastapi_app import create_app
from mcp_server import create_mcp_server


def export_openapi_specs(output_dir: str = ".") -> None:
    """Exports openapi.json and openapi.yaml to the specified directory."""
    app = create_app()
    schema = app.openapi()

    json_path = os.path.join(output_dir, "openapi.json")
    yaml_path = os.path.join(output_dir, "openapi.yaml")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"Exported OpenAPI JSON specification to: {os.path.abspath(json_path)}")

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(schema, f, sort_keys=False)
    print(f"Exported OpenAPI YAML specification to: {os.path.abspath(yaml_path)}")


def build_unified_fastapi_app():
    """
    Constructs FastAPI app with mounted MCP SSE transport.
    Provides REST endpoints, OpenAPI docs (/docs, /redoc, /openapi.json),
    and MCP SSE transport (/sse, /messages).
    """
    app = create_app()
    mcp = create_mcp_server()

    # Disable host checking for flexible deployment behind proxies / localhost
    mcp.settings.transport_security.enable_dns_rebinding_protection = False

    sse_app = mcp.sse_app()
    for route in sse_app.routes:
        app.routes.append(route)

    return app


def main():
    parser = argparse.ArgumentParser(
        description="AVV Chennai Academic Calendar (AY2026-27) MCP & OpenAPI Server"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stdio",
        action="store_true",
        help="Run as standard MCP server over stdio (for Claude Desktop, Cursor, Antigravity, etc.)",
    )
    group.add_argument(
        "--http",
        "--sse",
        dest="http",
        action="store_true",
        help="Run unified HTTP server with OpenAPI REST API, Swagger UI, and MCP SSE transport",
    )
    group.add_argument(
        "--export-openapi",
        action="store_true",
        help="Export openapi.json and openapi.yaml files and exit",
    )

    parser.add_argument("--host", default="0.0.0.0", help="Host address for HTTP server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP server (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    if args.export_openapi:
        export_openapi_specs()
        sys.exit(0)

    # Default behavior:
    # If standard input is not a TTY (e.g. piped or launched by Claude Desktop / Cursor), default to stdio
    # Otherwise, if --http is passed, run HTTP
    if args.http:
        print(f"Starting AVV Chennai Academic Calendar Server on http://{args.host}:{args.port}")
        print(f"  - Swagger UI Docs: http://{args.host}:{args.port}/docs")
        print(f"  - ReDoc:           http://{args.host}:{args.port}/redoc")
        print(f"  - OpenAPI Spec:    http://{args.host}:{args.port}/openapi.json")
        print(f"  - MCP SSE Stream:  http://{args.host}:{args.port}/sse")
        app = build_unified_fastapi_app()
        uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    else:
        # Run stdio MCP server
        mcp = create_mcp_server()
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
