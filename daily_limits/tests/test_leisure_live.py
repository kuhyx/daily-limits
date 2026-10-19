# Copyright (c) 2026 Krzysztof Rudnicki
"""Phase 2 dormant until live: ``leisure_active`` and the "Leisure" labels.

Whether the leisure budget is live is asked of ``earned_time.leisure_active``
for the 06:00 gaming day, through ``_paths.LEISURE_FROM_FILE``; the switch
file itself is never read here.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import earned_time
from earned_time import _leisure
import pytest

from daily_limits import _alerts, _cli, _paths, _render, _report, _sync
from daily_limits.tests import _samples
from daily_limits.tests._samples import at

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_no_test_reads_the_real_switch_file(hermetic: Path) -> None:
    switch = hermetic / "leisure_from"
    assert switch == _paths.LEISURE_FROM_FILE
    assert switch == _leisure.LEISURE_FROM_PATH
    assert not switch.exists()


def test_the_real_switch_file_is_earned_times() -> None:
    # The unpatched default is earned_time's own constant, never a copy.
    assert earned_time.LEISURE_FROM_PATH.as_posix() == "/etc/leisure-watch/leisure_from"


def test_dormant_without_a_switch_file() -> None:
    report = _report.build(at("2026-10-09T10:00"))
    assert report["leisure_active"] is False
    assert report["gaming"]["ceiling_minutes"] == earned_time.GAMING_CEILING_MINUTES


def test_live_on_the_switch_day_with_the_leisure_cap(
    leisure_on: Callable[[date], None],
) -> None:
    leisure_on(date(2026, 10, 9))
    report = _report.build(at("2026-10-09T10:00"))
    assert report["leisure_active"] is True
    assert report["gaming"]["ceiling_minutes"] == earned_time.LEISURE_CEILING_MINUTES


@pytest.mark.parametrize(("moment", "live"), [("05:59", False), ("06:00", True)])
def test_live_follows_the_gaming_day(
    leisure_on: Callable[[date], None], moment: str, live: bool
) -> None:
    leisure_on(date(2026, 10, 10))
    report = _report.build(at(f"2026-10-10T{moment}"))
    assert report["leisure_active"] is live


def test_summary_says_leisure_once_live() -> None:
    report = _samples.report(leisure_active=True, gaming_day="2026-10-08")
    text = _render.summary(report)
    assert "Leisure    3h budget, 1h34 used   [ceiling 8h]" in text
    assert "(leisure day 2026-10-08)" in text
    assert "+  25m leisure" in text
    assert "aming" not in text


def test_summary_still_says_gaming_while_dormant() -> None:
    text = _render.summary(_samples.report(gaming_day="2026-10-08"))
    assert "Gaming     3h budget" in text
    assert "(gaming day 2026-10-08)" in text
    assert "leisure" not in text.lower()


def test_sync_skips_the_shadow_alerts_once_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(shadow: object, facts: object) -> None:
        raise AssertionError((shadow, facts))

    synced: list[bool] = []
    monkeypatch.setattr(_report, "build", lambda: _samples.report(leisure_active=True))
    monkeypatch.setattr(_alerts, "tick", refuse)
    monkeypatch.setattr(
        _sync, "tick", lambda report, rebuild: synced.append(report["leisure_active"])
    )
    assert _cli.main(["--sync"]) == 0
    assert synced == [True]
