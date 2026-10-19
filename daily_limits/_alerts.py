# Copyright (c) 2026 Krzysztof Rudnicki
"""Shadow-week alerts, run by the ``--sync`` timer tick after the cache write.

* A critical notification (dunst, via ``notify-send``) when the would-be
  leisure left reaches 60, 30, 10 and 5 minutes; each once per gaming day.
  A jump past several thresholds says the tightest one, once.
* At would-be 0, the splash (``--shadow-splash``) in its own transient user
  unit (``systemd-run --user --collect``), so it outlives this oneshot. The
  fixed unit name means two can never run at once; it is re-shown every
  15 minutes while over.

Nothing here blocks anything: it is the shadow week. Bookkeeping lives in
``_paths.ALERT_STATE_FILE``, keyed by the gaming day.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Final

from daily_limits import _paths, _state

if TYPE_CHECKING:
    from daily_limits._leisure_now import Facts
    from daily_limits._shadow import LeisureShadow

_logger: Final = logging.getLogger(__name__)
THRESHOLDS: Final = (60, 30, 10, 5)
SPLASH_EVERY_S: Final = 15 * 60
SPLASH_UNIT: Final = "daily-limits-shadow-splash"
# What the splash needs from this process's environment: the display, and the
# overrides that point it at a fixture instead of the live files.
_FORWARDED: Final = (
    "DISPLAY",
    "XAUTHORITY",
    "PYTHONPATH",
    "DAILY_LIMITS_CACHE",
    "LEISURE_WATCH_NOW",
)
_TIMEOUT_S = 10.0


def counting_now(facts: Facts | None) -> str:
    """What leisure-watch says is counting right now, for a human."""
    if facts is None:
        return "unknown — leisure-watch is silent, so everything would count"
    if facts.state == "paused":
        return f"nothing (paused by {facts.paused_by})"
    return ", ".join(reason.label for reason in facts.reasons) or "nothing"


def _run(name: str, argv: list[str]) -> int | None:
    """Exit status of ``name argv...``; ``None`` (logged) when it cannot run."""
    path = shutil.which(name)
    if path is None:
        _logger.warning("%s is not on PATH", name)
        return None
    try:
        done = subprocess.run(
            [path, *argv], capture_output=True, timeout=_TIMEOUT_S, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.warning("%s did not finish: %s", name, exc)
        return None
    return done.returncode


def _notify(left: int, facts: Facts | None) -> bool:
    title = f"🛋 SHADOW: {left} min of leisure left"
    body = (
        "Shadow week: nothing is blocked yet; at 0 this would block.\n"
        f"Counting now: {counting_now(facts)}"
    )
    argv = ["-u", "critical", "-a", "daily-limits", title, body]
    if _run(_paths.NOTIFY_SEND, argv) == 0:
        return True
    _logger.warning("notify-send failed for the %d min shadow alert", left)
    return False


def _launch_splash() -> bool:
    """Start the splash unless one is already up; ``True`` once it shows."""
    unit = f"{SPLASH_UNIT}.service"
    if _run(_paths.SYSTEMCTL, ["--user", "--quiet", "is-active", unit]) == 0:
        return True
    setenv = [
        f"--setenv={name}={os.environ[name]}"
        for name in _FORWARDED
        if os.environ.get(name)
    ]
    argv = ["--user", "--collect", "--quiet", f"--unit={SPLASH_UNIT}", *setenv]
    argv += [sys.executable, "-m", "daily_limits", "--shadow-splash"]
    if _run(_paths.SYSTEMD_RUN, argv) == 0:
        return True
    _logger.warning("could not launch the shadow splash (%s)", SPLASH_UNIT)
    return False


def _countdown(left: int, notified: set[int], facts: Facts | None) -> bool:
    """Notify the tightest newly crossed threshold; ``True`` if state changed."""
    due = {limit for limit in THRESHOLDS if left <= limit} - notified
    if not due or not _notify(min(due), facts):
        return False
    notified |= due
    return True


def tick(shadow: LeisureShadow, facts: Facts | None, now: float | None = None) -> None:
    """Fire whatever is due for ``shadow`` (the C5 block) at ``now``."""
    left = shadow["left_minutes"]
    if left is None:
        return
    moment = time.time() if now is None else now
    saved = _state.load(_paths.ALERT_STATE_FILE)
    fresh = saved.get("day") != shadow["day"]
    state: dict[str, object] = (
        {"day": shadow["day"], "notified": []} if fresh else saved
    )
    raw = state.get("notified")
    notified = (
        {n for n in raw if isinstance(n, int)} if isinstance(raw, list) else set()
    )
    changed = fresh
    if shadow["would_block"]:
        # Over: the splash says it; every countdown step is behind us.
        changed = changed or not notified.issuperset(THRESHOLDS)
        notified.update(THRESHOLDS)
        last = state.get("splash_at")
        due = not isinstance(last, int | float) or moment - last >= SPLASH_EVERY_S
        if due and _launch_splash():
            state["splash_at"] = moment
            changed = True
    else:
        changed = _countdown(left, notified, facts) or changed
    if changed:
        state["notified"] = sorted(notified)
        _state.save(_paths.ALERT_STATE_FILE, state)
