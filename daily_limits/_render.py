# Copyright (c) 2026 Krzysztof Rudnicki
"""The human summary: what today allows, and what is left to earn more."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from daily_limits._report import Report

_MARK: Final = {"done": "[x]", "todo": "[ ]", "unknown": "[?]"}
_STATUS_WORD: Final = {"done": "done", "todo": "not yet", "unknown": "could not check"}


def duration(minutes: int) -> str:
    """``95`` -> ``1h35``; ``60`` -> ``1h``; ``25`` -> ``25m``."""
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f"{rest}m"
    return f"{hours}h{rest:02d}" if rest else f"{hours}h"


def _shutdown_line(report: Report) -> str:
    shut = report["shutdown"]
    applied = shut["applied"]
    if applied is None:
        head = f"Shutdown   {shut['resolved']} (resolved; schedule unreadable)"
    elif applied == shut["resolved"]:
        head = f"Shutdown   {applied}"
    else:
        head = f"Shutdown   {applied} applied, {shut['resolved']} resolved"
    return f"{head}   [floor {shut['floor']}, ceiling {shut['ceiling']}]"


def _gaming_line(report: Report) -> str:
    game = report["gaming"]
    budget = duration(game["budget_minutes"])
    used = game["used_minutes"]
    played = "used unknown" if used is None else f"{duration(used)} used"
    ceiling = duration(game["ceiling_minutes"])
    line = f"Gaming     {budget} budget, {played}   [ceiling {ceiling}]"
    return line + gaming_day_note(report)


def gaming_day_note(report: Report) -> str:
    """`` (gaming day YYYY-MM-DD)`` before 06:00, when it is not today."""
    day = report["gaming"]["day"]
    return "" if day == report["date"] else f" (gaming day {day})"


def summary(report: Report) -> str:
    """The multi-line text the bare ``daily-limits`` command prints."""
    lines = [f"Today {report['date']}", _shutdown_line(report), _gaming_line(report)]
    lines.append("")
    lines.append("Earners")
    for row in report["earners"]:
        mark = _MARK[row["status"]]
        # A done earner has nothing left to earn: show no "+0m", like the bar.
        amounts = " " * 30
        if row["status"] != "done":
            shutdown = duration(row["shutdown_minutes"])
            gaming = duration(row["gaming_minutes"])
            amounts = f"+{shutdown:>5} shutdown  +{gaming:>5} gaming"
        lines.append(
            f"  {mark} {row['label']:<11} {amounts}   {_STATUS_WORD[row['status']]}"
        )
    if report["todo"]:
        lines.append("")
        lines.append("To extend")
        lines.extend(
            f"  {row['label']:<11} -> shutdown {row['shutdown_after']}"
            + ("   (could not check)" if row["status"] == "unknown" else "")
            for row in report["todo"]
        )
    if any(row["status"] == "unknown" for row in report["earners"]):
        lines.append("")
        lines.append("[?] = could not check (no/unreadable ledger or key), never a no")
    return "\n".join(lines)
