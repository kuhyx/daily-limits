# Copyright (c) 2026 Krzysztof Rudnicki
"""Opening a LeetCode problem (``python3 -m leetcode_guard.open_cli``) from the popup.

A subprocess, never an import, as for ``_focus_open``: leetcode-guard owns the
suggestion list and the browser launch (its lock's ``Open`` button, without a
lock), and this app stays read-only. The system python is used because that is
where ``leetcode_guard`` is installed (its ``install.sh``).

Unlike the focus opener this one waits for the child. The guard's CLI starts
the browser in its own session and exits in well under a second, and with no
stdio its exit status is the only way to tell "opened" from "nothing to open":
a click that silently does nothing is the fault this row was added to fix.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Final

_logger = logging.getLogger(__name__)

SYSTEM_PYTHON: Final = "/usr/bin/python3"
FAILED: Final = "could not open a LeetCode problem"
# The click blocks the popup for this long at worst (a hung interpreter).
TIMEOUT_SECONDS: Final = 5


def launch() -> str | None:
    """Run ``python3 -m leetcode_guard.open_cli`` and read its exit status.

    Returns:
        ``None`` once a browser was started, else a one-line message for the
        popup.
    """
    try:
        done = subprocess.run(
            [SYSTEM_PYTHON, "-m", "leetcode_guard.open_cli"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _logger.warning("could not run leetcode_guard.open_cli: %s", exc)
        return FAILED
    if done.returncode != 0:
        _logger.warning("leetcode_guard.open_cli exited %d", done.returncode)
        return FAILED
    return None
