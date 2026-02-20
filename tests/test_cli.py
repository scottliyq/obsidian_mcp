import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from app import cli as cli_module
from app.core.config import AppConfig, EmbeddingConfig, IndexingConfig, ServerConfig, VectorStoreConfig, VaultConfig


@dataclass
class FakeIndexer:
    all_called: bool = False
    vault_called: bool = False

    async def index_all(self, force: bool = False) -> None:
        self.all_called = force

    async def index_vault(self, vault: VaultConfig, force: bool = False) -> None:
        self.vault_called = force


@dataclass
class FakeEmbedding:
    async def close(self) -> None:
        return None


@dataclass
class FakeServices:
    indexer: FakeIndexer
    embedding: FakeEmbedding


@pytest.mark.asyncio
async def test_cli_index_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    vault = VaultConfig(name="v1", path=tmp_path, language="en")
    config = AppConfig(
        server=ServerConfig(),
        embedding=EmbeddingConfig(),
        vector_store=VectorStoreConfig(),
        indexing=IndexingConfig(),
        vaults=[vault],
    )
    fake_services = FakeServices(indexer=FakeIndexer(), embedding=FakeEmbedding())

    monkeypatch.setattr(cli_module, "load_config", lambda _: config)
    monkeypatch.setattr(cli_module, "configure_logging", lambda _: None)
    monkeypatch.setattr(cli_module, "build_services", lambda _: fake_services)

    await cli_module._run_index(True, None, tmp_path / "config.yaml")
    assert fake_services.indexer.all_called is True


@pytest.mark.asyncio
async def test_cli_index_vault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    vault = VaultConfig(name="v1", path=tmp_path, language="en")
    config = AppConfig(
        server=ServerConfig(),
        embedding=EmbeddingConfig(),
        vector_store=VectorStoreConfig(),
        indexing=IndexingConfig(),
        vaults=[vault],
    )
    fake_services = FakeServices(indexer=FakeIndexer(), embedding=FakeEmbedding())

    monkeypatch.setattr(cli_module, "load_config", lambda _: config)
    monkeypatch.setattr(cli_module, "configure_logging", lambda _: None)
    monkeypatch.setattr(cli_module, "build_services", lambda _: fake_services)

    await cli_module._run_index(False, "v1", tmp_path / "config.yaml")
    assert fake_services.indexer.vault_called is True
