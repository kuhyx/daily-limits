# Copyright (c) 2026 Krzysztof Rudnicki
"""The ``leisure_shadow`` block (contract C5) of the shadow week.

The root steam-backlog-enforcer is the only accountant: it writes the shadow
fields (contract C4) into its world-readable ``playtime_state.json`` for the
same 06:00 gaming day as ``gaming``. This only reads them. The budget is the
enforcer's held ``shadow_budget_seconds`` (never re-resolved here), so
``would_block`` is exactly what it would block on. Any field missing, or a
state for another gaming day, is "no data": every number ``None``, never 0.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Final, TypedDict

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from daily_limits._leisure_now import Facts

_logger: Final = logging.getLogger(__name__)
_FIELDS: Final = ("shadow_seconds", "shadow_budget_seconds", "shadow_per_source")


class Source(TypedDict):
    """One billed source, largest first; ``label`` falls back to ``key``."""

    key: str
    label: str
    minutes: int


class LeisureShadow(TypedDict):
    """``leisure_shadow``: would-be numbers; ``None`` means no data."""

    day: str
    budget_minutes: int | None
    used_minutes: int | None
    left_minutes: int | None
    would_block: bool
    sources: list[Source]


def labels(facts: Facts | None) -> dict[str, str]:
    """Human labels for the keys counting right now (from ``now.json``)."""
    return {} if facts is None else {r.key: r.label for r in facts.reasons}


def _no_data(day: date) -> LeisureShadow:
    return {
        "day": day.isoformat(),
        "budget_minutes": None,
        "used_minutes": None,
        "left_minutes": None,
        "would_block": False,
        "sources": [],
    }


def _shadow_fields(
    state: Path, day: date
) -> tuple[float, float, dict[str, float]] | str:
    """``(used s, budget s, per-source s)``, or why there is no data."""
    try:
        raw = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _logger.warning("Cannot read the playtime state %s (%s)", state, exc)
        return "unreadable playtime state"
    if not isinstance(raw, dict) or raw.get("day_key") != day.isoformat():
        return f"{state} is not for gaming day {day}"
    used, budget, per_source = (raw.get(name) for name in _FIELDS)
    if not isinstance(used, int | float) or not isinstance(budget, int | float):
        return f"{state} has no shadow fields yet"
    if not isinstance(per_source, dict) or not all(
        isinstance(value, int | float) for value in per_source.values()
    ):
        return f"{state} has a malformed shadow_per_source"
    return float(used), float(budget), {str(k): float(v) for k, v in per_source.items()}


def build(state: Path, day: date, names: dict[str, str]) -> LeisureShadow:
    """The C5 block for gaming day ``day``, labelled with ``names``."""
    fields = _shadow_fields(state, day)
    if isinstance(fields, str):
        _logger.warning("Shadow leisure: no data (%s)", fields)
        return _no_data(day)
    used, budget, per_source = fields
    used_minutes, budget_minutes = int(used // 60), int(budget // 60)
    ranked = sorted(
        ((key, seconds) for key, seconds in per_source.items() if seconds > 0),
        key=lambda item: (-item[1], item[0]),
    )
    return {
        "day": day.isoformat(),
        "budget_minutes": budget_minutes,
        "used_minutes": used_minutes,
        "left_minutes": max(budget_minutes - used_minutes, 0),
        "would_block": used >= budget,
        "sources": [
            {"key": key, "label": names.get(key, key), "minutes": int(seconds // 60)}
            for key, seconds in ranked
        ],
    }
