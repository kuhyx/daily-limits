# Copyright (c) 2026 Krzysztof Rudnicki
"""Declaring a rest day the phone asked for, through screen-locker's own CLI.

A subprocess, never an import: screen-locker owns the rules (future days only,
two per ISO week, an NTP-confirmed clock) and this app must not re-implement or
bypass any of them. Its exit code is the answer; its output is the message.
"""

from __future__ import annotations

from datetime import date
import logging
import subprocess
from typing import Final

from daily_limits import _paths

_logger = logging.getLogger(__name__)

# The NTP check inside can stall; a tick runs every 60 s.
_TIMEOUT_SECONDS: Final = 45


def parse_day(raw: object) -> date | None:
    """``raw`` as a ``YYYY-MM-DD`` date, or ``None`` if it is anything else.

    Strict on purpose: the value ends up in another program's argv, so a
    ``"--list"`` or ``"tomorrow"`` from the phone must never get that far.
    """
    if not isinstance(raw, str):
        return None
    try:
        day = date.fromisoformat(raw)
    except ValueError as exc:
        _logger.warning("rejecting rest-day date %r: %s", raw, exc)
        return None
    return day if day.isoformat() == raw else None


def declare(day: date) -> tuple[bool, str]:
    """Run ``screen_locker.screen_lock --declare-rest-day <day>``.

    Returns:
        ``(ok, message)``: ``ok`` is exit status 0; ``message`` is its stdout,
        else its stderr, else a note of the exit status.
    """
    argv = [
        _paths.SCREEN_LOCKER_PYTHON,
        "-m",
        "screen_locker.screen_lock",
        "--declare-rest-day",
        day.isoformat(),
    ]
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _logger.warning("could not run screen-locker's rest-day CLI: %s", exc)
        return False, f"could not run screen-locker: {exc}"
    message = done.stdout.strip() or done.stderr.strip()
    return done.returncode == 0, message or f"screen-locker exited {done.returncode}"
