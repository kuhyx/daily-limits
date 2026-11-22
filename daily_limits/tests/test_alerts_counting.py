# Copyright (c) 2026 Krzysztof Rudnicki
"""The splash's "what counts now" line, split from test_alerts.py (250-line cap)."""

from __future__ import annotations

import pytest

from daily_limits import _alerts, _leisure_now
from daily_limits.tests.test_alerts import COUNTING


@pytest.mark.parametrize(
    ("facts", "text"),
    [
        (COUNTING, "Film — mpv, YouTube — Helium"),
        (None, "❓"),
        (
            _leisure_now.Facts(state="paused", paused_by="i3lock", reasons=()),
            "⏸ i3lock",
        ),
        (_leisure_now.Facts(state="free", paused_by=None, reasons=()), "∅"),
    ],
)
def test_counting_now(facts: _leisure_now.Facts | None, text: str) -> None:
    assert _alerts.counting_now(facts) == text
