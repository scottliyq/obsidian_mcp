from dataclasses import dataclass

from app.core.config import AppConfig, VaultConfig


@dataclass(frozen=True)
class ChunkingPolicy:
    strategy: str
    chunk_size_chars: int
    chunk_overlap_chars: int


def _resolve_policy(config: AppConfig, vault: VaultConfig) -> ChunkingPolicy:
    chunking = config.resolve_chunking(vault)
    strategy = chunking.strategy or "recursive"
    chunk_size = chunking.chunk_size_chars or config.indexing.default_chunk_size_chars
    overlap = chunking.chunk_overlap_chars or config.indexing.default_chunk_overlap_chars
    return ChunkingPolicy(
        strategy=strategy,
        chunk_size_chars=chunk_size,
        chunk_overlap_chars=overlap,
    )


def build_splitter_with_policy(strategy: str, chunk_size: int, overlap: int):
    if strategy == "chinese_recursive":
        separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        return ChineseRecursiveTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=separators,
        )
    separators = ["\n\n", "\n", ".", "!", "?", ";", ",", " ", ""]
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=separators,
    )


def _merge_with_overlap(chunks: list[str], chunk_size: int, overlap: int) -> list[str]:
    if overlap <= 0:
        return [chunk for chunk in chunks if chunk]
    merged: list[str] = []
    prev = ""
    for chunk in chunks:
        if not chunk:
            continue
        if not prev:
            merged.append(chunk)
        else:
            prefix = prev[-overlap:]
            candidate = f"{prefix}{chunk}"
            merged.append(candidate[:chunk_size])
        prev = chunk
    return merged


def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    if not separators:
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep = separators[0]
    if sep == "":
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    parts = text.split(sep)
    results: list[str] = []
    buffer = ""
    for part in parts:
        if not part:
            continue
        candidate = f"{buffer}{sep}{part}" if buffer else part
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer:
            results.extend(_recursive_split(buffer, separators[1:], chunk_size))
        buffer = part
    if buffer:
        results.extend(_recursive_split(buffer, separators[1:], chunk_size))
    return results


@dataclass(frozen=True)
class RecursiveCharacterTextSplitter:
    chunk_size: int
    chunk_overlap: int
    separators: list[str]

    def split_text(self, text: str) -> list[str]:
        chunks = _recursive_split(text, self.separators, self.chunk_size)
        return _merge_with_overlap(chunks, self.chunk_size, self.chunk_overlap)


@dataclass(frozen=True)
class ChineseRecursiveTextSplitter(RecursiveCharacterTextSplitter):
    pass


def build_splitter(config: AppConfig, vault: VaultConfig):
    policy = _resolve_policy(config, vault)
    return build_splitter_with_policy(
        policy.strategy,
        policy.chunk_size_chars,
        policy.chunk_overlap_chars,
    )
