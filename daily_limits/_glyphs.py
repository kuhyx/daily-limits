# Copyright (c) 2026 Krzysztof Rudnicki
"""The popup's glyphs: what replaces its words (textgate, zero visible text).

Plain, single-colour BMP symbols only. The popup runs on the system Tk 8.6,
where a colour-emoji glyph can crash the X connection, so the phone's and the
bar's emoji (``💪 🧩 📖``) are mirrored here by monochrome shapes.
"""

from __future__ import annotations

from typing import Final

SHUTDOWN: Final = "⏻"
GAMING: Final = "♟"
LEISURE: Final = "☼"
# The registry's answer when the schedule says something else (Σ = computed).
RESOLVED: Final = "∑"
CEILING: Final = "↑"
SICK: Final = "✚"
# Nothing left to earn today.
ALL_EARNED: Final = "★"
# Shown in WARNING when a launch failed; the reason goes to the log.
PROBLEM: Final = "⚠"
STATUS: Final = {"done": "✓", "todo": "○", "unknown": "?"}

_EARNER: Final = {
    "workout": "♥",
    "leetcode": "{}",
    "reading": "¶",
    "anki": "▣",
    "automation": "⚙",
    "tutor": "⚙",
    "focus": "◎",
}


def earner(name: str) -> str:
    """The glyph for earner ``name``; a bullet for one not mapped here."""
    return _EARNER.get(name, "•")
