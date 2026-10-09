# Copyright (c) 2026 Krzysztof Rudnicki
"""One ``--sync`` tick: answer, rebuild, publish once, then write results."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from crdt_sync import RemoteSyncError
import pytest

from daily_limits import _publish, _sync, _sync_client
from daily_limits.tests import _samples
from daily_limits.tests._fake_store import FakeStore

if TYPE_CHECKING:
    from daily_limits._report import Report

NOW = 1_791_540_000
REQ = "daily_limits/requests"


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> FakeStore:
    fake = FakeStore()
    monkeypatch.setattr(_sync_client, "get_sync_client", fake.client)
    monkeypatch.setattr(_sync, "_now", lambda: NOW)
    return fake


class _Rebuild:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> Report:
        self.calls += 1
        return {**_samples.report(), "date": "2026-10-10"}


def _published(store: FakeStore) -> dict[str, object]:
    text = store.files[_sync_client.STATUS_PATH]
    assert isinstance(text, str)
    data = json.loads(text)
    assert isinstance(data, dict)
    return data


def test_now_is_unix_seconds() -> None:
    assert isinstance(_sync._now(), int)
    assert _sync._now() > NOW


def test_first_tick_publishes(store: FakeStore) -> None:
    rebuild = _Rebuild()
    _sync.tick(_samples.report(), rebuild)
    assert rebuild.calls == 0
    assert _published(store)["published_at"] == NOW
    assert store.puts == [_sync_client.STATUS_PATH]


def test_quiet_tick_publishes_nothing(store: FakeStore) -> None:
    _publish.publish(store.client(), _samples.report(), now=NOW - 60)
    store.puts.clear()
    _sync.tick(_samples.report(), _Rebuild())
    assert store.puts == []


def test_refresh_rebuilds_publishes_then_answers(store: FakeStore) -> None:
    _publish.publish(store.client(), _samples.report(), now=NOW - 60)
    store.puts.clear()
    body = {"kind": "refresh", "created_at": NOW}
    store.files[f"{REQ}/r1.json"] = json.dumps(body)
    rebuild = _Rebuild()
    _sync.tick(_samples.report(), rebuild)
    assert rebuild.calls == 1
    assert _published(store)["date"] == "2026-10-10"
    assert store.puts == [_sync_client.STATUS_PATH, "daily_limits/results/r1.json"]
    assert f"{REQ}/r1.json" not in store.files


def test_unavailable_sync_is_one_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def unavailable() -> None:
        msg = "not configured"
        raise _sync_client.SyncUnavailableError(msg)

    monkeypatch.setattr(_sync_client, "get_sync_client", unavailable)
    with caplog.at_level(logging.WARNING):
        _sync.tick(_samples.report(), _Rebuild())
    assert "firebase sync skipped: not configured" in caplog.text


def test_failed_tick_is_one_warning(
    store: FakeStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def down(_path: str) -> list[str]:
        msg = "network down"
        raise RemoteSyncError(msg)

    monkeypatch.setattr(store, "list_directory", down)
    with caplog.at_level(logging.WARNING):
        _sync.tick(_samples.report(), _Rebuild())
    assert "firebase sync failed this tick: network down" in caplog.text
