# Copyright (c) 2026 Krzysztof Rudnicki
"""``daily-limits``: today's shutdown time and gaming limit, and how to extend them.

Modes: a human summary (default), ``--json`` (the contract), ``--write-cache``
(the contract, atomically, to ``$XDG_RUNTIME_DIR/daily-limits.json`` for the
i3blocks block), ``--sync`` (``--write-cache``, then the Firebase tick the
systemd timer runs: publish the status, answer the phone) and ``--gui`` (a
small Tk popup).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from daily_limits import _gui, _paths, _render, _report, _sync
from daily_limits._atomic import write_atomic

if TYPE_CHECKING:
    from collections.abc import Sequence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-limits", description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true", help="print the JSON contract")
    mode.add_argument(
        "--write-cache",
        action="store_true",
        help=f"write the JSON atomically to $XDG_RUNTIME_DIR/{_paths.CACHE_NAME}",
    )
    mode.add_argument(
        "--sync",
        action="store_true",
        help="--write-cache, then publish to Firebase and answer the phone's requests",
    )
    mode.add_argument("--gui", action="store_true", help="open a small Tk popup")
    return parser


def cache_path() -> Path | None:
    """``$XDG_RUNTIME_DIR/daily-limits.json``, or ``None`` when it is unset.

    There is no safe default: a guessed directory could be another user's.
    """
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    return Path(runtime) / _paths.CACHE_NAME if runtime else None


def _refresh_cache(target: Path) -> _report.Report:
    """Build today's report and write it to the cache; return the report."""
    report = _report.build()
    write_atomic(target, json.dumps(report) + "\n")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns the process exit status."""
    logging.basicConfig(level=logging.WARNING, format="daily-limits: %(message)s")
    args = _parser().parse_args(argv)
    if args.gui:
        return _gui.run()
    if args.write_cache or args.sync:
        target = cache_path()
        if target is None:
            sys.stderr.write(
                "daily-limits: XDG_RUNTIME_DIR is not set; cannot place the cache\n"
            )
            return 1
        # The cache is written before any network call, so an unreachable
        # Firebase can never cost the i3blocks block its numbers.
        report = _refresh_cache(target)
        if args.sync:
            _sync.tick(report, lambda: _refresh_cache(target))
        return 0
    report = _report.build()
    if args.json:
        sys.stdout.write(json.dumps(report) + "\n")
    else:
        sys.stdout.write(_render.summary(report) + "\n")
    return 0
