# Copyright (c) 2026 Krzysztof Rudnicki
"""The JSON contract: exact keys, numbers straight from earned_time."""

from __future__ import annotations

from datetime import date
import json
from typing import TYPE_CHECKING

import earned_time
import pytest

from daily_limits import _answers, _compat, _paths, _report
from daily_limits.tests._samples import at

if TYPE_CHECKING:
    from collections.abc import Callable

    from daily_limits._answers import Answer

# The registry of the pinned test day; the tutor cutover switches it.
DAY = date(2026, 10, 9)
REGISTRY = _compat.earners(DAY)
NAMES = [item.name for item in REGISTRY]


def _full(item: object) -> int:
    """Units that finish ``item``: a capped gate's all (the tutor's 4), else 1."""
    most: int | None = getattr(item, "max_units", None)
    return most or 1


CONTRACT_KEYS = {
    "date",
    "generated_at",
    "sick",
    "shutdown",
    "gaming",
    "earners",
    "todo",
}


def _answers_by_day(
    monkeypatch: pytest.MonkeyPatch, by_day: dict[date, dict[str, Answer]]
) -> list[date]:
    asked: list[date] = []

    def fake(day: date, moment: object) -> dict[str, Answer]:
        del moment
        asked.append(day)
        return by_day[day]

    monkeypatch.setattr(_answers, "answers_for", fake)
    return asked


@pytest.mark.parametrize(("minutes", "text"), [(0, "00:00"), (1250, "20:50")])
def test_hhmm(minutes: int, text: str) -> None:
    assert _report.hhmm(minutes) == text


def test_nothing_done_lists_every_earner_cumulatively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = date(2026, 10, 9)
    _answers_by_day(monkeypatch, {day: dict.fromkeys(NAMES, 0)})
    _paths.SCHEDULE_FILE.write_text("THU_SUN_MINUTES=1200\n", encoding="utf-8")
    _paths.PLAYTIME_STATE.write_text(
        json.dumps({"day_key": "2026-10-09", "seconds": 600}), encoding="utf-8"
    )
    report = _report.build(at("2026-10-09T10:00"))
    assert set(report) == CONTRACT_KEYS
    base = earned_time.base_for(day)
    ceiling = _compat.shutdown_ceiling(day)
    assert report["date"] == "2026-10-09"
    assert report["shutdown"] == {
        "applied": "20:00",
        "resolved": _report.hhmm(base.shutdown_minutes),
        "floor": _report.hhmm(base.shutdown_minutes),
        "ceiling": _report.hhmm(ceiling),
    }
    assert report["gaming"] == {
        "day": "2026-10-09",
        "budget_minutes": base.gaming_minutes,
        "used_minutes": 10,
        "ceiling_minutes": earned_time.GAMING_CEILING_MINUTES,
    }
    assert [row["status"] for row in report["earners"]] == ["todo"] * len(NAMES)
    running = base.shutdown_minutes
    expected = []
    for item in REGISTRY:
        running = min(ceiling, running + _compat.shutdown_left(item, 0, day))
        expected.append(
            {
                "name": item.name,
                "label": item.label,
                "status": "todo",
                "shutdown_after": _report.hhmm(running),
            }
        )
    assert report["todo"] == expected
    assert report["earners"][-1] == {
        "name": REGISTRY[-1].name,
        "label": REGISTRY[-1].label,
        "status": "todo",
        "shutdown_minutes": _compat.shutdown_left(REGISTRY[-1], 0, day),
        "gaming_minutes": _compat.gaming_left(REGISTRY[-1], 0),
    }


def test_done_and_unknown_earners(monkeypatch: pytest.MonkeyPatch) -> None:
    day = date(2026, 10, 9)
    answers: dict[str, Answer] = {item.name: _full(item) for item in REGISTRY}
    answers[NAMES[0]] = None
    _answers_by_day(monkeypatch, {day: answers})
    report = _report.build(at("2026-10-09T10:00"))
    statuses = [row["status"] for row in report["earners"]]
    assert statuses == ["unknown"] + ["done"] * (len(NAMES) - 1)
    assert [(row["name"], row["status"]) for row in report["todo"]] == [
        (NAMES[0], "unknown")
    ]
    assert report["shutdown"]["applied"] is None
    assert report["gaming"]["used_minutes"] is None


