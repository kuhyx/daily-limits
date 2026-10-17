# Copyright (c) 2026 Krzysztof Rudnicki
"""Launching ``sickdays gui``: detached, resolved on PATH, never a crash."""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from daily_limits import _sick_picker

if TYPE_CHECKING:
    import pytest


def test_launch_starts_the_resolved_executable_detached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_popen(argv: list[str], **kwargs: object) -> object:
        calls.append((argv, kwargs))
        return object()

    monkeypatch.setattr(
        "daily_limits._sick_picker.shutil.which", lambda _name: "/x/sickdays"
    )
    monkeypatch.setattr("daily_limits._sick_picker.subprocess.Popen", fake_popen)
    assert _sick_picker.launch() is None
    assert calls == [
        (
            ["/x/sickdays", "gui"],
            {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "start_new_session": True,
            },
        )
    ]


def test_launch_without_sickdays_warns(caplog: pytest.LogCaptureFixture) -> None:
    # The hermetic fixture leaves no sickdays on the resolved name.
    with caplog.at_level(logging.WARNING):
        assert _sick_picker.launch() == "sickdays is not installed"
    assert "not on PATH" in caplog.text


def test_launch_survives_a_popen_oserror(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(*_args: object, **_kwargs: object) -> object:
        msg = "exec format error"
        raise OSError(msg)

    monkeypatch.setattr(
        "daily_limits._sick_picker.shutil.which", lambda _name: "/x/sickdays"
    )
    monkeypatch.setattr("daily_limits._sick_picker.subprocess.Popen", broken)
    with caplog.at_level(logging.WARNING):
        assert _sick_picker.launch() == "sickdays is not installed"
    assert "exec format error" in caplog.text
