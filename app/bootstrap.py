from dataclasses import dataclass

from app.core.config import AppConfig
from app.infra.embedding.ollama import OllamaEmbeddingClient
from app.infra.vector.chroma import ChromaVectorStore
from app.services.indexer import Indexer
from app.services.search import SearchService
from app.services.watcher import VaultWatcher


@dataclass
class Services:
    embedding: OllamaEmbeddingClient
    vector_store: ChromaVectorStore
    indexer: Indexer
    search: SearchService
    watcher: VaultWatcher


def build_services(config: AppConfig) -> Services:
    embedding = OllamaEmbeddingClient(
        base_url=config.embedding.ollama_base_url,
        timeout_s=config.embedding.timeout_s,
    )
    vector_store = ChromaVectorStore(config.vector_store.persist_dir)
    indexer = Indexer(config=config, embedding=embedding, vector_store=vector_store)
    search = SearchService(config=config, embedding=embedding, vector_store=vector_store)
    watcher = VaultWatcher(config=config, indexer=indexer)
    return Services(
        embedding=embedding,
        vector_store=vector_store,
        indexer=indexer,
        search=search,
        watcher=watcher,
    )
