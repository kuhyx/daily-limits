# Copyright (c) 2026 Krzysztof Rudnicki
"""``--sync``'s local state: small JSON objects under ``_paths.STATE_DIR``.

A missing or corrupt file reads as ``{}``: the worst case is one extra publish
or one re-sent result, never a crashed tick. Writes are atomic.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from daily_limits._atomic import write_atomic

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)


def load(path: Path) -> dict[str, object]:
    """Return the JSON object at ``path``; ``{}`` when absent or unreadable."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _logger.warning("ignoring unreadable sync state %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        _logger.warning("ignoring sync state %s: not a JSON object", path)
        return {}
    return data


def save(path: Path, data: dict[str, object]) -> None:
    """Write ``data`` to ``path`` atomically, creating the state directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, json.dumps(data, sort_keys=True) + "\n")
