# Copyright (c) 2026 Krzysztof Rudnicki
"""The human summary."""

from __future__ import annotations

import pytest

from daily_limits import _render
from daily_limits.tests import _samples


@pytest.mark.parametrize(
    ("minutes", "text"), [(25, "25m"), (60, "1h"), (95, "1h35"), (0, "0m")]
)
def test_duration(minutes: int, text: str) -> None:
    assert _render.duration(minutes) == text


def test_summary_with_every_status() -> None:
    text = _render.summary(_samples.report())
    assert (
        "Shutdown   20:00 applied, 18:00 resolved   [floor 18:00, ceiling 23:00]"
        in text
    )
    assert "Gaming     3h budget, 1h34 used   [ceiling 8h]" in text
    assert "gaming day" not in text
    assert "[x] E0" in text
    assert "[ ] E1" in text
    assert "[?] E2" in text
    assert "could not check" in text
    assert "E1          -> shutdown 21:00\n" in text
    assert "E2          -> shutdown 22:00   (could not check)" in text
    assert text.endswith("never a no")


def test_summary_applied_equal_to_resolved() -> None:
    text = _render.summary(_samples.report(applied="18:00"))
    assert "Shutdown   18:00   [floor" in text


def test_summary_unreadable_schedule_and_playtime() -> None:
    text = _render.summary(_samples.report(applied=None, used=None))
    assert "18:00 (resolved; schedule unreadable)" in text
    assert "used unknown" in text


def test_summary_all_done_has_no_todo_and_no_footer() -> None:
    text = _render.summary(_samples.report(statuses=("done", "done")))
    assert "To extend" not in text
    assert "[?]" not in text


def test_summary_names_a_different_gaming_day() -> None:
    report = _samples.report(gaming_day="2026-10-08")
    assert _render.gaming_day_note(report) == " (gaming day 2026-10-08)"
    assert "[ceiling 8h] (gaming day 2026-10-08)" in _render.summary(report)
