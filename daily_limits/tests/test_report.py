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
    from daily_limits._answers import Answer

# The registry of the pinned test day; the tutor cutover switches it.
DAY = date(2026, 10, 9)
REGISTRY = _compat.earners(DAY)
NAMES = [item.name for item in REGISTRY]


def _full(item: object) -> int:
    """Units that finish ``item``: a capped gate's all (the tutor's 4), else 1."""
    most: int | None = getattr(item, "max_units", None)
    return most or 1


CONTRACT_KEYS = {"date", "generated_at", "shutdown", "gaming", "earners", "todo"}


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
