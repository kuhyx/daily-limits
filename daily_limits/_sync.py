# Copyright (c) 2026 Krzysztof Rudnicki
"""One ``--sync`` tick: answer the phone, then publish today's status.

Order: evaluate requests (a ``rest_day`` changes the limits), rebuild the
report if any asked for it, publish at most once, *then* write the results --
so a phone that sees its result already sees the new ``published_at`` too.

Firebase being unreachable, unconfigured or rejecting the login is one warning
and an early return. The cache was written before this runs, so the i3blocks
block never pays for the network.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING

from daily_limits import _publish, _requests, _sync_client

if TYPE_CHECKING:
    from collections.abc import Callable

    from daily_limits._report import Report

_logger = logging.getLogger(__name__)


def _now() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def _run(report: Report, rebuild: Callable[[], Report]) -> None:
    client = _sync_client.get_sync_client()
    now = _now()
    names, republish = _requests.collect(client, now=now)
    if republish:
        report = rebuild()
        now = _now()
    if republish or _publish.is_due(report, now=now):
        _publish.publish(client, report, now=now)
        _requests.sweep(client, now=now)
    _requests.finish(client, names)


def tick(report: Report, rebuild: Callable[[], Report]) -> None:
    """Run one sync tick; log a single warning instead of raising on failure.

    Args:
        report: The report just written to the cache.
        rebuild: Rebuilds the report and rewrites the cache; called when a
            request changed the limits or asked for a refresh.
    """
    try:
        _run(report, rebuild)
    except _sync_client.SyncUnavailableError as exc:
        _logger.warning("firebase sync skipped: %s", exc)
    except _sync_client.SYNC_ERRORS as exc:
        _logger.warning("firebase sync failed this tick: %s", exc)
