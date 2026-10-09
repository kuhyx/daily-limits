# Copyright (c) 2026 Krzysztof Rudnicki
"""Answering the phone's requests: exactly once, never raising on bad input."""

from __future__ import annotations

from datetime import date
import json
import logging

import pytest

from daily_limits import _paths, _requests, _rest_day, _state
from daily_limits.tests._fake_store import FakeStore

NOW = 1_791_540_000
REQ = "daily_limits/requests"
RES = "daily_limits/results"


def _body(**fields: object) -> str:
    return json.dumps({"created_at": NOW, **fields})


def _message(text: str | None) -> tuple[bool, str, bool]:
    result, republish = _requests.evaluate("r1", text, now=NOW)
    assert result["id"] == "r1"
    assert result["handled_at"] == NOW
    return bool(result["ok"]), str(result["message"]), republish


@pytest.mark.parametrize(
    ("text", "says"),
    [
        (None, "not a JSON string"),
        ("{oops", "malformed JSON"),
        ("[1]", "not a JSON object"),
        (json.dumps({"kind": "refresh"}), "created_at must be a unix int"),
        (json.dumps({"kind": "refresh", "created_at": True}), "created_at"),
        (json.dumps({"kind": "refresh", "created_at": "1"}), "created_at"),
        (_body(kind="nap"), "unknown kind 'nap'"),
        (_body(kind="rest_day", date="tomorrow"), "rest_day needs date"),
        (_body(kind="rest_day"), "rest_day needs date"),
    ],
)
def test_bad_requests_are_refused_without_republish(
    text: str | None, says: str
) -> None:
    ok, message, republish = _message(text)
    assert not ok
    assert says in message
    assert not republish


def test_an_old_request_expires() -> None:
    old = json.dumps({"kind": "refresh", "created_at": NOW - 601})
    assert _message(old) == (False, "expired", False)


def test_a_request_at_the_ttl_is_still_served() -> None:
    edge = json.dumps({"kind": "refresh", "created_at": NOW - 600})
    assert _message(edge)[0]


def test_refresh_asks_for_a_republish() -> None:
    assert _message(_body(kind="refresh")) == (
        True,
        "status recomputed and republished",
        True,
    )


def test_rest_day_goes_through_screen_locker(monkeypatch: pytest.MonkeyPatch) -> None:
    days: list[date] = []

    def declare(day: date) -> tuple[bool, str]:
        days.append(day)
        return False, "refused: in the past"

    monkeypatch.setattr(_rest_day, "declare", declare)
    ok, message, republish = _message(_body(kind="rest_day", date="2026-10-08"))
    assert (ok, message, republish) == (False, "refused: in the past", True)
    assert days == [date(2026, 10, 8)]


def test_collect_with_no_requests() -> None:
    assert _requests.collect(FakeStore().client(), now=NOW) == ([], False)
    assert not _paths.HANDLED_FILE.exists()


def test_collect_records_each_outcome_before_any_write() -> None:
    store = FakeStore(
        {
            f"{REQ}/a.json": _body(kind="refresh"),
            f"{REQ}/b.json": {"kind": "refresh"},
        }
    )
    names, republish = _requests.collect(store.client(), now=NOW)
    assert (names, republish) == (["a.json", "b.json"], True)
    assert store.puts == []
    handled = _state.load(_paths.HANDLED_FILE)
    assert handled["a"] == {
        "result": {
            "handled_at": NOW,
            "id": "a",
            "message": "status recomputed and republished",
            "ok": True,
        },
        "republish": True,
        "written": False,
    }
    b = handled["b"]
    assert isinstance(b, dict)
    assert b["republish"] is False


def test_collect_never_evaluates_a_request_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _state.save(
        _paths.HANDLED_FILE,
        {
            "done": {"result": {}, "written": True, "republish": True},
            "pending": {"result": {}, "written": False, "republish": True},
        },
    )

    def evaluate(*_args: object, **_kwargs: object) -> None:
        msg = "re-evaluated a handled request"
        raise AssertionError(msg)

    monkeypatch.setattr(_requests, "evaluate", evaluate)
    store = FakeStore({f"{REQ}/done.json": "{}"})
    assert _requests.collect(store.client(), now=NOW) == (["done.json"], False)
    store = FakeStore({f"{REQ}/done.json": "{}", f"{REQ}/pending.json": "{}"})
    assert _requests.collect(store.client(), now=NOW)[1]


def test_finish_writes_the_result_then_deletes_the_request() -> None:
    store = FakeStore({f"{REQ}/a.json": _body(kind="refresh")})
    names, _ = _requests.collect(store.client(), now=NOW)
    _requests.finish(store.client(), names)
    result = store.files[f"{RES}/a.json"]
    assert isinstance(result, str)
    assert json.loads(result)["ok"] is True
    assert f"{REQ}/a.json" not in store.files
    entry = _state.load(_paths.HANDLED_FILE)["a"]
    assert isinstance(entry, dict)
    assert entry["written"] is True


def test_finish_does_not_rewrite_a_written_result() -> None:
    _state.save(
        _paths.HANDLED_FILE,
        {"a": {"result": {"id": "a"}, "written": True, "republish": False}},
    )
    store = FakeStore({f"{REQ}/a.json": "{}"})
    _requests.finish(store.client(), ["a.json"])
    assert store.puts == []
    assert store.deletes == [f"{REQ}/a.json"]


@pytest.mark.parametrize("entry", [None, "junk", {"result": "junk"}])
def test_finish_leaves_a_request_with_no_stored_result(
    entry: object, caplog: pytest.LogCaptureFixture
) -> None:
    if entry is not None:
        _state.save(_paths.HANDLED_FILE, {"a": entry})
    store = FakeStore({f"{REQ}/a.json": "{}"})
    with caplog.at_level(logging.WARNING):
        _requests.finish(store.client(), ["a.json"])
    assert store.deletes == []
    assert "no stored result for request a.json" in caplog.text


def _result_text(handled_at: object) -> str:
    return json.dumps({"id": "x", "handled_at": handled_at})


def test_sweep_expires_week_old_results_and_keeps_the_rest() -> None:
    week = _requests.RESULT_TTL_SECONDS
    store = FakeStore(
        {
            f"{RES}/old.json": _result_text(NOW - week - 1),
            f"{RES}/edge.json": _result_text(NOW - week),
            f"{RES}/bad.json": "{oops",
            f"{RES}/list.json": "[1]",
            f"{RES}/str.json": _result_text("yesterday"),
        }
    )
    _requests.sweep(store.client(), now=NOW)
    assert store.deletes == [f"{RES}/old.json"]


def test_sweep_forgets_old_and_corrupt_handled_ids() -> None:
    week = _requests.RESULT_TTL_SECONDS
    _state.save(
        _paths.HANDLED_FILE,
        {
            "old": {"result": {"handled_at": NOW - week - 1}},
            "new": {"result": {"handled_at": NOW}},
            "junk": "junk",
            "no_result": {"result": "junk"},
            "no_time": {"result": {"handled_at": "x"}},
        },
    )
    _requests.sweep(FakeStore().client(), now=NOW)
    assert list(_state.load(_paths.HANDLED_FILE)) == ["new"]


def test_sweep_leaves_the_handled_file_alone_when_nothing_expired() -> None:
    _state.save(_paths.HANDLED_FILE, {"new": {"result": {"handled_at": NOW}}})
    before = _paths.HANDLED_FILE.stat().st_mtime_ns
    _requests.sweep(FakeStore().client(), now=NOW)
    assert _paths.HANDLED_FILE.stat().st_mtime_ns == before
