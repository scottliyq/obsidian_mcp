from dataclasses import dataclass
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingContextLengthError(ValueError):
    pass


@dataclass
class OllamaEmbeddingClient:
    base_url: str
    timeout_s: float

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=self.timeout_s)

    async def close(self) -> None:
        await self._client.aclose()

    async def embed_texts(self, model: str, texts: list[str]) -> list[list[float]]:
        cleaned = [text for text in texts if text and text.strip()]
        if not cleaned:
            return []

        payload = {"model": model, "input": cleaned}
        url = f"{self.base_url}/api/embed"
        response = await self._client.post(url, json=payload)
        if response.status_code == 404:
            return await self._embed_legacy(model, texts)
        if response.is_error:
            body = response.text
            logger.error(
                "ollama_embed_failed",
                status_code=response.status_code,
                body=body,
            )
            if response.status_code == 400 and "context length" in body:
                raise EmbeddingContextLengthError(body)
            response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("Ollama /api/embed response missing embeddings")
        return embeddings

    async def _embed_legacy(self, model: str, texts: list[str]) -> list[list[float]]:
        url = f"{self.base_url}/api/embeddings"
        results: list[list[float]] = []
        for text in texts:
            if not text or not text.strip():
                continue
            payload = {"model": model, "prompt": text}
            response = await self._client.post(url, json=payload)
            if response.status_code == 404:
                raise RuntimeError(
                    "Ollama embedding endpoint not found. "
                    "Check ollama_base_url, ensure Ollama is running, and verify the model is pulled."
                )
            if response.is_error:
                body = response.text
                logger.error(
                    "ollama_legacy_embed_failed",
                    status_code=response.status_code,
                    body=body,
                )
                if response.status_code == 400 and "context length" in body:
                    raise EmbeddingContextLengthError(body)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                raise ValueError("Ollama /api/embeddings response missing embedding")
            results.append(embedding)
        logger.warning("ollama_legacy_embeddings_used", model=model, count=len(texts))
        return results
