from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class IndexRecord:
    mtime: float
    sha1: str


@dataclass
class IndexState:
    entries: dict[str, IndexRecord]

    @classmethod
    def load(cls, path: Path) -> "IndexState":
        if not path.exists():
            return cls(entries={})
        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return cls(entries={})
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return cls(entries={})
        raw = data.get("entries", {}) if isinstance(data, dict) else {}
        entries: dict[str, IndexRecord] = {}
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            mtime = value.get("mtime")
            sha1 = value.get("sha1")
            if isinstance(mtime, (int, float)) and isinstance(sha1, str):
                entries[str(key)] = IndexRecord(mtime=float(mtime), sha1=sha1)
        return cls(entries=entries)

    def save(self, path: Path) -> None:
        payload = {
            "version": 1,
            "entries": {key: {"mtime": rec.mtime, "sha1": rec.sha1} for key, rec in self.entries.items()},
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
