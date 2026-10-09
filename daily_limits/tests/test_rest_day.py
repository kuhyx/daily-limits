# Copyright (c) 2026 Krzysztof Rudnicki
"""Declaring a rest day through screen-locker's CLI, as a subprocess."""

from __future__ import annotations

from datetime import date
import subprocess

import pytest

from daily_limits import _paths, _rest_day


@pytest.mark.parametrize(
    "raw",
    [
        None,
        20261010,
        "",
        "tomorrow",
        "--list",
        "2026-13-01",
        "20261010",
        "2026-10-10T00",
    ],
)
def test_parse_day_rejects_anything_but_yyyy_mm_dd(raw: object) -> None:
    assert _rest_day.parse_day(raw) is None


def test_parse_day_accepts_an_iso_date() -> None:
    assert _rest_day.parse_day("2026-10-10") == date(2026, 10, 10)


def _fake_run(
    monkeypatch: pytest.MonkeyPatch, *, code: int, out: str = "", err: str = ""
) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, code, out, err)

    monkeypatch.setattr(subprocess, "run", run)
    return calls


def test_declare_runs_screen_lockers_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_run(monkeypatch, code=0, out="declared 2026-10-10\n")
    assert _rest_day.declare(date(2026, 10, 10)) == (True, "declared 2026-10-10")
    assert calls == [
        [
            _paths.SCREEN_LOCKER_PYTHON,
            "-m",
            "screen_locker.screen_lock",
            "--declare-rest-day",
            "2026-10-10",
        ]
    ]


def test_declare_reports_a_refusal_from_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_run(monkeypatch, code=1, err="refused: two per week\n")
    assert _rest_day.declare(date(2026, 10, 10)) == (False, "refused: two per week")


def test_declare_without_output_names_the_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_run(monkeypatch, code=3)
    assert _rest_day.declare(date(2026, 10, 10)) == (False, "screen-locker exited 3")


def test_declare_survives_a_missing_interpreter() -> None:
    ok, message = _rest_day.declare(date(2026, 10, 10))
    assert not ok
    assert message.startswith("could not run screen-locker:")


def test_declare_survives_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(argv: list[str], **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(argv, 45)

    monkeypatch.setattr(subprocess, "run", run)
    ok, message = _rest_day.declare(date(2026, 10, 10))
    assert not ok
    assert "timed out" in message
