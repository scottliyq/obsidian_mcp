from dataclasses import dataclass
from pathlib import Path

import pytest

from app.core.config import AppConfig, EmbeddingConfig, IndexingConfig, ServerConfig, VectorStoreConfig, VaultConfig
from app.infra.embedding.ollama import EmbeddingContextLengthError
from app.services.indexer import Indexer


@dataclass
class FakeEmbeddingClient:
    fail_once: bool = False
    calls: int = 0

    async def embed_texts(self, model: str, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.fail_once:
            self.fail_once = False
            raise EmbeddingContextLengthError("context length")
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def close(self) -> None:
        return None


@dataclass
class FakeVectorStore:
    added: dict[str, list[str]]
    deleted: set[str]

    def reset_collection(self, vault_name: str) -> None:
        return None

    def delete_by_path(self, vault_name: str, path: str) -> None:
        self.deleted.add(path)
        self.added.pop(path, None)

    def add_texts(
        self,
        vault_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        if metadatas:
            path = str(metadatas[0].get("path"))
            self.added[path] = ids

    def query(self, vault_name: str, embedding: list[float], top_k: int) -> dict:
        ids = list(self.added.values())
        flat = ids[0] if ids else []
        return {"ids": [flat]}


@pytest.mark.asyncio
async def test_indexer_add_and_delete(tmp_path: Path) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    note_path = vault_dir / "note.md"
    note_path.write_text("hello world\n" * 5, encoding="utf-8")

    config = AppConfig(
        server=ServerConfig(),
        embedding=EmbeddingConfig(),
        vector_store=VectorStoreConfig(persist_dir=tmp_path / "vectors"),
        indexing=IndexingConfig(),
        vaults=[VaultConfig(name="v1", path=vault_dir, language="en")],
    )

    vector_store = FakeVectorStore(added={}, deleted=set())
    indexer = Indexer(config=config, embedding=FakeEmbeddingClient(), vector_store=vector_store)

    await indexer.reindex_file(config.vaults[0], note_path)
    result = vector_store.query("v1", [0.1, 0.2, 0.3], top_k=5)
    assert result["ids"][0]

    indexer.delete_file(config.vaults[0], note_path)
    result_after = vector_store.query("v1", [0.1, 0.2, 0.3], top_k=5)
    assert result_after["ids"][0] == []


@pytest.mark.asyncio
async def test_indexer_retries_on_context_length(tmp_path: Path) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    note_path = vault_dir / "note.md"
    note_path.write_text("hello world\n" * 200, encoding="utf-8")

    config = AppConfig(
        server=ServerConfig(),
        embedding=EmbeddingConfig(),
        vector_store=VectorStoreConfig(persist_dir=tmp_path / "vectors"),
        indexing=IndexingConfig(),
        vaults=[VaultConfig(name="v1", path=vault_dir, language="en")],
    )

    vector_store = FakeVectorStore(added={}, deleted=set())
    embedding = FakeEmbeddingClient(fail_once=True)
    indexer = Indexer(config=config, embedding=embedding, vector_store=vector_store)

    await indexer.reindex_file(config.vaults[0], note_path)
    result = vector_store.query("v1", [0.1, 0.2, 0.3], top_k=5)
    assert result["ids"][0]


@pytest.mark.asyncio
async def test_indexer_incremental_skip(tmp_path: Path) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    note_path = vault_dir / "note.md"
    note_path.write_text("hello world\n" * 5, encoding="utf-8")

    config = AppConfig(
        server=ServerConfig(),
        embedding=EmbeddingConfig(),
        vector_store=VectorStoreConfig(persist_dir=tmp_path / "vectors"),
        indexing=IndexingConfig(),
        vaults=[VaultConfig(name="v1", path=vault_dir, language="en")],
    )

    vector_store = FakeVectorStore(added={}, deleted=set())
    embedding = FakeEmbeddingClient()
    indexer = Indexer(config=config, embedding=embedding, vector_store=vector_store)

    await indexer.index_vault(config.vaults[0], force=False)
    first_calls = embedding.calls
    await indexer.index_vault(config.vaults[0], force=False)
    assert embedding.calls == first_calls
