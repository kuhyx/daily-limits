# Copyright (c) 2026 Krzysztof Rudnicki
"""Every earner's answer for one day, read generically from its signed ledger.

No earner is special-cased: a ledger-backed flat earner goes through
``earned_time.done_today``, a counted one (the workout) through
``credit_units``. An earner the installed earned_time gives no ledger (the
workout on 0.3.0) is ``None`` -- "could not check" -- never a guess.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging
from typing import TYPE_CHECKING, Final

import earned_time

from daily_limits import _compat, _paths

if TYPE_CHECKING:
    from earned_time import Earner

Answer = int | bool | None
_logger: Final = logging.getLogger(__name__)

# steam-backlog-enforcer's gaming day starts at 06:00 (its _gaming_days.py).
_GAMING_DAY_SHIFT: Final = timedelta(hours=6)


def gaming_day(moment: datetime) -> date:
    """The enforcer's gaming day at ``moment``: the calendar day before 06:00."""
    return (moment - _GAMING_DAY_SHIFT).date()


def _cutoff(day: date, moment: datetime) -> datetime:
    """Where ``day``'s credit window ends: now, or that day's last second."""
    end = datetime.combine(day, time.max).astimezone(moment.tzinfo)
    return min(moment, end)


def answer(item: Earner, day: date, moment: datetime) -> Answer:
    """``item``'s answer for ``day`` as seen at ``moment``."""
    if item.ledger is None or item.match is None:
        _logger.warning(
            "%s has no ledger in earned_time %s; could not check",
            item.label,
            _compat.version(),
        )
        return None
    ledger = _paths.HOME / item.ledger
    cutoff = _cutoff(day, moment)
    if item.kind == "counted":
        return _compat.credit_units(item, ledger, _paths.KEY_FILE, day, cutoff)
    done: bool | None = earned_time.done_today(
        item, ledger, _paths.KEY_FILE, now=cutoff
    )
    return done


def answers_for(day: date, moment: datetime) -> dict[str, Answer]:
    """Every registered earner's answer for ``day``; ``None`` means unknown."""
    return {item.name: answer(item, day, moment) for item in earned_time.EARNERS}
