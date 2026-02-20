import argparse
import asyncio
from pathlib import Path

import structlog

from app.bootstrap import build_services
from app.core.config import load_config
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="obsidian-mcp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Force reindex vaults")
    group = index_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Reindex all vaults")
    group.add_argument("--vault", type=str, help="Vault name to reindex")
    index_parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config.yaml",
    )

    return parser


async def _run_index(all_vaults: bool, vault_name: str | None, config_path: Path) -> None:
    config = load_config(config_path)
    configure_logging(config.server.log_level)
    services = build_services(config)
    try:
        if all_vaults:
            await services.indexer.index_all(force=True)
        else:
            vault = config.get_vault(vault_name or "")
            if not vault:
                raise ValueError(f"vault not found: {vault_name}")
            await services.indexer.index_vault(vault, force=True)
        logger.info("index_done")
    finally:
        await services.embedding.close()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "index":
        asyncio.run(_run_index(args.all, args.vault, Path(args.config)))


if __name__ == "__main__":
    main()
