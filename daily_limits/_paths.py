# Copyright (c) 2026 Krzysztof Rudnicki
"""Every file this app reads or writes -- all read-only except the cache.

Module constants so tests redirect them (monkeypatch) instead of ever touching
the real ledgers, the real key or the real schedule. Nothing here is written to
except :data:`CACHE_NAME` under ``$XDG_RUNTIME_DIR``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

HOME: Final = Path.home()

# The shared HMAC key every gate signs its ledger rows with.
KEY_FILE: Final = Path("/etc/workout-locker/hmac.key")

# screen-locker's applied schedule (root-owned, immutable, world-readable).
SCHEDULE_FILE: Final = Path("/etc/shutdown-schedule.conf")

# steam-backlog-enforcer's day state (root-owned, 0644 on purpose).
PLAYTIME_STATE: Final = HOME / ".config/steam_backlog_enforcer/playtime_state.json"

# The cache the i3blocks block reads; lives in $XDG_RUNTIME_DIR.
CACHE_NAME: Final = "daily-limits.json"
