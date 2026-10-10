# Copyright (c) 2026 Krzysztof Rudnicki
"""A small Tk popup of the same report, drawn with the unified design tokens.

Read-only: it rebuilds the report every minute and never writes anything.
``Escape`` or ``q`` closes it. The window class is ``daily-limits`` so an i3
``for_window`` rule can float or place it.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from typing import TYPE_CHECKING, Final

from daily_limits import _render, _report
from daily_limits import _tokens as tok

if TYPE_CHECKING:
    from daily_limits._report import Report

_REFRESH_MS: Final = 60_000
_STATUS_COLOUR: Final = {
    "done": tok.SUCCESS,
    "todo": tok.WARNING,
    "unknown": tok.MUTED_ON_DARK,
}
_STATUS_WORD: Final = {"done": "done", "todo": "to do", "unknown": "could not check"}


class Popup:
    """The window; :meth:`refresh` redraws it from a fresh report."""

    def __init__(self, root: tk.Tk) -> None:
        """Style ``root`` and draw the first report."""
        self._root = root
        self._family = tkfont.nametofont("TkDefaultFont").actual("family")
        root.title("Daily limits")
        root.configure(bg=tok.INK, padx=tok.LG, pady=tok.LG)
        root.resizable(width=False, height=False)
        root.bind("<Escape>", lambda _event: root.destroy())
        root.bind("q", lambda _event: root.destroy())
        self._body = tk.Frame(root, bg=tok.INK)
        self._body.pack(fill="both", expand=True)
        self.refresh()

    def _font(self, role: tok.TypeRole, *, bold: bool = False) -> tuple[str, int, str]:
        _family, size, weight = tok.font(role, bold=bold)
        return (self._family, size, weight)

    def _label(
        self,
        parent: tk.Misc,
        text: str,
        role: tok.TypeRole,
        *,
        fg: str = tok.TEXT_ON_DARK,
        bold: bool = False,
    ) -> tk.Label:
        bg = parent.cget("bg")
        return tk.Label(
            parent, text=text, fg=fg, bg=bg, font=self._font(role, bold=bold)
        )

    def refresh(self) -> None:
        """Rebuild the report and redraw; reschedules itself."""
        for child in self._body.winfo_children():
            child.destroy()
        self._draw(_report.build())
        self._root.after(_REFRESH_MS, self.refresh)

    def _draw(self, report: Report) -> None:
        shut, game = report["shutdown"], report["gaming"]
        self._label(
            self._body, f"Today {report['date']}", "label", fg=tok.MUTED_ON_DARK
        ).pack(anchor="w")
        self._label(
            self._body,
            f"Shutdown {shut['applied'] or shut['resolved']}",
            "title",
            bold=True,
        ).pack(anchor="w", pady=(tok.XS, 0))
        detail = (
            f"resolved {shut['resolved']}   floor {shut['floor']}"
            f"   ceiling {shut['ceiling']}"
        )
        self._label(self._body, detail, "caption", fg=tok.MUTED_ON_DARK).pack(
            anchor="w"
        )
        used = game["used_minutes"]
        played = "used unknown" if used is None else f"{_render.duration(used)} used"
        self._label(
            self._body,
            f"Gaming {_render.duration(game['budget_minutes'])} · {played}",
            "subtitle",
            bold=True,
        ).pack(anchor="w", pady=(tok.MD, 0))
        self._label(
            self._body,
            f"ceiling {_render.duration(game['ceiling_minutes'])}"
            + _render.gaming_day_note(report),
            "caption",
            fg=tok.MUTED_ON_DARK,
        ).pack(anchor="w")
        self._draw_earners(report)
        self._draw_todo(report)

    def _draw_earners(self, report: Report) -> None:
        card = tk.Frame(self._body, bg=tok.INK_RAISED_1, padx=tok.MD, pady=tok.SM)
        card.pack(fill="x", pady=(tok.MD, 0))
        for row, earner in enumerate(report["earners"]):
            colour = _STATUS_COLOUR[earner["status"]]
            # A done earner has nothing left to earn: no "+0m", like the bar.
            done = earner["status"] == "done"
            cells: tuple[tuple[str, str, tok.TypeRole], ...] = (
                (earner["label"], tok.TEXT_ON_DARK, "body"),
                (
                    "" if done else f"+{_render.duration(earner['shutdown_minutes'])}",
                    tok.MUTED_ON_DARK,
                    "label",
                ),
                (
                    ""
                    if done
                    else f"+{_render.duration(earner['gaming_minutes'])} game",
                    tok.MUTED_ON_DARK,
                    "label",
                ),
                (_STATUS_WORD[earner["status"]], colour, "label"),
            )
            for column, (text, fg, role) in enumerate(cells):
                self._label(card, text, role, fg=fg).grid(
                    row=row, column=column, sticky="w", padx=(0, tok.MD), pady=tok.XS
                )

    def _draw_todo(self, report: Report) -> None:
        if not report["todo"]:
            self._label(
                self._body, "Everything earned today.", "body", fg=tok.SUCCESS
            ).pack(anchor="w", pady=(tok.MD, 0))
            return
        self._label(self._body, "To extend", "label", fg=tok.MUTED_ON_DARK).pack(
            anchor="w", pady=(tok.MD, tok.XS)
        )
        for row in report["todo"]:
            unknown = row["status"] == "unknown"
            self._label(
                self._body,
                f"{row['label']}  →  shutdown {row['shutdown_after']}"
                + ("  (could not check)" if unknown else ""),
                "body",
                fg=tok.MUTED_ON_DARK if unknown else tok.TEXT_ON_DARK,
            ).pack(anchor="w")


def run() -> int:
    """Open the popup and block until it is closed."""
    root = tk.Tk(className="daily-limits")
    Popup(root)
    root.mainloop()
    return 0
