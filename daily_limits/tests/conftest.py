# Copyright (c) 2026 Krzysztof Rudnicki
"""Hermetic defaults for every test.

Autouse, so no test can forget them:

* every path (ledgers under HOME, the HMAC key, the shutdown schedule, the
  enforcer's playtime state) points into ``tmp_path`` -- the real files are
  never read;
* ``$XDG_RUNTIME_DIR`` is a temp dir, so ``--write-cache`` never touches
  /run/user;
* ``tkinter.Tk`` raises: no test may open a real window (GUI tests install a
  fake tk module instead).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from daily_limits import _paths

if TYPE_CHECKING:
    from pathlib import Path

TEST_KEY = b"test-hmac-key"


def _no_tk(*_args: object, **_kwargs: object) -> None:
    msg = "a test tried to open a real Tk window"
    raise AssertionError(msg)


@pytest.fixture(autouse=True)
def hermetic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect every path the app reads into ``tmp_path``."""
    home = tmp_path / "home"
    home.mkdir()
    key = tmp_path / "hmac.key"
    key.write_bytes(TEST_KEY)
    runtime = tmp_path / "run"
    runtime.mkdir()
    monkeypatch.setattr(_paths, "HOME", home)
    monkeypatch.setattr(_paths, "KEY_FILE", key)
    monkeypatch.setattr(_paths, "SCHEDULE_FILE", tmp_path / "shutdown-schedule.conf")
    monkeypatch.setattr(_paths, "PLAYTIME_STATE", tmp_path / "playtime_state.json")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr("tkinter.Tk", _no_tk)
    return tmp_path
