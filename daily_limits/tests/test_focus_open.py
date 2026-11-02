# Copyright (c) 2026 Krzysztof Rudnicki
"""Launching ``focus_project.open``: detached, system python, never a crash."""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from daily_limits import _focus_open

if TYPE_CHECKING:
    import pytest


def test_launch_starts_the_module_detached_under_the_system_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_popen(argv: list[str], **kwargs: object) -> object:
        calls.append((argv, kwargs))
        return object()

    monkeypatch.setattr("daily_limits._focus_open.subprocess.Popen", fake_popen)
    assert _focus_open.launch() is None
    assert calls == [
        (
            ["/usr/bin/python3", "-m", "focus_project.open"],
            {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "start_new_session": True,
            },
        )
    ]


def test_launch_survives_a_popen_oserror(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(*_args: object, **_kwargs: object) -> object:
        msg = "no such file"
        raise OSError(msg)

    monkeypatch.setattr("daily_limits._focus_open.subprocess.Popen", broken)
    with caplog.at_level(logging.WARNING):
        assert _focus_open.launch() == "could not open the focus work"
    assert "could not start focus_project.open" in caplog.text
