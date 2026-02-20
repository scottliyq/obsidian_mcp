import asyncio
from dataclasses import dataclass
from pathlib import Path

import structlog
from watchfiles import Change, awatch

from app.core.config import AppConfig, VaultConfig
from app.services.indexer import Indexer

logger = structlog.get_logger(__name__)


@dataclass
class VaultWatcher:
    config: AppConfig
    indexer: Indexer

    async def run(self) -> None:
        tasks = [asyncio.create_task(self._watch_vault(vault)) for vault in self.config.vaults]
        await asyncio.gather(*tasks)

    async def _watch_vault(self, vault: VaultConfig) -> None:
        ignore = set(self.config.indexing.ignore_dirs)
        async for changes in awatch(vault.path):
            for change, path_str in changes:
                path = Path(path_str)
                if path.suffix.lower() != ".md":
                    continue
                if self._is_ignored(path, ignore):
                    continue
                if change in (Change.added, Change.modified):
                    await self.indexer.reindex_file(vault, path)
                elif change is Change.deleted:
                    self.indexer.delete_file(vault, path)
                else:
                    logger.warning("unhandled_change", change=str(change), path=path_str)

    @staticmethod
    def _is_ignored(path: Path, ignore: set[str]) -> bool:
        parts = set(path.parts)
        return bool(parts & ignore)
