# Copyright (c) 2026 Krzysztof Rudnicki
"""Opening the desktop sick-day picker, ``sickdays gui``, from the popup.

A subprocess, never an import, for the same reason as ``_rest_day``: sickdays
owns its rules and its writes, and this app stays read-only. The child gets its
own session and no inherited stdio, so closing the popup does not take it down.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Final

_logger = logging.getLogger(__name__)

EXECUTABLE: Final = "sickdays"
NOT_INSTALLED: Final = "sickdays is not installed"


def launch() -> str | None:
    """Start ``sickdays gui`` detached.

    Returns:
        ``None`` once it is started, else a one-line message for the popup.
    """
    path = shutil.which(EXECUTABLE)
    if path is None:
        _logger.warning(
            "%s is not on PATH; cannot open the sick-day picker", EXECUTABLE
        )
        return NOT_INSTALLED
    try:
        # Not a `with`: leaving it would wait for the picker, which must
        # outlive the popup.
        subprocess.Popen(  # pylint: disable=consider-using-with
            [path, "gui"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        _logger.warning("could not start %s gui: %s", path, exc)
        return NOT_INSTALLED
    return None
