# Copyright (c) 2026 Krzysztof Rudnicki
"""Running ``leetcode_guard.open_cli``: system python, exit status, never a crash."""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from daily_limits import _leetcode_open
from daily_limits import _tokens as tok
from daily_limits.tests import _samples
from daily_limits.tests._fake_tk import clickable, popup, texts

if TYPE_CHECKING:
    import pytest

    from daily_limits import _report
    from daily_limits.tests._fake_tk import FakeWidget

ARGV = ["/usr/bin/python3", "-m", "leetcode_guard.open_cli"]


def _exits(monkeypatch: pytest.MonkeyPatch, code: int) -> list[tuple[object, ...]]:
    """Make the guard's CLI exit ``code``; returns the recorded calls."""
    calls: list[tuple[object, ...]] = []

    def fake_run(argv: list[str], **kwargs: object) -> object:
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, code)

    monkeypatch.setattr("daily_limits._leetcode_open.subprocess.run", fake_run)
    return calls


def test_launch_runs_the_guards_opener_without_stdio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _exits(monkeypatch, 0)
    assert _leetcode_open.launch() is None
    assert calls == [
        (
            ARGV,
            {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "timeout": _leetcode_open.TIMEOUT_SECONDS,
                "check": False,
            },
        )
    ]


def test_a_nonzero_exit_is_a_failed_open(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _exits(monkeypatch, 1)
    with caplog.at_level(logging.WARNING):
        assert _leetcode_open.launch() == "could not open a LeetCode problem"
    assert "leetcode_guard.open_cli exited 1" in caplog.text


def test_launch_survives_a_missing_python_and_a_hang(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    for error in (OSError("no such file"), subprocess.TimeoutExpired(ARGV, 1)):

        def broken(
            *_args: object, _error: Exception = error, **_kwargs: object
        ) -> object:
            raise _error

        monkeypatch.setattr("daily_limits._leetcode_open.subprocess.run", broken)
        with caplog.at_level(logging.WARNING):
            assert _leetcode_open.launch() == _leetcode_open.FAILED
    assert caplog.text.count("could not run leetcode_guard.open_cli") == 2


def _leetcode_report() -> _report.Report:
    """The sample report with its second earner (todo) named ``leetcode``."""
    report = _samples.report()
    report["earners"][1]["name"] = "leetcode"
    report["todo"][0]["name"] = "leetcode"
    return report


def test_the_leetcode_row_opens_a_problem(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    opened: list[str] = []
    monkeypatch.setattr(
        "daily_limits._leetcode_open.launch", lambda: opened.append("go")
    )
    root, _texts_drawn = popup(monkeypatch, _leetcode_report())
    cells = clickable(root)
    # Four cells of the earner row plus the row under "To extend".
    assert len(cells) == 5
    assert {str(w.options["cursor"]) for w in cells} == {"hand2"}
    for widget in cells:
        widget.bindings["<Button-1>"](object())
    assert opened == ["go"] * 5


def test_a_failed_leetcode_open_warns_in_the_popup(
    monkeypatch: pytest.MonkeyPatch,
    roots: list[FakeWidget],
    caplog: pytest.LogCaptureFixture,
) -> None:
    del roots
    monkeypatch.setattr("daily_limits._leetcode_open.launch", lambda: "no problem")
    root, _texts_drawn = popup(monkeypatch, _leetcode_report())
    clickable(root)[0].bindings["<Button-1>"](object())
    assert dict(texts(root))["⚠"] == tok.WARNING
    assert "no problem" in caplog.text
