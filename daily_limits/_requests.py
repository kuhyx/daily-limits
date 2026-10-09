# Copyright (c) 2026 Krzysztof Rudnicki
"""Answering the phone's requests under ``daily_limits/requests/``.

The phone writes ``requests/<id>.json``; the PC answers in
``results/<id>.json`` and deletes the request. The id is the *filename* stem,
never the body's ``id``: a malformed body has none, and the phone looks for
its answer by the name it wrote.

Exactly once: an outcome is recorded locally (``_paths.HANDLED_FILE``) the
moment the request is evaluated, before any network write. A tick that dies
after declaring a rest day but before writing the result re-sends the stored
result next tick; it never runs the declaration again.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Final

from daily_limits import _paths, _rest_day, _state, _sync_client

if TYPE_CHECKING:
    from crdt_sync import FirebaseSyncClient

_logger = logging.getLogger(__name__)

REQUEST_TTL_SECONDS: Final = 10 * 60
RESULT_TTL_SECONDS: Final = 7 * 24 * 60 * 60
_SUFFIX: Final = ".json"


def _result(request_id: str, *, ok: bool, message: str, now: int) -> dict[str, object]:
    return {"id": request_id, "ok": ok, "message": message, "handled_at": now}


def _created_at(body: dict[str, object]) -> int | None:
    value = body.get("created_at")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _act(body: dict[str, object]) -> tuple[bool, str, bool]:
    """Carry out one well-formed, unexpired request: ``(ok, message, republish)``."""
    kind = body.get("kind")
    if kind == "refresh":
        return True, "status recomputed and republished", True
    if kind == "rest_day":
        day = _rest_day.parse_day(body.get("date"))
        if day is None:
            return (
                False,
                f"rest_day needs date YYYY-MM-DD, got {body.get('date')!r}",
                False,
            )
        ok, message = _rest_day.declare(day)
        return ok, message, True
    return False, f"unknown kind {kind!r} (expected 'refresh' or 'rest_day')", False


def evaluate(
    request_id: str, text: str | None, *, now: int
) -> tuple[dict[str, object], bool]:
    """Return ``(result, republish)`` for one request; never raises on bad input."""
    if text is None:
        reason = (
            "malformed: the value is not a JSON string (write serialized JSON text)"
        )
        return _result(request_id, ok=False, message=reason, now=now), False
    try:
        body = json.loads(text)
    except ValueError as exc:
        _logger.warning("request %s is not JSON: %s", request_id, exc)
        return _result(
            request_id, ok=False, message=f"malformed JSON: {exc}", now=now
        ), False
    if not isinstance(body, dict):
        return _result(
            request_id, ok=False, message="malformed: not a JSON object", now=now
        ), False
    created_at = _created_at(body)
    if created_at is None:
        reason = "malformed: created_at must be a unix int"
        return _result(request_id, ok=False, message=reason, now=now), False
    if now - created_at > REQUEST_TTL_SECONDS:
        return _result(request_id, ok=False, message="expired", now=now), False
    ok, message, republish = _act(body)
    return _result(request_id, ok=ok, message=message, now=now), republish


def collect(client: FirebaseSyncClient, *, now: int) -> tuple[list[str], bool]:
    """Evaluate every unhandled request; return ``(request names, republish)``.

    Each new outcome is saved to the handled file straight away, unwritten.
    An outcome still unwritten from a failed tick asks for its republish
    again, so a refresh whose publish failed is not answered without one.
    """
    names = client.list_directory(_sync_client.REQUESTS_DIR)
    if not names:
        return [], False
    texts = client.get_string_map(_sync_client.REQUESTS_DIR)
    handled = _state.load(_paths.HANDLED_FILE)
    republish = False
    for name in names:
        request_id = name.removesuffix(_SUFFIX)
        entry = handled.get(request_id)
        if isinstance(entry, dict):
            republish = republish or (
                not entry.get("written") and bool(entry.get("republish"))
            )
            continue
        result, wants = evaluate(request_id, texts.get(name), now=now)
        republish = republish or wants
        handled[request_id] = {"result": result, "written": False, "republish": wants}
        _state.save(_paths.HANDLED_FILE, handled)
    return names, republish


def finish(client: FirebaseSyncClient, names: list[str]) -> None:
    """Write each pending result, mark it written, then delete its request."""
    handled = _state.load(_paths.HANDLED_FILE)
    for name in names:
        request_id = name.removesuffix(_SUFFIX)
        entry = handled.get(request_id)
        if not isinstance(entry, dict) or not isinstance(entry.get("result"), dict):
            _logger.warning("no stored result for request %s; leaving it", name)
            continue
        if not entry.get("written"):
            client.put_file_text(
                f"{_sync_client.RESULTS_DIR}/{request_id}{_SUFFIX}",
                json.dumps(entry["result"]),
                message="daily-limits: answer request",
            )
            entry["written"] = True
            _state.save(_paths.HANDLED_FILE, handled)
        client.delete_file(
            f"{_sync_client.REQUESTS_DIR}/{name}", message="daily-limits: handled"
        )


def _handled_at(name: str, text: str) -> int | None:
    """``handled_at`` of one result; ``None`` (with a warning) if unreadable."""
    try:
        value = json.loads(text).get("handled_at")
    except (ValueError, AttributeError) as exc:
        _logger.warning("leaving result %s: unreadable: %s", name, exc)
        return None
    if not isinstance(value, int):
        _logger.warning("leaving result %s: no readable handled_at", name)
        return None
    return value


def _entry_time(entry: object) -> int | None:
    """``handled_at`` of a handled-file entry; ``None`` for a corrupt one."""
    if not isinstance(entry, dict):
        return None
    result = entry.get("result")
    value = result.get("handled_at") if isinstance(result, dict) else None
    return value if isinstance(value, int) else None


def sweep(client: FirebaseSyncClient, *, now: int) -> None:
    """Delete results older than 7 days, and forget handled ids just as old."""
    cutoff = now - RESULT_TTL_SECONDS
    for name, text in client.get_string_map(_sync_client.RESULTS_DIR).items():
        handled_at = _handled_at(name, text)
        if handled_at is not None and handled_at < cutoff:
            client.delete_file(
                f"{_sync_client.RESULTS_DIR}/{name}", message="daily-limits: expire"
            )
    handled = _state.load(_paths.HANDLED_FILE)
    kept = {
        request_id: entry
        for request_id, entry in handled.items()
        if (_entry_time(entry) or 0) >= cutoff
    }
    if len(kept) != len(handled):
        _state.save(_paths.HANDLED_FILE, kept)
