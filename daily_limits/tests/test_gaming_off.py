# Copyright (c) 2026 Krzysztof Rudnicki
"""Gaming is not limited from 2026-11-16: the budget is neither built nor drawn."""

from __future__ import annotations

from datetime import date
import json
from typing import TYPE_CHECKING

import earned_time
import pytest

from daily_limits import (
    _alerts,
    _answers,
    _cli,
    _compat,
    _leisure_now,
    _render,
    _report,
    _splash,
)
from daily_limits import _glyphs as gl
from daily_limits.tests import _samples
from daily_limits.tests._fake_tk import FakeWidget, popup
from daily_limits.tests.test_splash import write_cache

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from daily_limits._answers import Answer

OFF = date(2026, 11, 16)


def _nothing_done(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(day: date, moment: object) -> dict[str, Answer]:
        del moment
        return {item.name: 0 for item in _compat.earners(day)}

    monkeypatch.setattr(_answers, "answers_for", fake)


@pytest.mark.parametrize(
    ("moment", "enforced"),
    [
        ("2026-11-16T10:00", False),
        ("2026-11-17T01:00", False),  # gaming day is still 11-16
        ("2026-11-16T05:00", True),  # the gaming day is 11-15: still limited
        ("2026-10-09T10:00", True),
    ],
)
def test_flag_follows_the_gaming_day(
    monkeypatch: pytest.MonkeyPatch, moment: str, enforced: bool
) -> None:
    _nothing_done(monkeypatch)
    report = _report.build(_samples.at(moment))
    assert report["gaming_enforced"] is enforced


def test_sick_todo_steps_pay_shutdown_not_gaming(
    monkeypatch: pytest.MonkeyPatch, sick_pool: Callable[[date], None]
) -> None:
    _nothing_done(monkeypatch)
    sick_pool(OFF)
    # The unified ladder makes the two pays equal today; poison gaming pay so
    # only the shutdown pay can produce the expected step.
    monkeypatch.setattr(_compat, "gaming_left", lambda item, answer: 999)
    report = _report.build(_samples.at("2026-11-16T10:00"))
    first = _compat.earners(OFF)[0]
    start = report["shutdown"]["resolved"]
    hours, minutes = map(int, start.split(":"))
    expected = min(
        _compat.shutdown_ceiling(OFF),
        hours * 60 + minutes + _compat.shutdown_left(first, 0, OFF),
    )
    assert report["todo"][0]["shutdown_after"] == _report.hhmm(expected)
    assert earned_time.gaming_enforced(OFF) is False


def test_summary_has_no_budget_line_or_amount() -> None:
    text = _render.summary(_samples.report(gaming_enforced=False))
    for word in ("Gaming", "Leisure", "budget", "used", "gaming"):
        assert word not in text
    assert "  [ ] E1          +   1h shutdown   not yet\n" in text
    assert "25m" not in text
    assert "Shutdown   20:00 applied" in text


def test_popup_draws_no_budget(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    _root, drawn = popup(monkeypatch, _samples.report(gaming_enforced=False))
    shown = [text for text, _fg in drawn]
    assert "⏻ 20:00" in shown
    assert shown.count("⏻ +1h") == 2
    assert not [t for t in shown if gl.GAMING in t or gl.LEISURE in t]
    assert not [t for t in shown if t.startswith(gl.CEILING)]


def test_no_shadow_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks: list[object] = []
    monkeypatch.setattr(_alerts, "tick", lambda *args: ticks.append(args))
    monkeypatch.setattr(_leisure_now, "read", lambda: None)
    _cli._shadow_alerts(_samples.report(gaming_enforced=False))
    assert ticks == []
    _cli._shadow_alerts(_samples.report())
    assert len(ticks) == 1


def test_no_splash(tmp_path: Path) -> None:
    cache = write_cache(tmp_path / "c.json")
    assert _splash.read_shadow(cache) is not None
    report = json.loads(cache.read_text(encoding="utf-8"))
    cache.write_text(json.dumps({**report, "gaming_enforced": False}), encoding="utf-8")
    assert _splash.read_shadow(cache) is None
