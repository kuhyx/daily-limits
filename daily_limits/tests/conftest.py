# Copyright (c) 2026 Krzysztof Rudnicki
"""Hermetic defaults for every test.

Autouse, so no test can forget them:

* every path (ledgers under HOME, the HMAC key, the shutdown schedule, the
  enforcer's playtime state) points into ``tmp_path`` -- the real files are
  never read;
* the sick-day pool is an empty file under ``tmp_path`` (``sick_pool`` marks
  days in it) -- ``~/.local/share/sickdays`` is never read;
* ``$XDG_RUNTIME_DIR`` is a temp dir, so ``--write-cache`` never touches
  /run/user;
* ``--sync``'s state lives in ``tmp_path``, screen-locker's interpreter is a
  path that does not exist, and building a real Firebase client fails: no
  test reaches the network or declares a rest day;
* the sick-day picker resolves to a name that is on no PATH, so no test
  starts the real ``sickdays gui``;
* ``tkinter.Tk`` raises: no test may open a real window (GUI tests install a
  fake tk module instead).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import sickdays
from sickdays import _paths as sick_paths

from daily_limits import _paths, _sick_picker, _sync_client

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date
    from pathlib import Path

TEST_KEY = b"test-hmac-key"


def _no_tk(*_args: object, **_kwargs: object) -> None:
    msg = "a test tried to open a real Tk window"
    raise AssertionError(msg)


def _no_firebase(*_args: object, **_kwargs: object) -> None:
    msg = "a test tried to build a real Firebase client"
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
    state = tmp_path / "state"
    monkeypatch.setattr(_paths, "STATE_DIR", state)
    monkeypatch.setattr(_paths, "DEVICE_ID_FILE", state / ".device_id")
    monkeypatch.setattr(_paths, "PUBLISH_STATE_FILE", state / "publish_state.json")
    monkeypatch.setattr(_paths, "HANDLED_FILE", state / "handled_requests.json")
    monkeypatch.setattr(_paths, "SCREEN_LOCKER_PYTHON", str(tmp_path / "no-python"))
    monkeypatch.setattr(_sync_client, "firebase_client_for", _no_firebase)
    monkeypatch.setattr(_sick_picker, "EXECUTABLE", "sickdays-absent-in-tests")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr("tkinter.Tk", _no_tk)
    monkeypatch.setattr(sick_paths, "LOG_PATH", sick_paths.Paths.under(tmp_path).log)
    return tmp_path


@pytest.fixture
def sick_pool(hermetic: Path) -> Callable[[date], None]:
    """Mark a day sick in the (temp) pool, through the real ``sickdays`` writer."""
    paths = sick_paths.Paths.under(hermetic)

    def mark(day: date) -> None:
        sickdays.add_sick_day(day, is_free=lambda _day: False, paths=paths, now=day)

    return mark
