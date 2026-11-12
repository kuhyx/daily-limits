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
  test reaches the network or declares a rest day; the crdt-sync passphrase
  is a temp file holding ``test-passphrase`` (never the real
  ``~/.config/crdt-sync/password``), Argon2id runs at its lowest cost and
  the once-per-process e2e copy memo is cleared;
* the sick-day picker resolves to a name that is on no PATH, so no test
  starts the real ``sickdays gui``;
* the shadow alerts' state lives in ``tmp_path`` and notify-send,
  systemd-run, systemctl and xrandr resolve to names on no PATH, so no test
  notifies, launches a splash or asks the real X server;
* ``tkinter.Tk`` raises: no test may open a real window (GUI tests install a
  fake tk module instead);
* the leisure switch file (``/etc/leisure-watch/leisure_from``) is a missing
  file under ``tmp_path`` for both daily-limits and earned_time's own
  ``resolve()`` (``leisure_on`` writes it), so no test reads the real one.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

from crdt_sync import Argon2Params, reset_e2e_copy_memo
from earned_time import _leisure
import pytest
import sickdays
from sickdays import _paths as sick_paths

from daily_limits import _gui, _paths, _sick_picker, _sync_client
from daily_limits.tests._fake_tk import FakeWidget

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
    monkeypatch.setenv("FOCUS_PROJECT_DATA", str(tmp_path / "focus_project"))
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
    password = tmp_path / "crdt-sync-password"
    password.write_text("test-passphrase\n", encoding="utf-8")
    monkeypatch.setattr(_paths, "PASSWORD_FILE", password)
    monkeypatch.setattr(
        _sync_client, "ARGON2", Argon2Params(memory_kib=8, iterations=1)
    )
    reset_e2e_copy_memo()
    monkeypatch.setattr(_sick_picker, "EXECUTABLE", "sickdays-absent-in-tests")
    monkeypatch.setattr(_paths, "ALERT_STATE_FILE", tmp_path / "alerts" / "a.json")
    for name in ("NOTIFY_SEND", "SYSTEMD_RUN", "SYSTEMCTL", "XRANDR", "PKILL"):
        monkeypatch.setattr(_paths, name, f"{name.lower()}-absent-in-tests")
    # focus_project is a soft import: None here means "not installed", so no
    # test reads the real projects.json (a test that needs it installs a fake).
    monkeypatch.setitem(sys.modules, "focus_project", None)
    monkeypatch.delenv("DAILY_LIMITS_CACHE", raising=False)
    monkeypatch.delenv("LEISURE_WATCH_NOW", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr("tkinter.Tk", _no_tk)
    monkeypatch.setattr(sick_paths, "LOG_PATH", sick_paths.Paths.under(tmp_path).log)
    # Both readers of the switch file: ours (passed as ``path=``) and the one
    # earned_time.resolve() looks up at call time for the base and the cap.
    switch = tmp_path / "leisure_from"
    monkeypatch.setattr(_paths, "LEISURE_FROM_FILE", switch)
    monkeypatch.setattr(_leisure, "LEISURE_FROM_PATH", switch)
    return tmp_path


@pytest.fixture
def leisure_on(hermetic: Path) -> Callable[[date], None]:
    """Write the (temp) switch file: the leisure budget is live from ``day``."""

    def switch_on(day: date) -> None:
        (hermetic / "leisure_from").write_text(f"{day.isoformat()}\n", encoding="utf-8")

    return switch_on


@pytest.fixture
def sick_pool(hermetic: Path) -> Callable[[date], None]:
    """Mark a day sick in the (temp) pool, through the real ``sickdays`` writer."""
    paths = sick_paths.Paths.under(hermetic)

    def mark(day: date) -> None:
        sickdays.add_sick_day(day, is_free=lambda _day: False, paths=paths, now=day)

    return mark


@pytest.fixture
def roots(monkeypatch: pytest.MonkeyPatch) -> list[FakeWidget]:
    """Install the fake tk; returns the roots it creates."""
    created: list[FakeWidget] = []

    def make_root(**options: object) -> FakeWidget:
        root = FakeWidget()
        root.options.update(options)
        created.append(root)
        return root

    fake_tk = SimpleNamespace(
        Tk=make_root, Frame=FakeWidget, Label=FakeWidget, Button=FakeWidget
    )
    fake_font = SimpleNamespace(
        nametofont=lambda _name: SimpleNamespace(actual=lambda _key: "Fake Sans")
    )
    monkeypatch.setattr(_gui, "tk", fake_tk)
    monkeypatch.setattr(_gui, "tkfont", fake_font)
    return created
