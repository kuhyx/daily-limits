# Copyright (c) 2026 Krzysztof Rudnicki
"""The read-only readers: the applied schedule and the enforcer's playtime."""

from __future__ import annotations

from datetime import date
import json
from typing import TYPE_CHECKING

import pytest

from daily_limits import _sources

if TYPE_CHECKING:
    from pathlib import Path

FRIDAY = date(2026, 10, 9)
MONDAY = date(2026, 10, 5)

SCHEDULE = """# Shutdown schedule configuration
MON_WED_MINUTES=1200
THU_SUN_MINUTES=1260
MORNING_END_MINUTES=300
MON_WED_HOUR=20
not a key line
"""


def _schedule(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "schedule.conf"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(("day", "expected"), [(FRIDAY, 1260), (MONDAY, 1200)])
def test_applied_shutdown_picks_the_range_covering_the_weekday(
    tmp_path: Path, day: date, expected: int
) -> None:
    assert _sources.applied_shutdown(_schedule(tmp_path, SCHEDULE), day) == expected


def test_applied_shutdown_accepts_a_single_day_key_and_quotes(tmp_path: Path) -> None:
    path = _schedule(tmp_path, 'FRI_MINUTES="1290"\n')
    assert _sources.applied_shutdown(path, FRIDAY) == 1290


def test_applied_shutdown_skips_unknown_day_names(tmp_path: Path) -> None:
    path = _schedule(tmp_path, "XYZ_MINUTES=1\nTHU_XYZ_MINUTES=2\nTHU_SUN_MINUTES=3\n")
    assert _sources.applied_shutdown(path, FRIDAY) == 3


def test_applied_shutdown_unparsable_value_is_unknown(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = _schedule(tmp_path, "THU_SUN_MINUTES=late\n")
    assert _sources.applied_shutdown(path, FRIDAY) is None
    assert "Unparsable" in caplog.text


def test_applied_shutdown_without_a_covering_key_is_unknown(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = _schedule(tmp_path, "MON_WED_MINUTES=1200\n")
    assert _sources.applied_shutdown(path, FRIDAY) is None
    assert "covers FRI" in caplog.text


def test_applied_shutdown_missing_file_is_unknown(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    assert _sources.applied_shutdown(tmp_path / "absent.conf", FRIDAY) is None
    assert "Cannot read the shutdown schedule" in caplog.text


def _state(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "playtime_state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_used_minutes_for_the_same_gaming_day(tmp_path: Path) -> None:
    path = _state(tmp_path, {"day_key": "2026-10-09", "seconds": 5448.9})
    assert _sources.gaming_used_minutes(path, FRIDAY) == 90


def test_used_minutes_from_an_earlier_day_is_zero(tmp_path: Path) -> None:
    path = _state(tmp_path, {"day_key": "2026-10-08", "seconds": 999.0})
    assert _sources.gaming_used_minutes(path, FRIDAY) == 0


def test_used_minutes_from_a_later_day_is_unknown(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = _state(tmp_path, {"day_key": "2026-10-10", "seconds": 60})
    assert _sources.gaming_used_minutes(path, FRIDAY) is None
    assert "ahead of" in caplog.text


@pytest.mark.parametrize(
    "payload",
    [[1, 2], {"day_key": "2026-10-09"}, {"seconds": 5}, {"day_key": 1, "seconds": 5}],
)
def test_used_minutes_malformed_state_is_unknown(
    tmp_path: Path, payload: object, caplog: pytest.LogCaptureFixture
) -> None:
    assert _sources.gaming_used_minutes(_state(tmp_path, payload), FRIDAY) is None
    assert "has no seconds/day_key" in caplog.text


def test_used_minutes_unreadable_or_invalid_state_is_unknown(tmp_path: Path) -> None:
    assert _sources.gaming_used_minutes(tmp_path / "absent.json", FRIDAY) is None
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert _sources.gaming_used_minutes(bad, FRIDAY) is None
