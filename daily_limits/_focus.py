# Copyright (c) 2026 Krzysztof Rudnicki
"""The active focus project, for the i3blocks focus block.

``focus_project`` (~/src/utils) decides what is active and how many minutes
are done; this module only asks it, softly: a missing package or a failing
``status()`` costs the report its ``focus`` field (logged), never the limits
themselves. Whenever the field changes, i3blocks is poked so the bar is not
a minute late.
"""

from __future__ import annotations

import importlib
import logging
import subprocess
from typing import TYPE_CHECKING, Any

from daily_limits import _paths

if TYPE_CHECKING:
    from datetime import date

_logger = logging.getLogger(__name__)


def fetch(day: date) -> dict[str, Any] | None:
    """``focus_project.status(day)``, or ``None`` when it cannot be had."""
    try:
        module = importlib.import_module("focus_project")
        status = module.status(day)
    except ImportError, OSError, ValueError, LookupError, TypeError, AttributeError:
        # Soft by contract: a failure drops the field; the traceback says why.
        _logger.exception("focus_project unavailable, no focus field")
        return None
    if not isinstance(status, dict):
        _logger.warning(
            "focus_project.status returned %s, no focus field", type(status)
        )
        return None
    return status


def notify() -> None:
    """Poke i3blocks (``signal=`` of the focus block); never raises."""
    cmd = [_paths.PKILL, f"-RTMIN+{_paths.FOCUS_SIGNAL}", "-x", "i3blocks"]
    try:
        # pkill exits 1 when no i3blocks runs (headless): not an error here.
        subprocess.run(cmd, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.warning("could not run pkill to refresh i3blocks: %s", exc)
