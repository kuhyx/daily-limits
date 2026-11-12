# Copyright (c) 2026 Krzysztof Rudnicki
"""The Firebase RTDB client ``--sync`` uses, and the logical paths it owns.

Error handling copied from home-guard's ``_sync_client.py``: ``ConfigError``
subclasses ``Exception`` directly, *not* ``RemoteSyncError``, so both are
caught explicitly. An unconfigured setup, a rejected credential and a locked
end-to-end key all mean "this machine cannot sync right now", never a crash
of the cache timer.

End-to-end encryption: every blob lives under ``daily_limits-e2e/`` sealed
with the key derived from the shared crdt-sync passphrase, so Firebase only
relays ciphertext. No passphrase (or a wrong one) is fail closed: the tick is
skipped and nothing, plaintext least of all, is written.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from crdt_sync import (
    ConfigError,
    E2eLayout,
    E2eLockedError,
    FirebaseAuthError,
    RemoteSyncError,
    firebase_client_for,
    open_encrypted_client,
)

from daily_limits import _paths

if TYPE_CHECKING:
    from crdt_sync import Argon2Params, EncryptingStore

APP_NAME: Final = "daily_limits"

# The pre-encryption prefix. Kept only to derive the layout: the plaintext
# copy there is never read, written or deleted any more.
OLD_PREFIX: Final = "daily_limits"
LAYOUT: Final = E2eLayout.of(OLD_PREFIX)

# Logical crdt_sync paths, the phone's exactly (each blob is sealed to its
# path). On the wire every ``.`` in a key is escaped (``status.json`` ->
# ``status~2Ejson``) and each value is a JSON *string* holding the sealed
# document -- that is crdt_sync's text-blob contract.
STATUS_PATH: Final = f"{LAYOUT.prefix}/status.json"
REQUESTS_DIR: Final = f"{LAYOUT.prefix}/requests"
RESULTS_DIR: Final = f"{LAYOUT.prefix}/results"

# Argon2id cost for a header this machine creates; ``None`` is crdt_sync's
# recommended cost. Tests lower it.
ARGON2: Argon2Params | None = None

# A tick runs every 60 s; one slow request must not eat the next tick.
_TIMEOUT_SECONDS: Final = 10.0

# Everything a Firebase tick can raise that means "no sync this tick":
# config/auth/transport errors, a state file that cannot be written, and a
# non-JSON response body.
SYNC_ERRORS: Final = (ConfigError, RemoteSyncError, OSError, ValueError)


class SyncUnavailableError(Exception):
    """Raised when no usable Firebase client could be built right now."""


def _passphrase() -> str:
    """The shared crdt-sync passphrase (blank is locked, as crdt_sync decides).

    Raises:
        SyncUnavailableError: This machine has no passphrase file.
    """
    try:
        return _paths.PASSWORD_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        msg = f"daily-limits sync e2e locked: no passphrase at {exc.filename}"
        raise SyncUnavailableError(msg) from exc


def get_sync_client() -> EncryptingStore:
    """Return the signed-in encrypted store, or raise :class:`SyncUnavailableError`.

    It reads requests and results with ``get_string_map`` (one GET for a
    whole directory) and opens each sealed entry.
    """
    try:
        client = firebase_client_for(APP_NAME, timeout_seconds=_TIMEOUT_SECONDS)
    except ConfigError as exc:
        msg = f"daily-limits sync not configured: {exc}"
        raise SyncUnavailableError(msg) from exc
    except FirebaseAuthError as exc:
        msg = f"daily-limits sync credentials rejected: {exc}"
        raise SyncUnavailableError(msg) from exc
    try:
        store, _ = open_encrypted_client(
            client, OLD_PREFIX, passphrase=_passphrase(), params=ARGON2
        )
    except E2eLockedError as exc:
        msg = f"daily-limits sync e2e locked: {exc}"
        raise SyncUnavailableError(msg) from exc
    return store
