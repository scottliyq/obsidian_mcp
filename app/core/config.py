from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ServerConfig:
    name: str = "obsidian-mcp"
    log_level: str = "INFO"
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/mcp"
    stateless_http: bool = False


@dataclass(frozen=True)
class EmbeddingConfig:
    ollama_base_url: str = "http://localhost:11434"
    timeout_s: float = 30.0
    default_model: str = "nomic-embed-text"


@dataclass(frozen=True)
class VectorStoreConfig:
    persist_dir: Path = Path(".vector_store")


@dataclass(frozen=True)
class IndexingConfig:
    default_chunk_size_chars: int = 800
    default_chunk_overlap_chars: int = 120
    ignore_dirs: list[str] = field(default_factory=lambda: [".obsidian"])


@dataclass(frozen=True)
class ChunkingConfig:
    strategy: str | None = None
    chunk_size_chars: int | None = None
    chunk_overlap_chars: int | None = None


@dataclass(frozen=True)
class VaultConfig:
    name: str
    path: Path
    language: str = "en"
    chunking: ChunkingConfig | None = None
    embedding_model: str | None = None


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    embedding: EmbeddingConfig
    vector_store: VectorStoreConfig
    indexing: IndexingConfig
    vaults: list[VaultConfig]

    def get_vault(self, name: str) -> VaultConfig | None:
        for vault in self.vaults:
            if vault.name == name:
                return vault
        return None

    def resolve_embedding_model(self, vault: VaultConfig) -> str:
        if vault.embedding_model:
            return vault.embedding_model
        if vault.language.lower() == "zh":
            return "qllama/bge-small-zh-v1.5"
        return self.embedding.default_model

    def resolve_chunking(self, vault: VaultConfig) -> ChunkingConfig:
        if vault.chunking:
            return ChunkingConfig(
                strategy=vault.chunking.strategy,
                chunk_size_chars=vault.chunking.chunk_size_chars,
                chunk_overlap_chars=vault.chunking.chunk_overlap_chars,
            )
        default_strategy = "chinese_recursive" if vault.language.lower() == "zh" else "recursive"
        return ChunkingConfig(
            strategy=default_strategy,
            chunk_size_chars=self.indexing.default_chunk_size_chars,
            chunk_overlap_chars=self.indexing.default_chunk_overlap_chars,
        )


@dataclass(frozen=True)
class RawConfig:
    server: dict[str, Any]
    embedding: dict[str, Any]
    vector_store: dict[str, Any]
    indexing: dict[str, Any]
    vaults: list[dict[str, Any]]



def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config.yaml must be a mapping")
    return data



def load_config(path: Path) -> AppConfig:
    data = _load_yaml(path)
    server = ServerConfig(**data.get("server", {}))
    embedding = EmbeddingConfig(**data.get("embedding", {}))
    vector_store = VectorStoreConfig(
        persist_dir=Path(data.get("vector_store", {}).get("persist_dir", ".vector_store"))
    )
    indexing = IndexingConfig(**data.get("indexing", {}))

    vaults_data = data.get("vaults", [])
    if not isinstance(vaults_data, list) or not vaults_data:
        raise ValueError("config.yaml must define at least one vault")

    vaults: list[VaultConfig] = []
    for vault in vaults_data:
        if not isinstance(vault, dict):
            raise ValueError("vault entry must be a mapping")
        chunking_data = vault.get("chunking")
        chunking = None
        if isinstance(chunking_data, dict):
            chunking = ChunkingConfig(
                strategy=chunking_data.get("strategy"),
                chunk_size_chars=chunking_data.get("chunk_size_chars"),
                chunk_overlap_chars=chunking_data.get("chunk_overlap_chars"),
            )
        vaults.append(
            VaultConfig(
                name=vault["name"],
                path=Path(vault["path"]).expanduser(),
                language=vault.get("language", "en"),
                chunking=chunking,
                embedding_model=vault.get("embedding_model"),
            )
        )

    return AppConfig(
        server=server,
        embedding=embedding,
        vector_store=vector_store,
        indexing=indexing,
        vaults=vaults,
    )
