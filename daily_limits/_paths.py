# Copyright (c) 2026 Krzysztof Rudnicki
"""Every file this app reads or writes, and the programs it runs.

Module constants so tests redirect them (monkeypatch) instead of ever touching
the real ledgers, the real key or the real schedule. The only files written are
:data:`CACHE_NAME` under ``$XDG_RUNTIME_DIR``, the sync state under
:data:`STATE_DIR` and the shadow alerts' :data:`ALERT_STATE_FILE`. Ledgers, the
schedule and the budget are never written here.
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

# leisure-watch's signed "what counts right now" (contract C3), relative to
# $XDG_RUNTIME_DIR; $LEISURE_WATCH_NOW overrides it.
LEISURE_NOW_NAME: Final = "leisure-watch/now.json"

# The shadow week's alert bookkeeping: thresholds notified and the last splash,
# per gaming day.
ALERT_STATE_FILE: Final = HOME / ".local/state/daily-limits/shadow_alerts.json"

# The desktop helpers the shadow alerts run (looked up on PATH).
NOTIFY_SEND: Final = "notify-send"
SYSTEMD_RUN: Final = "systemd-run"
SYSTEMCTL: Final = "systemctl"
XRANDR: Final = "xrandr"

# --sync's own state: the device id, what was last published, handled requests.
STATE_DIR: Final = HOME / ".local/share/daily-limits"
DEVICE_ID_FILE: Final = STATE_DIR / ".device_id"
PUBLISH_STATE_FILE: Final = STATE_DIR / "publish_state.json"
HANDLED_FILE: Final = STATE_DIR / "handled_requests.json"

# The interpreter screen-locker is installed into (editable, system python).
# Absolute: the systemd user unit's PATH is not the login shell's.
SCREEN_LOCKER_PYTHON: Final = "/usr/bin/python3"
