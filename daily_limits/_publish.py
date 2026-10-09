# Copyright (c) 2026 Krzysztof Rudnicki
"""Publishing today's report to ``daily_limits/status.json`` for the phone.

The payload is the frozen JSON contract plus ``published_at`` (unix seconds)
and ``device_id`` (this install's persisted uuid). It is written when its
content changed -- ignoring ``generated_at``, which changes every tick -- and
at least every :data:`HEARTBEAT_SECONDS` regardless, because the phone reads a
``published_at`` older than 15 min as "PC offline".
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Final

from crdt_sync import load_device_identity

from daily_limits import _paths, _state, _sync_client

if TYPE_CHECKING:
    from crdt_sync import FirebaseSyncClient

    from daily_limits._report import Report

HEARTBEAT_SECONDS: Final = 10 * 60

# Keys that change on every build without the limits changing.
_VOLATILE: Final = frozenset({"generated_at", "published_at"})


def device_id() -> str:
    """This install's persisted uuid (minted on first call)."""
    return str(load_device_identity(_paths.DEVICE_ID_FILE).device_id)


def digest(report: Report) -> str:
    """Hash of the report's content, ignoring the per-build timestamps."""
    stable = {key: value for key, value in report.items() if key not in _VOLATILE}
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def is_due(report: Report, *, now: int) -> bool:
    """Whether the content changed or the heartbeat interval has passed."""
    last = _state.load(_paths.PUBLISH_STATE_FILE)
    published_at = last.get("published_at")
    if not isinstance(published_at, int) or now - published_at >= HEARTBEAT_SECONDS:
        return True
    return last.get("digest") != digest(report)


def publish(client: FirebaseSyncClient, report: Report, *, now: int) -> None:
    """Write ``report`` to the status path, then record what was published.

    The local record is written only after the PUT succeeded, so a failed
    publish is retried on the next tick rather than mistaken for a sent one.
    """
    payload = {**report, "published_at": now, "device_id": device_id()}
    client.put_file_text(
        _sync_client.STATUS_PATH,
        json.dumps(payload),
        message="daily-limits: publish status",
    )
    _state.save(
        _paths.PUBLISH_STATE_FILE,
        {"digest": digest(report), "published_at": now},
    )
