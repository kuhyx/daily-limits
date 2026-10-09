# Copyright (c) 2026 Krzysztof Rudnicki
"""A hand-built report for the render, CLI and GUI tests."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from daily_limits._report import Report, Status, TodoRow


def at(iso: str) -> datetime:
    """A local, timezone-aware moment."""
    return datetime.fromisoformat(iso).astimezone()


def report(
    *,
    applied: str | None = "20:00",
    resolved: str = "18:00",
    used: int | None = 94,
    gaming_day: str = "2026-10-09",
    statuses: tuple[Status, ...] = ("done", "todo", "unknown"),
) -> Report:
    """A report with one earner per status in ``statuses``."""
    names = [f"e{index}" for index in range(len(statuses))]
    todo: list[TodoRow] = [
        {
            "name": name,
            "label": name.upper(),
            "status": "unknown" if status == "unknown" else "todo",
            "shutdown_after": f"2{index}:00",
        }
        for index, (name, status) in enumerate(zip(names, statuses, strict=True))
        if status != "done"
    ]
    return {
        "date": "2026-10-09",
        "generated_at": 1791532875,
        "shutdown": {
            "applied": applied,
            "resolved": resolved,
            "floor": "18:00",
            "ceiling": "23:00",
        },
        "gaming": {
            "day": gaming_day,
            "budget_minutes": 180,
            "used_minutes": used,
            "ceiling_minutes": 480,
        },
        "earners": [
            {
                "name": name,
                "label": name.upper(),
                "status": status,
                "shutdown_minutes": 60,
                "gaming_minutes": 25,
            }
            for name, status in zip(names, statuses, strict=True)
        ],
        "todo": todo,
    }
