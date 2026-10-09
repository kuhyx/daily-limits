# Copyright (c) 2026 Krzysztof Rudnicki
"""Read-only facts from the other apps' files: the schedule and playtime.

Every reader returns ``None`` for "could not check" and logs why -- never a
guessed zero. Nothing here writes, and nothing talks to a daemon.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

_logger: Final = logging.getLogger(__name__)

_DAYS: Final = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
# ``MON_WED_MINUTES=1200`` (a day range) or ``FRI_MINUTES=1260`` (one day).
_DAY_KEY: Final = re.compile(r"^([A-Z]{3})(?:_([A-Z]{3}))?_MINUTES$")


def _covers(first: str, last: str | None, weekday: int) -> bool:
    if first not in _DAYS or (last is not None and last not in _DAYS):
        return False
    start = _DAYS.index(first)
    end = _DAYS.index(last) if last is not None else start
    return start <= weekday <= end


def applied_shutdown(schedule: Path, day: date) -> int | None:
    """Today's shutdown from screen-locker's schedule, minutes after midnight.

    Picks the ``*_MINUTES`` key whose weekday (range) covers ``day``;
    ``MORNING_END_MINUTES`` and the legacy ``*_HOUR`` keys never match.
    """
    try:
        text = schedule.read_text(encoding="utf-8")
    except OSError as exc:
        _logger.warning("Cannot read the shutdown schedule %s (%s)", schedule, exc)
        return None
    for line in text.splitlines():
        key, sep, value = line.strip().partition("=")
        found = _DAY_KEY.match(key)
        if not sep or found is None:
            continue
        if _covers(found.group(1), found.group(2), day.weekday()):
            try:
                return int(value.strip().strip("\"'"))
            except ValueError:
                _logger.warning("Unparsable %s=%r in %s", key, value, schedule)
                return None
    _logger.warning("No *_MINUTES key in %s covers %s", schedule, _DAYS[day.weekday()])
    return None


def gaming_used_minutes(state: Path, day: date) -> int | None:
    """Minutes the enforcer billed to gaming day ``day`` (06:00 to 06:00).

    A state still stamped with an earlier day means nothing was played yet on
    ``day``: 0. Unreadable or malformed: ``None``.
    """
    try:
        raw = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _logger.warning("Cannot read the playtime state %s (%s)", state, exc)
        return None
    seconds = raw.get("seconds") if isinstance(raw, dict) else None
    day_key = raw.get("day_key") if isinstance(raw, dict) else None
    if not isinstance(seconds, int | float) or not isinstance(day_key, str):
        _logger.warning("Playtime state %s has no seconds/day_key", state)
        return None
    if day_key < day.isoformat():
        return 0
    if day_key > day.isoformat():
        _logger.warning("Playtime state is for %s, ahead of %s", day_key, day)
        return None
    return int(seconds // 60)
