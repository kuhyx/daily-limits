# Copyright (c) 2026 Krzysztof Rudnicki
"""Publishing the status: on change, and on the heartbeat regardless."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from daily_limits import _publish, _sync_client
from daily_limits.tests import _samples
from daily_limits.tests._fake_store import FakeStore

if TYPE_CHECKING:
    from daily_limits._report import Report

NOW = 1_791_540_000


def test_device_id_is_minted_once_and_kept() -> None:
    first = _publish.device_id()
    assert first
    assert _publish.device_id() == first


def test_digest_ignores_the_per_build_timestamps() -> None:
    report = _samples.report()
    moved = cast("Report", {**report, "generated_at": 1, "published_at": 2})
    assert _publish.digest(moved) == _publish.digest(report)
    assert _publish.digest({**report, "date": "2026-10-10"}) != _publish.digest(report)


def test_publish_writes_the_contract_with_time_and_device() -> None:
    store = FakeStore()
    report = _samples.report()
    _publish.publish(store.client(), report, now=NOW)
    text = store.files[_sync_client.STATUS_PATH]
    assert isinstance(text, str)
    assert json.loads(text) == {
        **report,
        "published_at": NOW,
        "device_id": _publish.device_id(),
    }


def test_is_due_with_nothing_published_yet() -> None:
    assert _publish.is_due(_samples.report(), now=NOW)


def test_is_not_due_for_the_same_content_inside_the_heartbeat() -> None:
    report = _samples.report()
    _publish.publish(FakeStore().client(), report, now=NOW)
    later = NOW + _publish.HEARTBEAT_SECONDS - 1
    assert not _publish.is_due({**report, "generated_at": later}, now=later)


def test_is_due_when_the_content_changed() -> None:
    report = _samples.report()
    _publish.publish(FakeStore().client(), report, now=NOW)
    assert _publish.is_due({**report, "date": "2026-10-10"}, now=NOW + 1)


def test_is_due_on_the_heartbeat() -> None:
    report = _samples.report()
    _publish.publish(FakeStore().client(), report, now=NOW)
    assert _publish.is_due(report, now=NOW + _publish.HEARTBEAT_SECONDS)
