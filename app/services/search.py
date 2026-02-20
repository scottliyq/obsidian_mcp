from dataclasses import dataclass

from app.core.config import AppConfig, VaultConfig
from app.infra.embedding.ollama import OllamaEmbeddingClient
from app.infra.vector.chroma import ChromaVectorStore


@dataclass(frozen=True)
class SearchResult:
    vault: str
    path: str
    score: float
    snippet: str
    chunk_id: str


@dataclass
class SearchService:
    config: AppConfig
    embedding: OllamaEmbeddingClient
    vector_store: ChromaVectorStore

    async def search(self, query: str, vault_name: str | None, top_k: int) -> list[SearchResult]:
        vaults = self._resolve_vaults(vault_name)
        results: list[SearchResult] = []
        for vault in vaults:
            model = self.config.resolve_embedding_model(vault)
            embedding = await self.embedding.embed_texts(model, [query])
            if not embedding:
                continue
            payload = self.vector_store.query(vault.name, embedding[0], top_k)
            results.extend(self._to_results(vault, payload))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    def _resolve_vaults(self, vault_name: str | None) -> list[VaultConfig]:
        if vault_name:
            vault = self.config.get_vault(vault_name)
            if not vault:
                raise ValueError(f"vault not found: {vault_name}")
            return [vault]
        return list(self.config.vaults)

    @staticmethod
    def _to_results(vault: VaultConfig, payload: dict) -> list[SearchResult]:
        documents = payload.get("documents", [[]])[0]
        metadatas = payload.get("metadatas", [[]])[0]
        distances = payload.get("distances", [[]])[0]
        results: list[SearchResult] = []
        for idx, (doc, meta, distance) in enumerate(
            zip(documents, metadatas, distances, strict=False)
        ):
            if not isinstance(meta, dict):
                continue
            score = 1.0 - float(distance) if distance is not None else 0.0
            snippet = str(doc)[:200] if doc else ""
            results.append(
                SearchResult(
                    vault=vault.name,
                    path=str(meta.get("path", "")),
                    score=score,
                    snippet=snippet,
                    chunk_id=f"{vault.name}:{meta.get('path', '')}:{idx}",
                )
            )
        return results
