from pathlib import Path

from app.services.index_state import IndexState


def test_load_empty_state_file_returns_empty_entries(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("", encoding="utf-8")

    state = IndexState.load(state_path)

    assert state.entries == {}


def test_load_invalid_json_state_file_returns_empty_entries(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("{invalid", encoding="utf-8")

    state = IndexState.load(state_path)

    assert state.entries == {}
