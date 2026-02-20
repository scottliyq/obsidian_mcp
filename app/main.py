from pathlib import Path

from app.mcp.server import create_server


def main() -> None:
    config_path = Path("config.yaml")
    server = create_server(config_path)
    server.run()


if __name__ == "__main__":
    main()
