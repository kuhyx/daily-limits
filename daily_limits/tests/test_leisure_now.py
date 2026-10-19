# Copyright (c) 2026 Krzysztof Rudnicki
"""leisure-watch's signed ``now.json`` (contract C3), read and verified."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

import pytest

from daily_limits import _leisure_now, _paths
from daily_limits.tests.conftest import TEST_KEY

NOW = 1_792_000_000.0


def sign(doc: dict[str, object], key: bytes = TEST_KEY) -> dict[str, object]:
    """``doc`` with the watcher's HMAC-SHA256 ``sig`` over its canonical JSON."""
    body = {k: v for k, v in doc.items() if k != "sig"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {**body, "sig": sig}


def now_doc(
    *,
    ts: float = NOW,
    state: str = "leisure",
    paused_by: str | None = None,
    reasons: list[object] | None = None,
) -> dict[str, object]:
    """An unsigned C3 document."""
    return {
        "v": 1,
        "ts": ts,
        "seq": 3,
        "state": state,
        "paused_by": paused_by,
        "reasons": [
            {"source": "media", "key": "app:mpv", "pid": 42, "label": "Film — mpv"}
        ]
        if reasons is None
        else reasons,
        "focus": {"app": "mpv", "title": "Film", "domain": None, "idle": False},
        "extensions": {"helium": None, "librewolf": None},
    }


def write_now(doc: dict[str, object]) -> Path:
    """Write ``doc`` where the reader looks for it (the temp runtime dir)."""
    target = Path(os.environ["XDG_RUNTIME_DIR"]) / _paths.LEISURE_NOW_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(doc), encoding="utf-8")
    return target


def test_a_fresh_signed_file_is_read() -> None:
    write_now(sign(now_doc()))
    facts = _leisure_now.read(now=NOW + 5)
    assert facts == _leisure_now.Facts(
        state="leisure",
        paused_by=None,
        reasons=(
            _leisure_now.Reason(
                source="media", key="app:mpv", pid=42, label="Film — mpv"
            ),
        ),
    )


def test_paused_keeps_who_paused_it() -> None:
    write_now(sign(now_doc(state="paused", paused_by="i3lock", reasons=[])))
    facts = _leisure_now.read(now=NOW)
    assert facts is not None
    assert (facts.state, facts.paused_by, facts.reasons) == ("paused", "i3lock", ())


def test_env_override_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = tmp_path / "elsewhere.json"
    other.write_text(json.dumps(sign(now_doc())), encoding="utf-8")
    monkeypatch.setenv("LEISURE_WATCH_NOW", str(other))
    assert _leisure_now.now_path() == other
    assert _leisure_now.read(now=NOW) is not None


def test_no_runtime_dir_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR")
    assert _leisure_now.now_path() is None
    assert _leisure_now.read(now=NOW) is None


@pytest.mark.parametrize("age", [15.1, -2.1])
def test_stale_or_future_is_none(age: float) -> None:
    write_now(sign(now_doc()))
    assert _leisure_now.read(now=NOW + age) is None


def test_fifteen_seconds_old_is_still_fresh() -> None:
    write_now(sign(now_doc()))
    assert _leisure_now.read(now=NOW + 15) is not None


def test_bad_signature_is_none() -> None:
    write_now(sign(now_doc(), key=b"another-key"))
    assert _leisure_now.read(now=NOW) is None


def test_unreadable_key_is_none() -> None:
    write_now(sign(now_doc()))
    _paths.KEY_FILE.unlink()
    assert _leisure_now.read(now=NOW) is None


def test_missing_file_is_none() -> None:
    assert _leisure_now.read(now=NOW) is None


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        "[1, 2]",
        json.dumps({"ts": NOW, "state": "leisure", "reasons": []}),
    ],
)
def test_garbage_is_none(body: str) -> None:
    target = write_now({})
    target.write_text(body, encoding="utf-8")
    assert _leisure_now.read(now=NOW) is None


@pytest.mark.parametrize(
    "doc",
    [
        now_doc(state="bored"),
        now_doc(reasons=[{"key": 3, "label": "x"}]),
        now_doc(reasons=["app:mpv"]),
        {**now_doc(), "reasons": "nope"},
        {**now_doc(), "ts": "soon"},
        {**now_doc(), "paused_by": 7},
    ],
)
def test_malformed_signed_documents_are_none(doc: dict[str, object]) -> None:
    write_now(sign(doc))
    assert _leisure_now.read(now=NOW) is None


def test_reason_without_pid_or_source() -> None:
    write_now(sign(now_doc(reasons=[{"key": "domain:x.com", "label": "x.com"}])))
    facts = _leisure_now.read(now=NOW)
    assert facts is not None
    assert facts.reasons == (
        _leisure_now.Reason(source="", key="domain:x.com", pid=None, label="x.com"),
    )


def test_read_defaults_to_the_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    write_now(sign(now_doc()))
    monkeypatch.setattr("daily_limits._leisure_now.time.time", lambda: NOW + 1)
    assert _leisure_now.read() is not None
