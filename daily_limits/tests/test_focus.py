# Copyright (c) 2026 Krzysztof Rudnicki
"""The ``focus`` field: a soft import of focus_project, and the i3blocks poke."""

from __future__ import annotations

from datetime import date
import json
import logging
import subprocess
import sys
import types
from typing import TYPE_CHECKING

from daily_limits import _cli, _focus, _paths, _report

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest

DAY = date(2026, 11, 2)
STATUS = {
    "project": "hackerrank-prep",
    "name": "HackerRank prep",
    "minutes": 45,
    "daily_minutes": 120,
    "unlock_minutes": 30,
    "ends": "2026-11-05",
    "replaces": ["leetcode", "reading", "tutor"],
}


def _install(monkeypatch: pytest.MonkeyPatch, status: Callable[[date], object]) -> None:
    fake = types.SimpleNamespace(status=status)
    monkeypatch.setitem(sys.modules, "focus_project", fake)


def test_fetch_returns_the_status_of_the_day(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[date] = []

    def status(day: date) -> dict[str, object]:
        asked.append(day)
        return dict(STATUS)

    _install(monkeypatch, status)
    assert _focus.fetch(DAY) == STATUS
    assert asked == [DAY]


def test_fetch_without_the_package_is_none_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # conftest sets sys.modules["focus_project"] = None: the import fails.
    with caplog.at_level(logging.WARNING):
        assert _focus.fetch(DAY) is None
    assert "focus_project" in caplog.text


def test_fetch_survives_a_failing_status(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(_day: date) -> object:
        msg = "projects.json is garbage"
        raise ValueError(msg)

    _install(monkeypatch, boom)
    with caplog.at_level(logging.WARNING):
        assert _focus.fetch(DAY) is None
    assert "projects.json is garbage" in caplog.text


def test_fetch_rejects_a_non_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, lambda _day: ["nope"])
    assert _focus.fetch(DAY) is None


def test_the_report_carries_focus_only_when_it_is_known(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "focus" not in _report.build()
    _install(monkeypatch, lambda _day: dict(STATUS))
    assert _report.build()["focus"] == STATUS


def test_notify_signals_i3blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", run)
    _focus.notify()
    assert calls == [[_paths.PKILL, f"-RTMIN+{_paths.FOCUS_SIGNAL}", "-x", "i3blocks"]]


def test_notify_without_pkill_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    # conftest points PKILL at a name on no PATH.
    with caplog.at_level(logging.WARNING):
        _focus.notify()
    assert "pkill" in caplog.text


def test_the_cache_refresh_signals_only_when_focus_changed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pokes: list[int] = []
    monkeypatch.setattr(_focus, "notify", lambda: pokes.append(1))
    target = tmp_path / "cache.json"
    _install(monkeypatch, lambda _day: dict(STATUS))
    _cli._refresh_cache(target)  # no previous cache: a first sight is a change
    assert len(pokes) == 1
    _cli._refresh_cache(target)  # same focus: no poke
    assert len(pokes) == 1
    _install(monkeypatch, lambda _day: {**STATUS, "minutes": 46})
    _cli._refresh_cache(target)
    assert len(pokes) == 2
    assert json.loads(target.read_text())["focus"]["minutes"] == 46


def test_a_project_ending_signals_too(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pokes: list[int] = []
    monkeypatch.setattr(_focus, "notify", lambda: pokes.append(1))
    target = tmp_path / "cache.json"
    _install(monkeypatch, lambda _day: dict(STATUS))
    _cli._refresh_cache(target)
    monkeypatch.setitem(sys.modules, "focus_project", None)  # focus vanished
    _cli._refresh_cache(target)
    assert len(pokes) == 2


def test_a_garbled_previous_cache_counts_as_changed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pokes: list[int] = []
    monkeypatch.setattr(_focus, "notify", lambda: pokes.append(1))
    target = tmp_path / "cache.json"
    target.write_text("{", encoding="utf-8")
    _install(monkeypatch, lambda _day: dict(STATUS))
    _cli._refresh_cache(target)
    assert pokes == [1]
