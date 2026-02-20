from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import hashlib

import structlog

from app.core.config import AppConfig, VaultConfig
from app.infra.embedding.ollama import EmbeddingContextLengthError, OllamaEmbeddingClient
from app.services.chunking import build_splitter, build_splitter_with_policy
from app.services.index_state import IndexRecord, IndexState

logger = structlog.get_logger(__name__)


class VectorStore(Protocol):
    def reset_collection(self, vault_name: str) -> None:
        ...

    def delete_by_path(self, vault_name: str, path: str) -> None:
        ...

    def add_texts(
        self,
        vault_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, object]],
        embeddings: list[list[float]],
    ) -> None:
        ...


@dataclass
class Indexer:
    config: AppConfig
    embedding: OllamaEmbeddingClient
    vector_store: VectorStore

    async def index_all(self, force: bool = False) -> None:
        for vault in self.config.vaults:
            await self.index_vault(vault, force=force)

    async def index_vault(self, vault: VaultConfig, force: bool = False) -> None:
        if force:
            self.vector_store.reset_collection(vault.name)
        state_path = self._state_path(vault)
        state = IndexState.load(state_path)
        if force:
            state.entries.clear()
        files = list(self._iter_markdown_files(vault))
        logger.info("vault_index_start", vault=vault.name, files=len(files), force=force)
        current_paths: set[str] = set()
        for path in files:
            current_paths.add(str(path))
            await self._reindex_if_needed(vault, path, state)
        removed = set(state.entries.keys()) - current_paths
        for path_str in removed:
            self.vector_store.delete_by_path(vault.name, path_str)
            state.entries.pop(path_str, None)
        logger.info("vault_index_done", vault=vault.name, files=len(files))
        state.save(state_path)

    async def reindex_file(self, vault: VaultConfig, path: Path) -> None:
        if not path.exists():
            return
        state_path = self._state_path(vault)
        state = IndexState.load(state_path)
        await self._reindex_if_needed(vault, path, state)
        state.save(state_path)

    def delete_file(self, vault: VaultConfig, path: Path) -> None:
        self.vector_store.delete_by_path(vault.name, str(path))
        state_path = self._state_path(vault)
        state = IndexState.load(state_path)
        state.entries.pop(str(path), None)
        state.save(state_path)
        logger.info("file_deleted", vault=vault.name, path=str(path))

    def _iter_markdown_files(self, vault: VaultConfig):
        ignore = set(self.config.indexing.ignore_dirs)
        for path in vault.path.rglob("*.md"):
            if self._is_ignored(path, ignore):
                continue
            yield path

    @staticmethod
    def _is_ignored(path: Path, ignore: set[str]) -> bool:
        parts = set(path.parts)
        return bool(parts & ignore)

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _chunk_id(vault: VaultConfig, path: Path, index: int) -> str:
        return f"{vault.name}:{path}:{index}"

    def _state_path(self, vault: VaultConfig) -> Path:
        base = self.config.vector_store.persist_dir
        base.mkdir(parents=True, exist_ok=True)
        return base / f".index_state_{vault.name}.json"

    async def _reindex_if_needed(self, vault: VaultConfig, path: Path, state: IndexState) -> None:
        if not path.exists():
            return
        stat = path.stat()
        record = state.entries.get(str(path))
        if record and record.mtime == stat.st_mtime:
            return

        text = self._read_text(path)
        if not text:
            return
        sha1 = self._hash_text(text)
        if record and record.sha1 == sha1:
            state.entries[str(path)] = IndexRecord(mtime=stat.st_mtime, sha1=sha1)
            return

        policy = self.config.resolve_chunking(vault)
        strategy = policy.strategy or "recursive"
        chunk_size = policy.chunk_size_chars or self.config.indexing.default_chunk_size_chars
        overlap = policy.chunk_overlap_chars or self.config.indexing.default_chunk_overlap_chars

        model = self.config.resolve_embedding_model(vault)
        embeddings: list[list[float]] = []
        chunks: list[str] = []
        for _ in range(4):
            splitter = build_splitter_with_policy(strategy, chunk_size, overlap)
            chunks = splitter.split_text(text)
            if not chunks:
                return
            try:
                embeddings = await self.embedding.embed_texts(model, chunks)
                break
            except EmbeddingContextLengthError:
                if chunk_size <= 200:
                    raise
                chunk_size = max(200, chunk_size // 2)
                overlap = min(overlap, max(40, chunk_size // 5))
        if not embeddings:
            return

        ids = [self._chunk_id(vault, path, idx) for idx in range(len(chunks))]
        metadatas = [
            {
                "vault": vault.name,
                "path": str(path),
                "chunk_index": idx,
            }
            for idx in range(len(chunks))
        ]
        self.vector_store.delete_by_path(vault.name, str(path))
        self.vector_store.add_texts(
            vault_name=vault.name,
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        state.entries[str(path)] = IndexRecord(mtime=stat.st_mtime, sha1=sha1)
        logger.info(
            "file_indexed",
            vault=vault.name,
            path=str(path),
            chunks=len(chunks),
            model=model,
        )

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()
