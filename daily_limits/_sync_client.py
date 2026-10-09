# Copyright (c) 2026 Krzysztof Rudnicki
"""The Firebase RTDB client ``--sync`` uses, and the logical paths it owns.

Error handling copied from home-guard's ``_sync_client.py``: ``ConfigError``
subclasses ``Exception`` directly, *not* ``RemoteSyncError``, so both are
caught explicitly. An unconfigured setup and a rejected credential both mean
"this machine cannot sync right now", never a crash of the cache timer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from crdt_sync import (
    ConfigError,
    FirebaseAuthError,
    RemoteSyncError,
    firebase_client_for,
)

if TYPE_CHECKING:
    from crdt_sync import FirebaseSyncClient

APP_NAME: Final = "daily_limits"

# Logical crdt_sync paths. On the wire every ``.`` in a key is escaped
# (``status.json`` -> ``status~2Ejson``) and each value is a JSON *string*
# holding the serialized document -- that is crdt_sync's text-blob contract.
STATUS_PATH: Final = "daily_limits/status.json"
REQUESTS_DIR: Final = "daily_limits/requests"
RESULTS_DIR: Final = "daily_limits/results"

# A tick runs every 60 s; one slow request must not eat the next tick.
_TIMEOUT_SECONDS: Final = 10.0

# Everything a Firebase tick can raise that means "no sync this tick":
# config/auth/transport errors, a state file that cannot be written, and a
# non-JSON response body.
SYNC_ERRORS: Final = (ConfigError, RemoteSyncError, OSError, ValueError)


class SyncUnavailableError(Exception):
    """Raised when no usable Firebase client could be built right now."""


def get_sync_client() -> FirebaseSyncClient:
    """Return a signed-in Firebase client, or raise :class:`SyncUnavailableError`.

    The concrete client, not the ``RemoteStore`` protocol: requests and results
    are read with ``get_string_map`` (one GET for a whole directory).
    """
    try:
        return firebase_client_for(APP_NAME, timeout_seconds=_TIMEOUT_SECONDS)
    except ConfigError as exc:
        msg = f"daily-limits sync not configured: {exc}"
        raise SyncUnavailableError(msg) from exc
    except FirebaseAuthError as exc:
        msg = f"daily-limits sync credentials rejected: {exc}"
        raise SyncUnavailableError(msg) from exc