def test_before_six_the_gaming_block_is_yesterdays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    today, yesterday = date(2026, 10, 9), date(2026, 10, 8)
    asked = _answers_by_day(
        monkeypatch,
        {today: dict.fromkeys(NAMES, 0), yesterday: dict.fromkeys(NAMES, 1)},
    )
    _paths.PLAYTIME_STATE.write_text(
        json.dumps({"day_key": "2026-10-08", "seconds": 7200}), encoding="utf-8"
    )
    report = _report.build(at("2026-10-09T03:00"))
    assert asked == [today, yesterday]
    assert report["date"] == "2026-10-09"
    # The hermetic ledgers are empty: no gate has paid out, so first_credits
    # holds None for each one (only a confirmed gate stays penalised).
    yesterday_all_done = earned_time.resolve(
        dict.fromkeys(NAMES, 1),
        day=yesterday,
        first_credits=dict.fromkeys(
            [item.name for item in _compat.earners(yesterday)], None
        ),
    )
    assert report["gaming"]["day"] == "2026-10-08"
    assert report["gaming"]["budget_minutes"] == yesterday_all_done.gaming_minutes
    assert report["gaming"]["used_minutes"] == 120
    # Shutdown is still today's, where nothing is done.
    assert all(row["status"] == "todo" for row in report["earners"])


def test_build_defaults_to_now(monkeypatch: pytest.MonkeyPatch) -> None:
    def nothing(day: date, moment: object) -> dict[str, Answer]:
        del moment
        return {item.name: 0 for item in _compat.earners(day)}

    monkeypatch.setattr(_answers, "answers_for", nothing)
    report = _report.build()
    assert report["generated_at"] > 0
    today = date.fromisoformat(report["date"])
    assert len(report["earners"]) == len(_compat.earners(today))


def _expected_todo(day: date, start: int, *, sick: bool) -> list[int]:
    """Cumulative shutdown per earner from the earned ``start`` (nothing done)."""
    ceiling = _compat.shutdown_ceiling(day)
    steps: list[int] = []
    running = start
    for item in _compat.earners(day):
        left = (
            _compat.gaming_left(item, 0)
            if sick
            else _compat.shutdown_left(item, 0, day)
        )
        running = min(ceiling, running + left)
        steps.append(running)
    return steps


def test_normal_day_is_not_sick(monkeypatch: pytest.MonkeyPatch) -> None:
    _answers_by_day(monkeypatch, {DAY: dict.fromkeys(NAMES, 0)})
    report = _report.build(at("2026-10-09T10:00"))
    assert report["sick"] is False


def test_sick_day_lifts_shutdown_and_every_todo_step(
    monkeypatch: pytest.MonkeyPatch, sick_pool: Callable[[date], None]
) -> None:
    _answers_by_day(monkeypatch, {DAY: dict.fromkeys(NAMES, 0)})
    sick_pool(DAY)
    report = _report.build(at("2026-10-09T10:00"))
    base = earned_time.base_for(DAY).shutdown_minutes
    assert report["sick"] is True
    # Nothing done: the base is below the 20:00 floor, so it is lifted to it.
    assert base < earned_time.SICK_SHUTDOWN_FLOOR_MINUTES
    assert report["shutdown"]["resolved"] == "20:00"
    # ``floor`` stays the unlifted base: it is what an unsick day starts from.
    assert report["shutdown"]["floor"] == _report.hhmm(base)
    assert [row["shutdown_after"] for row in report["todo"]] == [
        _report.hhmm(step)
        for step in _expected_todo(
            DAY, earned_time.SICK_SHUTDOWN_FLOOR_MINUTES, sick=True
        )
    ]
    # Stacked (earned_time 0.13.0): the first step is 20:00 + its gaming pay.
    first = earned_time.SICK_SHUTDOWN_FLOOR_MINUTES + _compat.gaming_left(
        _compat.earners(DAY)[0], 0
    )
    assert report["todo"][0]["shutdown_after"] == _report.hhmm(first)


def test_sick_day_does_not_change_gaming(
    monkeypatch: pytest.MonkeyPatch, sick_pool: Callable[[date], None]
) -> None:
    _answers_by_day(monkeypatch, {DAY: dict.fromkeys(NAMES, 0)})
    plain = _report.build(at("2026-10-09T10:00"))
    sick_pool(DAY)
    sick = _report.build(at("2026-10-09T10:00"))
    assert sick["gaming"] == plain["gaming"]
    assert sick["earners"] == plain["earners"]


def test_before_six_the_resolved_day_is_asked_not_today(
    monkeypatch: pytest.MonkeyPatch, sick_pool: Callable[[date], None]
) -> None:
    today, yesterday = date(2026, 10, 9), date(2026, 10, 8)
    _answers_by_day(
        monkeypatch,
        {today: dict.fromkeys(NAMES, 0), yesterday: dict.fromkeys(NAMES, 0)},
    )
    sick_pool(yesterday)
    # 03:00: shutdown is still today's (not sick); the gaming day is yesterday.
    report = _report.build(at("2026-10-09T03:00"))
    assert report["sick"] is False
    assert report["gaming"]["day"] == "2026-10-08"
