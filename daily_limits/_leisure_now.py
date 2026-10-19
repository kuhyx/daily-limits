# Copyright (c) 2026 Krzysztof Rudnicki
"""leisure-watch's signed ``now.json`` (contract C3): what counts right now.

Stdlib only (leisure_watch is not imported; this package stays stdlib +
earned_time + sickdays + crdt_sync). :func:`read` returns ``None`` for "do not
trust this" -- missing, older than 15 s, from the future, malformed or badly
signed -- and the callers say so instead of guessing "nothing counts".
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import time
from typing import Final

from daily_limits import _paths

_logger: Final = logging.getLogger(__name__)
_STATES: Final = frozenset({"leisure", "free", "paused"})
MAX_AGE_S: Final = 15.0
# A writer clock a little ahead of ours is tolerated (leisure-watch's own skew).
_FUTURE_SKEW_S: Final = 2.0


@dataclass(frozen=True)
class Reason:
    """One thing that makes this moment leisure (``key`` as in C4 sources)."""

    source: str
    key: str
    pid: int | None
    label: str


@dataclass(frozen=True)
class Facts:
    """The trusted part of one ``now.json``."""

    state: str
    paused_by: str | None
    reasons: tuple[Reason, ...]


def now_path() -> Path | None:
    """``$LEISURE_WATCH_NOW``, else ``$XDG_RUNTIME_DIR/leisure-watch/now.json``."""
    override = os.environ.get("LEISURE_WATCH_NOW")
    if override:
        return Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    return Path(runtime) / _paths.LEISURE_NOW_NAME if runtime else None


def _signed(doc: dict[str, object]) -> bool:
    try:
        key = _paths.KEY_FILE.read_bytes().strip()
    except OSError as exc:
        _logger.warning("Cannot read the HMAC key %s (%s)", _paths.KEY_FILE, exc)
        return False
    body = {k: v for k, v in doc.items() if k != "sig"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    want = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, str(doc.get("sig", "")))


def _reason(raw: object) -> Reason | None:
    if not isinstance(raw, dict):
        return None
    key, label = raw.get("key"), raw.get("label")
    if not isinstance(key, str) or not isinstance(label, str):
        return None
    pid, source = raw.get("pid"), raw.get("source")
    return Reason(
        source=source if isinstance(source, str) else "",
        key=key,
        pid=pid if isinstance(pid, int) else None,
        label=label,
    )


def _facts(doc: dict[str, object], now: float) -> Facts | None:
    ts, state, paused_by = doc.get("ts"), doc.get("state"), doc.get("paused_by")
    raw_reasons = doc.get("reasons")
    if not isinstance(ts, int | float) or not -_FUTURE_SKEW_S <= now - ts <= MAX_AGE_S:
        return None
    if state not in _STATES or not isinstance(raw_reasons, list):
        return None
    if paused_by is not None and not isinstance(paused_by, str):
        return None
    reasons = [_reason(raw) for raw in raw_reasons]
    if any(reason is None for reason in reasons):
        return None
    return Facts(
        state=str(state),
        paused_by=paused_by,
        reasons=tuple(reason for reason in reasons if reason is not None),
    )


def read(now: float | None = None) -> Facts | None:
    """The fresh, correctly signed facts, or ``None`` (logged) when untrusted."""
    path = now_path()
    if path is None:
        _logger.warning("XDG_RUNTIME_DIR is not set; cannot find leisure-watch")
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _logger.warning("Cannot read leisure-watch's %s (%s)", path, exc)
        return None
    if not isinstance(doc, dict) or not _signed(doc):
        _logger.warning("leisure-watch's %s is not correctly signed", path)
        return None
    facts = _facts(doc, time.time() if now is None else now)
    if facts is None:
        _logger.warning("leisure-watch's %s is stale or malformed", path)
    return facts
