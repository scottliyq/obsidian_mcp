from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ChromaVectorStore:
    persist_dir: Path

    def __post_init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collections: dict[str, Any] = {}

    def get_collection(self, vault_name: str) -> Any:
        if vault_name not in self._collections:
            collection = self._client.get_or_create_collection(
                name=f"vault_{vault_name}",
                metadata={"hnsw:space": "cosine"},
            )
            self._collections[vault_name] = collection
        return self._collections[vault_name]

    def reset_collection(self, vault_name: str) -> None:
        name = f"vault_{vault_name}"
        try:
            self._client.delete_collection(name=name)
        except ValueError:
            logger.warning("collection_missing", collection=name)
        self._collections.pop(vault_name, None)
        self.get_collection(vault_name)

    def delete_by_path(self, vault_name: str, path: str) -> None:
        collection = self.get_collection(vault_name)
        collection.delete(where={"path": path})

    def add_texts(
        self,
        vault_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        collection = self.get_collection(vault_name)
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self,
        vault_name: str,
        embedding: list[float],
        top_k: int,
    ) -> dict[str, Any]:
        collection = self.get_collection(vault_name)
        return collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
