# Copyright (c) 2026 Krzysztof Rudnicki
"""``daily-limits``: today's shutdown time and gaming limit, and how to extend them.

Modes: a human summary (default), ``--json`` (the contract), ``--write-cache``
(the contract, atomically, to ``$XDG_RUNTIME_DIR/daily-limits.json`` for the
i3blocks block), ``--sync`` (``--write-cache``, then the Firebase tick the
systemd timer runs: publish the status, answer the phone) and ``--gui`` (a
small Tk popup). ``--sync`` also fires the shadow week's alerts
(``_alerts``), whose would-be-0 splash is ``--shadow-splash``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from daily_limits import (
    _alerts,
    _gui,
    _leisure_now,
    _paths,
    _render,
    _report,
    _splash,
    _sync,
)
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
    mode.add_argument(
        "--shadow-splash",
        action="store_true",
        help="the shadow week's would-be-0 splash (launched by --sync)",
    )
    return parser


def cache_path() -> Path | None:
    """``$DAILY_LIMITS_CACHE``, else ``$XDG_RUNTIME_DIR/daily-limits.json``.

    ``None`` when neither is set. There is no safe default: a guessed
    directory could be another user's. The override is the one the i3blocks
    block honours too.
    """
    override = os.environ.get("DAILY_LIMITS_CACHE")
    if override:
        return Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    return Path(runtime) / _paths.CACHE_NAME if runtime else None


def _refresh_cache(target: Path) -> _report.Report:
    """Build today's report and write it to the cache; return the report."""
    report = _report.build()
    write_atomic(target, json.dumps(report) + "\n")
    return report


def _shadow_alerts(report: _report.Report) -> None:
    """The shadow week's alerts; a failure there never costs the Firebase tick.

    None once the leisure budget is live: the enforcer warns for real then.
    """
    if report["leisure_active"]:
        return
    try:
        _alerts.tick(report["leisure_shadow"], _leisure_now.read())
    except OSError as exc:
        logging.getLogger(__name__).warning("shadow alerts failed: %s", exc)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns the process exit status."""
    logging.basicConfig(level=logging.WARNING, format="daily-limits: %(message)s")
    args = _parser().parse_args(argv)
    if args.gui:
        return _gui.run()
    if args.shadow_splash:
        return _splash.run(cache_path())
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
            _shadow_alerts(report)
            _sync.tick(report, lambda: _refresh_cache(target))
        return 0
    report = _report.build()
    if args.json:
        sys.stdout.write(json.dumps(report) + "\n")
    else:
        sys.stdout.write(_render.summary(report) + "\n")
    return 0
