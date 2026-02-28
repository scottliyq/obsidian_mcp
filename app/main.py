import argparse
from pathlib import Path

from app.core.config import load_config
from app.mcp.server import create_server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="obsidian-mcp")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "streamable-http"],
        default=None,
        help="MCP transport mode, fallback to config server.transport",
    )
    parser.add_argument("--host", type=str, default=None, help="HTTP host, fallback to config")
    parser.add_argument("--port", type=int, default=None, help="HTTP port, fallback to config")
    parser.add_argument("--path", type=str, default=None, help="HTTP endpoint path, fallback to config")
    parser.add_argument(
        "--stateless-http",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable/disable stateless HTTP mode, fallback to config",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    server = create_server(config_path)

    transport = args.transport or config.server.transport
    if transport == "stdio":
        server.run(transport="stdio")
        return

    host = args.host or config.server.host
    port = args.port if args.port is not None else config.server.port
    path = args.path or config.server.path
    stateless_http = (
        args.stateless_http if args.stateless_http is not None else config.server.stateless_http
    )

    server.run(
        transport="streamable-http",
        host=host,
        port=port,
        path=path,
        stateless_http=stateless_http,
    )


if __name__ == "__main__":
    main()
