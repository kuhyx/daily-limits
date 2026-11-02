# Copyright (c) 2026 Krzysztof Rudnicki
"""Starting a program that must outlive the popup that launched it."""

from __future__ import annotations

import subprocess


def start(argv: list[str]) -> None:
    """Start ``argv`` in its own session with no inherited stdio.

    Raises:
        OSError: the program could not be started.
    """
    # Not a `with`: leaving it would wait for the child, which must outlive
    # the popup.
    subprocess.Popen(  # pylint: disable=consider-using-with
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
