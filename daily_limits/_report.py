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
    from datetime import date

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


def _status(item: Earner, answer: int | None) -> Status:
    if answer is None:
        return "unknown"
    return "todo" if _compat.units_left(item, answer) else "done"


def _todo(resolution: Resolution) -> list[TodoRow]:
    """Not-done earners in registry order, each with the cumulative shutdown."""
    rows: list[TodoRow] = []
    shutdown = resolution.shutdown_minutes
    for term in resolution.terms:
        item: Earner = term.earner
        if term.answer is not None and not _compat.units_left(item, term.answer):
            continue
        shutdown = min(
            _compat.shutdown_ceiling(resolution.day),
            shutdown + _compat.shutdown_left(item, term.answer, resolution.day),
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


def _resolve(day: date, moment: datetime) -> Resolution:
    """Resolve ``day`` as seen at ``moment``, its penalties delayed by maturity.

    Only today and the current gaming day are ever resolved here.
    """
    answers = _answers.answers_for(day, moment)
    first_paid = _answers.first_credits(day)
    if first_paid is None:
        return earned_time.resolve(answers, day=day)
    return earned_time.resolve(answers, day=day, first_credits=first_paid)


def build(now: datetime | None = None) -> Report:
    """Resolve today (and the gaming day) into the contract; reads only."""
    moment = (now or datetime.now(tz=UTC)).astimezone()
    day = moment.date()
    resolution = _resolve(day, moment)
    # Before 06:00 the enforcer still bills yesterday: resolve that day's budget
    # so it and ``used_minutes`` describe the same gaming day.
    game_day = _answers.gaming_day(moment)
    gaming = resolution if game_day == day else _resolve(game_day, moment)
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
                "status": _status(term.earner, term.answer),
                # A full day's worth, like gaming: the tutor's 4 blocks, not 1.
                "shutdown_minutes": _compat.shutdown_left(term.earner, 0, day),
                "gaming_minutes": _compat.gaming_most(term.earner),
            }
            for term in resolution.terms
        ],
        "todo": _todo(resolution),
    }
