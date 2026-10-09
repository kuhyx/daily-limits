# Copyright (c) 2026 Krzysztof Rudnicki
"""Newer earned_time helpers, used when installed, with the 0.3.0 fallback.

From 2026-10-10 the shutdown ladder makes an earner's shutdown minutes and the
ceiling depend on the day (``shutdown_minutes_for`` / ``shutdown_ceiling_for``),
and the counted workout gets a ledger read by ``credit_units``. None of those
exist in 0.3.0; there the raw ``Earner`` fields and constants are the whole
answer. Either way no minute is hard-coded here.
"""

from __future__ import annotations

from importlib import metadata
from typing import TYPE_CHECKING

import earned_time

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date, datetime
    from pathlib import Path

    from earned_time import Earner


def version() -> str:
    """The installed earned-time version, for log lines."""
    dist = next(iter(metadata.distributions(name="earned-time")), None)
    return "(source tree)" if dist is None else dist.version


def shutdown_minutes(item: Earner, day: date) -> int:
    """What ``item``'s first unit pushes shutdown later by on ``day``."""
    helper: Callable[[Earner, date], int] | None = getattr(
        earned_time, "shutdown_minutes_for", None
    )
    return item.shutdown_minutes if helper is None else helper(item, day)


def shutdown_ceiling(day: date) -> int:
    """The latest shutdown ``day`` can earn, minutes after midnight."""
    helper: Callable[[date], int] | None = getattr(
        earned_time, "shutdown_ceiling_for", None
    )
    return earned_time.SHUTDOWN_CEILING_MINUTES if helper is None else helper(day)


def credit_units(
    item: Earner, ledger: Path, key_file: Path, day: date, cutoff: datetime
) -> int | bool | None:
    """Units a counted earner's ledger credits on ``day``; ``None`` = unknown.

    Without ``credit_units`` the ledger still answers yes/no for the first
    unit through ``done_today`` -- an undercount of extras, never a guess.
    """
    helper: Callable[[Earner, Path, Path, date], int | None] | None = getattr(
        earned_time, "credit_units", None
    )
    if helper is not None:
        return helper(item, ledger, key_file, day)
    done: bool | None = earned_time.done_today(item, ledger, key_file, now=cutoff)
    return done


def earners(day: date) -> tuple[Earner, ...]:
    """The registry in force on ``day`` (``earners_for``, earned_time >= 0.5)."""
    helper: Callable[[date], tuple[Earner, ...]] | None = getattr(
        earned_time, "earners_for", None
    )
    return tuple(earned_time.EARNERS if helper is None else helper(day))


def units_left(item: Earner, answer: int | None) -> int:
    """Units ``item`` can still pay: 1 until done, a capped gate's remainder.

    A capped counted gate is the tutor (4 blocks a day).
    """
    done = answer or 0
    most: int | None = getattr(item, "max_units", None)
    if most is None:
        return 0 if done > 0 else 1
    return max(0, most - done)


def shutdown_left(item: Earner, answer: int | None, day: date) -> int:
    """Shutdown minutes ``item``'s remaining units would still add on ``day``."""
    most: int | None = getattr(item, "max_units", None)
    if most is None:
        return shutdown_minutes(item, day)
    return int(item.shutdown_for(most, day) - item.shutdown_for(answer or 0, day))


def gaming_most(item: Earner) -> int:
    """Gaming minutes a fully done day pays (the tutor's 4 blocks, not one)."""
    return int(getattr(item, "max_gaming_minutes", item.gaming_minutes))
