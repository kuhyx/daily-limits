# Copyright (c) 2026 Krzysztof Rudnicki
"""Shadow-week alerts: notifications at 60/30/10/5 left, the would-be-0 splash."""

from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING

import pytest

from daily_limits import _alerts, _leisure_now, _paths

if TYPE_CHECKING:
    from pathlib import Path

    from daily_limits._shadow import LeisureShadow

T0 = 1_792_000_000.0
MPV = _leisure_now.Reason(source="media", key="app:mpv", pid=42, label="Film — mpv")
YT = _leisure_now.Reason(
    source="focus", key="domain:youtube.com", pid=7, label="YouTube — Helium"
)
COUNTING = _leisure_now.Facts(state="leisure", paused_by=None, reasons=(MPV, YT))


def shadow(left: int | None, *, day: str = "2026-10-19") -> LeisureShadow:
    """A C5 block with ``left`` minutes left (``None``: no data)."""
    return {
        "day": day,
        "budget_minutes": None if left is None else 600,
        "used_minutes": None if left is None else 600 - max(left, 0),
        "left_minutes": None if left is None else max(left, 0),
        "would_block": left is not None and left <= 0,
        "sources": [],
    }


class Fakes:
    """Stand-in executables that log their argv; exit codes are settable."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.log = root / "calls.log"

    def make(self, name: str) -> str:
        path = self.root / name
        path.write_text(
            "#!/bin/bash\n"
            # One log line per call: a newline inside an argument becomes " ".
            'args="$*"\n'
            f'printf "%s\\n" "{name} ${{args//$\'\\n\'/ }}" >>"{self.log}"\n'
            f'exit "$(cat "{self.root}/{name}.rc" 2>/dev/null || echo 0)"\n',
            encoding="utf-8",
        )
        path.chmod(0o755)
        return str(path)

    def exit_code(self, name: str, code: int) -> None:
        (self.root / f"{name}.rc").write_text(str(code), encoding="utf-8")

    def calls(self, name: str) -> list[str]:
        if not self.log.exists():
            return []
        lines = self.log.read_text(encoding="utf-8").splitlines()
        return [line for line in lines if line.startswith(f"{name} ")]


@pytest.fixture
def fakes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Fakes:
    root = tmp_path / "fakes"
    root.mkdir()
    made = Fakes(root)
    monkeypatch.setattr(_paths, "NOTIFY_SEND", made.make("notify-send"))
    monkeypatch.setattr(_paths, "SYSTEMD_RUN", made.make("systemd-run"))
    monkeypatch.setattr(_paths, "SYSTEMCTL", made.make("systemctl"))
    made.exit_code("systemctl", 3)  # is-active: inactive
    for name in ("DISPLAY", "XAUTHORITY", "PYTHONPATH", "DAILY_LIMITS_CACHE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("LEISURE_WATCH_NOW", raising=False)
    return made


def state() -> dict[str, object]:
    loaded: dict[str, object] = json.loads(
        _paths.ALERT_STATE_FILE.read_text(encoding="utf-8")
    )
    return loaded


def test_no_data_does_nothing(fakes: Fakes) -> None:
    _alerts.tick(shadow(None), COUNTING, now=T0)
    assert fakes.calls("notify-send") == []
    assert not _paths.ALERT_STATE_FILE.exists()


def test_each_threshold_fires_once_per_day(fakes: Fakes) -> None:
    for left in (65, 60, 58, 30, 29, 25, 8, 4, 3):
        _alerts.tick(shadow(left), COUNTING, now=T0)
    sent = fakes.calls("notify-send")
    assert len(sent) == 4
    # A jump from 25 straight to 8 says 10, once, and marks 10 done too.
    assert [line.split(" ")[7] for line in sent] == ["60", "30", "10", "5"]
    assert state() == {"day": "2026-10-19", "notified": [5, 10, 30, 60]}
    assert fakes.calls("systemd-run") == []


def test_the_notification_says_shadow_and_what_counts(fakes: Fakes) -> None:
    _alerts.tick(shadow(30), COUNTING, now=T0)
    (line,) = fakes.calls("notify-send")
    assert line.startswith("notify-send -u critical -a daily-limits ")
    assert "SHADOW: 30 min of leisure left" in line
    assert "nothing is blocked yet" in line
    assert "Counting now: Film — mpv, YouTube — Helium" in line


def test_a_new_gaming_day_starts_over(fakes: Fakes) -> None:
    _alerts.tick(shadow(5), COUNTING, now=T0)
    _alerts.tick(shadow(59, day="2026-10-20"), COUNTING, now=T0)
    assert len(fakes.calls("notify-send")) == 2
    assert state()["notified"] == [60]


def test_a_failed_notification_is_retried(
    fakes: Fakes, caplog: pytest.LogCaptureFixture
) -> None:
    fakes.exit_code("notify-send", 1)
    with caplog.at_level(logging.WARNING):
        _alerts.tick(shadow(10), COUNTING, now=T0)
    assert "notify-send failed" in caplog.text
    assert state()["notified"] == []
    fakes.exit_code("notify-send", 0)
    _alerts.tick(shadow(10), COUNTING, now=T0)
    assert state()["notified"] == [10, 30, 60]


def test_a_missing_notify_send_is_a_warning(
    fakes: Fakes, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    del fakes
    monkeypatch.setattr(_paths, "NOTIFY_SEND", "notify-send-absent")
    with caplog.at_level(logging.WARNING):
        _alerts.tick(shadow(10), COUNTING, now=T0)
    assert "notify-send-absent is not on PATH" in caplog.text


def test_would_block_launches_the_splash_every_15_min(
    fakes: Fakes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setenv("DAILY_LIMITS_CACHE", "/x/cache.json")
    _alerts.tick(shadow(0), COUNTING, now=T0)
    (launch,) = fakes.calls("systemd-run")
    assert launch == (
        "systemd-run --user --collect --quiet --unit=daily-limits-shadow-splash"
        " --setenv=DISPLAY=:99 --setenv=DAILY_LIMITS_CACHE=/x/cache.json"
        f" {sys.executable} -m daily_limits --shadow-splash"
    )
    # Over: no countdown notification, every threshold counts as passed.
    assert fakes.calls("notify-send") == []
    assert state() == {
        "day": "2026-10-19",
        "notified": [5, 10, 30, 60],
        "splash_at": T0,
    }
    _alerts.tick(shadow(0), COUNTING, now=T0 + 899)
    assert len(fakes.calls("systemd-run")) == 1
    _alerts.tick(shadow(0), COUNTING, now=T0 + 900)
    assert len(fakes.calls("systemd-run")) == 2


def test_a_splash_still_showing_is_not_doubled(fakes: Fakes) -> None:
    fakes.exit_code("systemctl", 0)  # is-active: active
    _alerts.tick(shadow(0), COUNTING, now=T0)
    assert fakes.calls("systemctl") == [
        "systemctl --user --quiet is-active daily-limits-shadow-splash.service"
    ]
    assert fakes.calls("systemd-run") == []
    assert state()["splash_at"] == T0


def test_a_failed_launch_is_retried_next_tick(
    fakes: Fakes, caplog: pytest.LogCaptureFixture
) -> None:
    fakes.exit_code("systemd-run", 1)
    with caplog.at_level(logging.WARNING):
        _alerts.tick(shadow(0), COUNTING, now=T0)
    assert "could not launch the shadow splash" in caplog.text
    assert "splash_at" not in state()
    fakes.exit_code("systemd-run", 0)
    _alerts.tick(shadow(0), COUNTING, now=T0 + 60)
    assert state()["splash_at"] == T0 + 60


def test_a_missing_systemd_run_is_a_warning(
    fakes: Fakes, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    del fakes
    monkeypatch.setattr(_paths, "SYSTEMD_RUN", "systemd-run-absent")
    monkeypatch.setattr(_paths, "SYSTEMCTL", "systemctl-absent")
    with caplog.at_level(logging.WARNING):
        _alerts.tick(shadow(0), COUNTING, now=T0)
    assert "systemd-run-absent is not on PATH" in caplog.text


def test_a_hung_helper_times_out(
    fakes: Fakes,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    del fakes
    monkeypatch.setattr(_alerts, "_TIMEOUT_S", 0.05)
    sleeper = tmp_path / "sleeper"
    sleeper.write_text("#!/bin/bash\nexec sleep 2\n", encoding="utf-8")
    sleeper.chmod(0o755)
    monkeypatch.setattr(_paths, "NOTIFY_SEND", str(sleeper))
    with caplog.at_level(logging.WARNING):
        _alerts.tick(shadow(5), COUNTING, now=T0)
    assert "notify-send failed" in caplog.text


@pytest.mark.parametrize(
    ("facts", "text"),
    [
        (COUNTING, "Film — mpv, YouTube — Helium"),
        (None, "unknown — leisure-watch is silent, so everything would count"),
        (
            _leisure_now.Facts(state="paused", paused_by="i3lock", reasons=()),
            "nothing (paused by i3lock)",
        ),
        (_leisure_now.Facts(state="free", paused_by=None, reasons=()), "nothing"),
    ],
)
def test_counting_now(facts: _leisure_now.Facts | None, text: str) -> None:
    assert _alerts.counting_now(facts) == text


def test_tick_defaults_to_the_wall_clock(
    fakes: Fakes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("daily_limits._alerts.time.time", lambda: T0 + 5)
    _alerts.tick(shadow(0), COUNTING)
    assert len(fakes.calls("systemd-run")) == 1
    assert state()["splash_at"] == T0 + 5
