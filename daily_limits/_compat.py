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
