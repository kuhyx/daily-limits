# Copyright (c) 2026 Krzysztof Rudnicki
"""Today's limits as the JSON contract the i3blocks block and the GUI read.

Every number comes from ``earned_time`` (the registry and its ``resolve``);
nothing here hard-codes a minute, so a registry bump changes the output with
no code change. The contract's keys are fixed -- an i3blocks script reads them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, Literal, TypedDict

import earned_time

from daily_limits import _answers, _compat, _paths, _sources

if TYPE_CHECKING:
    from earned_time import Earner, Resolution

Status = Literal["done", "todo", "unknown"]
_MINUTES_PER_HOUR: Final = 60


class Shutdown(TypedDict):
    """``shutdown`` block: HH:MM strings; ``applied`` is null when unreadable."""

    applied: str | None
    resolved: str
    floor: str
    ceiling: str


class Gaming(TypedDict):
    """``gaming`` block, for the enforcer's gaming day (06:00 to 06:00).

    ``day`` is the calendar date before 06:00; ``used_minutes`` is null when
    it cannot be read.
    """

    day: str
    budget_minutes: int
    used_minutes: int | None
    ceiling_minutes: int


class EarnerRow(TypedDict):
    """One ``earners`` entry, in registry order."""

    name: str
    label: str
    status: Status
    shutdown_minutes: int
    gaming_minutes: int


class TodoRow(TypedDict):
    """One ``todo`` entry: where shutdown lands once this one is done too.

    ``status`` tells a plain "not yet" from "could not check".
    """

    name: str
    label: str
    status: Literal["todo", "unknown"]
    shutdown_after: str


class Report(TypedDict):
    """The whole contract."""

    date: str
    generated_at: int
    shutdown: Shutdown
    gaming: Gaming
    earners: list[EarnerRow]
    todo: list[TodoRow]


def hhmm(minutes: int) -> str:
    """Minutes after midnight as ``HH:MM``."""
    hours, rest = divmod(minutes, _MINUTES_PER_HOUR)
    return f"{hours:02d}:{rest:02d}"


def _status(answer: int | None) -> Status:
    if answer is None:
        return "unknown"
    return "done" if answer > 0 else "todo"


def _todo(resolution: Resolution) -> list[TodoRow]:
    """Not-done earners in registry order, each with the cumulative shutdown."""
    rows: list[TodoRow] = []
    shutdown = resolution.shutdown_minutes
    for term in resolution.terms:
        if term.answer is not None and term.answer > 0:
            continue
        item: Earner = term.earner
        shutdown = min(
            _compat.shutdown_ceiling(resolution.day),
            shutdown + _compat.shutdown_minutes(item, resolution.day),
        )
        rows.append(
            {
                "name": item.name,
                "label": item.label,
                "status": "unknown" if term.answer is None else "todo",
                "shutdown_after": hhmm(shutdown),
            }
        )
    return rows


def build(now: datetime | None = None) -> Report:
    """Resolve today (and the gaming day) into the contract; reads only."""
    moment = (now or datetime.now(tz=UTC)).astimezone()
    day = moment.date()
    resolution = earned_time.resolve(_answers.answers_for(day, moment), day=day)
    # Before 06:00 the enforcer still bills yesterday: resolve that day's budget
    # so it and ``used_minutes`` describe the same gaming day.
    game_day = _answers.gaming_day(moment)
    gaming = (
        resolution
        if game_day == day
        else earned_time.resolve(_answers.answers_for(game_day, moment), day=game_day)
    )
    applied = _sources.applied_shutdown(_paths.SCHEDULE_FILE, day)
    return {
        "date": day.isoformat(),
        "generated_at": int(moment.timestamp()),
        "shutdown": {
            "applied": None if applied is None else hhmm(applied),
            "resolved": hhmm(resolution.shutdown_minutes),
            "floor": hhmm(resolution.base.shutdown_minutes),
            "ceiling": hhmm(_compat.shutdown_ceiling(day)),
        },
        "gaming": {
            "day": game_day.isoformat(),
            "budget_minutes": gaming.gaming_minutes,
            "used_minutes": _sources.gaming_used_minutes(
                _paths.PLAYTIME_STATE, game_day
            ),
            "ceiling_minutes": earned_time.GAMING_CEILING_MINUTES,
        },
        "earners": [
            {
                "name": term.earner.name,
                "label": term.earner.label,
                "status": _status(term.answer),
                "shutdown_minutes": _compat.shutdown_minutes(term.earner, day),
                "gaming_minutes": term.earner.gaming_minutes,
            }
            for term in resolution.terms
        ],
        "todo": _todo(resolution),
    }
