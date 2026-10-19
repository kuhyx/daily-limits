# Copyright (c) 2026 Krzysztof Rudnicki
"""The ``daily-limits`` entry point and the atomic cache write."""

from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import sys
from typing import TYPE_CHECKING

import pytest

from daily_limits import (
    _alerts,
    _atomic,
    _cli,
    _gui,
    _leisure_now,
    _paths,
    _report,
    _splash,
    _sync,
)
from daily_limits.tests import _samples

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture(autouse=True)
def fixed_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_report, "build", _samples.report)


def test_default_prints_the_summary(capsys: pytest.CaptureFixture[str]) -> None:
    assert _cli.main([]) == 0
    assert capsys.readouterr().out.startswith("Today 2026-10-09\n")


def test_json_prints_the_contract(capsys: pytest.CaptureFixture[str]) -> None:
    assert _cli.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == _samples.report()


def test_write_cache_writes_the_contract_atomically() -> None:
    assert _cli.main(["--write-cache"]) == 0
    target = Path(os.environ["XDG_RUNTIME_DIR"]) / _paths.CACHE_NAME
    assert json.loads(target.read_text(encoding="utf-8")) == _samples.report()
    assert target.stat().st_mode & 0o777 == 0o644
    assert [p.name for p in target.parent.iterdir()] == [_paths.CACHE_NAME]


def test_write_cache_without_a_runtime_dir_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR")
    assert _cli.main(["--write-cache"]) == 1
    assert "XDG_RUNTIME_DIR is not set" in capsys.readouterr().err


def test_sync_writes_the_cache_then_ticks(monkeypatch: pytest.MonkeyPatch) -> None:
    target = Path(os.environ["XDG_RUNTIME_DIR"]) / _paths.CACHE_NAME
    ticks: list[_report.Report] = []

    def tick(report: _report.Report, rebuild: Callable[[], _report.Report]) -> None:
        # The cache is already on disk before Firebase is touched.
        assert json.loads(target.read_text(encoding="utf-8")) == report
        target.unlink()
        ticks.append(report)
        assert rebuild() == report
        assert target.exists()

    monkeypatch.setattr(_sync, "tick", tick)
    monkeypatch.setattr(_alerts, "tick", lambda shadow, facts: None)
    assert _cli.main(["--sync"]) == 0
    assert ticks == [_samples.report()]


def test_sync_runs_the_shadow_alerts_after_the_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = Path(os.environ["XDG_RUNTIME_DIR"]) / _paths.CACHE_NAME
    facts = _leisure_now.Facts(state="free", paused_by=None, reasons=())
    alerts: list[object] = []

    def alert(shadow: object, seen: object) -> None:
        assert target.exists()
        alerts.append((shadow, seen))

    monkeypatch.setattr(_leisure_now, "read", lambda: facts)
    monkeypatch.setattr(_alerts, "tick", alert)
    monkeypatch.setattr(_sync, "tick", lambda report, rebuild: alerts.append("sync"))
    assert _cli.main(["--sync"]) == 0
    assert alerts == [(_samples.report()["leisure_shadow"], facts), "sync"]


def test_a_failing_alert_never_costs_the_sync(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(shadow: object, facts: object) -> None:
        del shadow, facts
        msg = "read-only state dir"
        raise OSError(msg)

    synced: list[str] = []
    monkeypatch.setattr(_alerts, "tick", broken)
    monkeypatch.setattr(_sync, "tick", lambda report, rebuild: synced.append("sync"))
    assert _cli.main(["--sync"]) == 0
    assert synced == ["sync"]
    assert "shadow alerts failed: read-only state dir" in caplog.text


def test_write_cache_alone_never_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(shadow: object, facts: object) -> None:
        raise AssertionError((shadow, facts))

    monkeypatch.setattr(_alerts, "tick", refuse)
    assert _cli.main(["--write-cache"]) == 0


def test_cache_path_honours_the_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DAILY_LIMITS_CACHE", str(tmp_path / "c.json"))
    assert _cli.cache_path() == tmp_path / "c.json"


def test_shadow_splash_mode_shows_the_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    shown: list[Path | None] = []

    def show(cache: Path | None) -> int:
        shown.append(cache)
        return 5

    monkeypatch.setattr(_splash, "run", show)
    assert _cli.main(["--shadow-splash"]) == 5
    assert shown == [Path(os.environ["XDG_RUNTIME_DIR"]) / _paths.CACHE_NAME]


def test_write_atomic_removes_its_temp_file_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(self: Path, target: Path) -> Path:
        del self, target
        msg = "replace refused"
        raise OSError(msg)

    monkeypatch.setattr(Path, "replace", refuse)
    target = tmp_path / "out.json"
    with pytest.raises(OSError, match="replace refused"):
        _atomic.write_atomic(target, "{}")
    assert not list(tmp_path.glob(".out.json.*"))
    assert not target.exists()


def test_gui_mode_runs_the_popup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_gui, "run", lambda: 7)
    assert _cli.main(["--gui"]) == 7


def test_modes_are_exclusive(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _cli.main(["--json", "--gui"])
    assert "not allowed with" in capsys.readouterr().err


def test_module_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["daily-limits", "--json"])
    monkeypatch.setattr(_cli, "main", lambda: 3)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("daily_limits", run_name="__main__")
    assert exit_info.value.code == 3
