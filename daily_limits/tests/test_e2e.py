# Copyright (c) 2026 Krzysztof Rudnicki
"""End-to-end encryption of ``--sync``: Firebase only ever sees ciphertext.

These go through the real :func:`_sync_client.get_sync_client` with a raw
:class:`FakeStore` as the Firebase client, so what lands in ``files`` is
exactly what would land in the RTDB. The phone is played by a second
encrypted client on the same raw store with the same passphrase.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from crdt_sync import open_encrypted_client
import pytest

from daily_limits import _paths, _sync, _sync_client
from daily_limits.tests import _samples
from daily_limits.tests._fake_store import FakeStore

if TYPE_CHECKING:
    from crdt_sync import EncryptingStore

    from daily_limits._report import Report

NOW = 1_791_540_000
PASSPHRASE = "test-passphrase"


@pytest.fixture
def raw(monkeypatch: pytest.MonkeyPatch) -> FakeStore:
    """The 'RTDB': a raw store handed out as the signed-in Firebase client."""
    fake = FakeStore()
    monkeypatch.setattr(
        _sync_client, "firebase_client_for", lambda *_a, **_k: fake.client()
    )
    monkeypatch.setattr(_sync, "_now", lambda: NOW)
    return fake


def _phone(raw: FakeStore) -> EncryptingStore:
    store, _ = open_encrypted_client(
        raw, _sync_client.OLD_PREFIX, passphrase=PASSPHRASE, params=_sync_client.ARGON2
    )
    return store


def _no_rebuild() -> Report:
    raise AssertionError


def _blobs(raw: FakeStore) -> str:
    return json.dumps(raw.files)


def test_paths_move_to_the_e2e_prefix() -> None:
    assert _sync_client.STATUS_PATH == "daily_limits-e2e/status.json"
    assert _sync_client.REQUESTS_DIR == "daily_limits-e2e/requests"
    assert _sync_client.RESULTS_DIR == "daily_limits-e2e/results"


def test_published_status_is_ciphertext(raw: FakeStore) -> None:
    _sync.tick(_samples.report(), _no_rebuild)
    sealed = raw.files[_sync_client.STATUS_PATH]
    assert isinstance(sealed, str)
    assert "published_at" not in sealed
    assert "device_id" not in sealed
    assert not any(path.startswith("daily_limits/") for path in raw.files)
    opened = _phone(raw).get_file_text(_sync_client.STATUS_PATH)
    assert opened is not None
    assert json.loads(opened)["published_at"] == NOW


def test_sealed_request_is_answered_with_a_sealed_result(raw: FakeStore) -> None:
    phone = _phone(raw)
    request = f"{_sync_client.REQUESTS_DIR}/r1.json"
    phone.put_file_text(
        request, json.dumps({"kind": "bogus", "created_at": NOW}), message="ask"
    )
    assert "bogus" not in _blobs(raw)
    _sync.tick(_samples.report(), _no_rebuild)
    result_path = f"{_sync_client.RESULTS_DIR}/r1.json"
    assert "handled_at" not in _blobs(raw)
    assert request not in raw.files
    opened = phone.get_file_text(result_path)
    assert opened is not None
    assert json.loads(opened)["message"].startswith("unknown kind 'bogus'")


def test_no_passphrase_skips_the_tick(
    raw: FakeStore, caplog: pytest.LogCaptureFixture
) -> None:
    _paths.PASSWORD_FILE.unlink()
    with caplog.at_level(logging.WARNING):
        _sync.tick(_samples.report(), _no_rebuild)
    assert raw.puts == []
    assert "firebase sync skipped" in caplog.text
    assert "e2e locked" in caplog.text


def test_blank_passphrase_skips_the_tick(raw: FakeStore) -> None:
    _paths.PASSWORD_FILE.write_text("  \n", encoding="utf-8")
    _sync.tick(_samples.report(), _no_rebuild)
    assert raw.puts == []


def test_wrong_passphrase_skips_the_tick(
    raw: FakeStore, caplog: pytest.LogCaptureFixture
) -> None:
    _phone(raw)  # the header now holds the real passphrase's check
    raw.puts.clear()
    _paths.PASSWORD_FILE.write_text("not-the-passphrase\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        _sync.tick(_samples.report(), _no_rebuild)
    assert raw.puts == []
    assert "e2e locked" in caplog.text
    assert _sync_client.STATUS_PATH not in raw.files


def test_a_plaintext_request_on_the_old_prefix_is_ignored(raw: FakeStore) -> None:
    old = "daily_limits/requests/r1.json"
    raw.files[old] = json.dumps({"kind": "refresh", "created_at": NOW})
    _sync.tick(_samples.report(), _no_rebuild)
    assert old in raw.files
    assert not any("results" in path for path in raw.files)
