# Copyright (c) 2026 Krzysztof Rudnicki
"""Building the Firebase client: unconfigured or rejected is "unavailable"."""

from __future__ import annotations

from crdt_sync import ConfigError, FirebaseAuthError
import pytest

from daily_limits import _sync_client
from daily_limits.tests._fake_store import FakeStore


def test_returns_the_client_for_this_app(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeStore()
    seen: list[tuple[str, float]] = []

    def build(app: str, *, timeout_seconds: float) -> object:
        seen.append((app, timeout_seconds))
        return store

    monkeypatch.setattr(_sync_client, "firebase_client_for", build)
    assert _sync_client.get_sync_client() is store
    assert seen == [("daily_limits", 10.0)]


@pytest.mark.parametrize(
    ("error", "says"),
    [
        (ConfigError("no session"), "not configured"),
        (FirebaseAuthError("bad login"), "credentials rejected"),
    ],
)
def test_setup_failures_become_unavailable(
    monkeypatch: pytest.MonkeyPatch, error: Exception, says: str
) -> None:
    def build(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(_sync_client, "firebase_client_for", build)
    with pytest.raises(_sync_client.SyncUnavailableError, match=says):
        _sync_client.get_sync_client()
