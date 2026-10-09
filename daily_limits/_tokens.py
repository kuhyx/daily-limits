# Copyright (c) 2026 Krzysztof Rudnicki
"""Design tokens for the Tk popup, copied from the unified design system.

Source: ``~/src/utils/unified-design-system/DOCS-tokens.md`` (the same values
as gatelock's ``_theme.LockPalette``). gatelock is not imported because this
package stays stdlib + earned_time only; the hexes are the frozen shared
palette, so a copy cannot drift without ``palette_check.py`` noticing upstream.

Font sizes are **pixels**, so :func:`font` returns Tk's negative form (a
positive size means points and renders about a third larger).
"""

from __future__ import annotations

from typing import Final, Literal

# Neutrals (dark theme) + semantic roles.
INK: Final = "#211D1B"
INK_RAISED_1: Final = "#2B2624"
INK_RAISED_2: Final = "#38312E"
LINE_DARK: Final = "#463E3A"
TEXT_ON_DARK: Final = "#ECEAE9"
MUTED_ON_DARK: Final = "#AAA09A"
ACCENT: Final = "#B8862E"
SUCCESS: Final = "#8A9A3C"
WARNING: Final = "#E0A63C"
DANGER: Final = "#E2585F"
ON_FILL: Final = INK

# Spacing scale (4px base).
XS: Final = 4
SM: Final = 8
MD: Final = 16
LG: Final = 24
XL: Final = 32

TypeRole = Literal["display", "title", "subtitle", "body", "label", "caption"]
_TYPE_PX: Final[dict[TypeRole, int]] = {
    "display": 32,
    "title": 24,
    "subtitle": 20,
    "body": 16,
    "label": 14,
    "caption": 12,
}
FAMILY: Final = "TkDefaultFont"


def font(role: TypeRole, *, bold: bool = False) -> tuple[str, int, str]:
    """A Tk font tuple for ``role``, sized in pixels (negative)."""
    return (FAMILY, -_TYPE_PX[role], "bold" if bold else "normal")
