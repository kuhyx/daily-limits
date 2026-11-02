# Copyright (c) 2026 Krzysztof Rudnicki
"""Opening the focus work (``python3 -m focus_project.open``) from the popup.

A subprocess, never an import, as for ``_sick_picker``: ``focus_project`` owns
what is active and where the work is (the tutor focus screen and the work
URL), and this app stays read-only. The system python is used because that is
where ``focus_project`` is installed (its ``install.sh``); the child gets its
own session, so closing the popup does not take the opened windows down.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Final

_logger = logging.getLogger(__name__)

SYSTEM_PYTHON: Final = "/usr/bin/python3"
FAILED: Final = "could not open the focus work"


def launch() -> str | None:
    """Start ``python3 -m focus_project.open`` detached.

    Returns:
        ``None`` once it is started, else a one-line message for the popup.
    """
    try:
        # Not a `with`: leaving it would wait for the tutor server to come up.
        subprocess.Popen(  # pylint: disable=consider-using-with
            [SYSTEM_PYTHON, "-m", "focus_project.open"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        _logger.warning("could not start focus_project.open: %s", exc)
        return FAILED
    return None
