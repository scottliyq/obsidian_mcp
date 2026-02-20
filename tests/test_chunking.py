from pathlib import Path

from app.core.config import AppConfig, EmbeddingConfig, IndexingConfig, ServerConfig, VectorStoreConfig, VaultConfig
from app.services.chunking import build_splitter


def _config(vault: VaultConfig) -> AppConfig:
    return AppConfig(
        server=ServerConfig(),
        embedding=EmbeddingConfig(),
        vector_store=VectorStoreConfig(),
        indexing=IndexingConfig(),
        vaults=[vault],
    )


def test_build_splitter_chinese_strategy() -> None:
    vault = VaultConfig(
        name="zh",
        path=Path("/tmp/zh"),
        language="zh",
    )
    splitter = build_splitter(_config(vault), vault)
    assert splitter.__class__.__name__ == "ChineseRecursiveTextSplitter"


def test_build_splitter_recursive_strategy() -> None:
    vault = VaultConfig(
        name="en",
        path=Path("/tmp/en"),
        language="en",
    )
    splitter = build_splitter(_config(vault), vault)
    assert splitter.__class__.__name__ == "RecursiveCharacterTextSplitter"
