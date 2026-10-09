# Copyright (c) 2026 Krzysztof Rudnicki
"""``--sync``'s local JSON state: absent or broken reads as empty."""

from __future__ import annotations

from typing import TYPE_CHECKING

from daily_limits import _paths, _state

if TYPE_CHECKING:
    from pathlib import Path


def test_save_creates_the_directory_and_load_reads_it_back() -> None:
    _state.save(_paths.HANDLED_FILE, {"a": 1})
    assert _state.load(_paths.HANDLED_FILE) == {"a": 1}
    assert _paths.HANDLED_FILE.stat().st_mode & 0o777 == 0o644


def test_missing_file_is_empty() -> None:
    assert _state.load(_paths.HANDLED_FILE) == {}


def test_corrupt_json_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json", encoding="utf-8")
    assert _state.load(path) == {}


def test_unreadable_path_is_empty(tmp_path: Path) -> None:
    assert _state.load(tmp_path) == {}


def test_non_object_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert _state.load(path) == {}
