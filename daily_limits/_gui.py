# Copyright (c) 2026 Krzysztof Rudnicki
"""A small Tk popup of the same report, drawn with the unified design tokens.

Read-only: it rebuilds the report every minute and never writes anything. Its
one button launches ``sickdays gui`` (``_sick_picker``), which owns its writes.
``Escape`` or ``q`` closes it. The window class is ``daily-limits`` so an i3
``for_window`` rule can float or place it.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import font as tkfont
from typing import TYPE_CHECKING, Final

from daily_limits import _focus_open, _render, _report, _sick_picker
from daily_limits import _glyphs as gl
from daily_limits import _tokens as tok

if TYPE_CHECKING:
    from daily_limits._report import Report

_logger: Final = logging.getLogger(__name__)
_REFRESH_MS: Final = 60_000
_STATUS_COLOUR: Final = {
    "done": tok.SUCCESS,
    "todo": tok.WARNING,
    "unknown": tok.MUTED_ON_DARK,
}
# The registry name of the focus earner: its row opens the work (see below).
_FOCUS: Final = "focus"


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
        # Replaced by the real one beside the sick-day button on every draw;
        # this unpacked placeholder only spares the handlers a None check.
        self._notice: tk.Label = tk.Label(self._body)
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

    def _open_focus(self, _event: object = None) -> None:
        """Click on the focus row: the tutor focus screen and the work URL."""
        self._warn(_focus_open.launch())

    def _warn(self, message: str | None) -> None:
        """A failed launch: a warning glyph by the button, the reason in the log."""
        if message is None:
            self._notice.configure(text="")
            return
        _logger.warning("%s", message)
        self._notice.configure(text=gl.PROBLEM)

    def _link(self, label: tk.Label, name: str) -> tk.Label:
        """Make ``label`` open the focus work when it is the focus row's."""
        if name == _FOCUS:
            label.configure(cursor="hand2")
            label.bind("<Button-1>", self._open_focus)
        return label

    @staticmethod
    def _tint(report: Report, name: str, fg: str) -> str:
        """``DANGER`` for the focus row while a milestone is missed, else ``fg``."""
        missed = name == _FOCUS and report.get("focus", {}).get("missed") is True
        return tok.DANGER if missed else fg

    def refresh(self) -> None:
        """Rebuild the report and redraw; reschedules itself."""
        for child in self._body.winfo_children():
            child.destroy()
        self._draw(_report.build())
        self._root.after(_REFRESH_MS, self.refresh)

    def _draw(self, report: Report) -> None:
        shut, game = report["shutdown"], report["gaming"]
        # Today's date; the sick-day cross sits by the button below.
        self._label(self._body, report["date"], "label", fg=tok.MUTED_ON_DARK).pack(
            anchor="w"
        )
        self._label(
            self._body,
            f"{gl.SHUTDOWN} {shut['applied'] or shut['resolved']}",
            "title",
            bold=True,
        ).pack(anchor="w", pady=(tok.XS, 0))
        detail = (
            f"{gl.RESOLVED} {shut['resolved']}   {shut['floor']} → {shut['ceiling']}"
        )
        self._label(self._body, detail, "caption", fg=tok.MUTED_ON_DARK).pack(
            anchor="w"
        )
        used = game["used_minutes"]
        played = "?" if used is None else _render.duration(used)
        self._label(
            self._body,
            f"{_budget_glyph(report)} {played} / "
            f"{_render.duration(game['budget_minutes'])}",
            "subtitle",
            bold=True,
        ).pack(anchor="w", pady=(tok.MD, 0))
        # The gaming day's date only when it is not today (before 06:00).
        day = "" if game["day"] == report["date"] else f"   {game['day']}"
        self._label(
            self._body,
            f"{gl.CEILING} {_render.duration(game['ceiling_minutes'])}{day}",
            "caption",
            fg=tok.MUTED_ON_DARK,
        ).pack(anchor="w")
        self._draw_earners(report)
        self._draw_todo(report)
        self._draw_sick_days(report)

    def _draw_earners(self, report: Report) -> None:
        budget = _budget_glyph(report)
        card = tk.Frame(self._body, bg=tok.INK_RAISED_1, padx=tok.MD, pady=tok.SM)
        card.pack(fill="x", pady=(tok.MD, 0))
        for row, earner in enumerate(report["earners"]):
            # A done earner has nothing left to earn: no "+0m", like the bar.
            done = earner["status"] == "done"
            shutdown = _render.duration(earner["shutdown_minutes"])
            gaming = _render.duration(earner["gaming_minutes"])
            cells: tuple[tuple[str, str, tok.TypeRole], ...] = (
                (gl.earner(earner["name"]), tok.TEXT_ON_DARK, "body"),
                (
                    "" if done else f"{gl.SHUTDOWN} +{shutdown}",
                    tok.MUTED_ON_DARK,
                    "label",
                ),
                ("" if done else f"{budget} +{gaming}", tok.MUTED_ON_DARK, "label"),
                (
                    gl.STATUS[earner["status"]],
                    _STATUS_COLOUR[earner["status"]],
                    "body",
                ),
            )
            for column, (text, fg, role) in enumerate(cells):
                tinted = self._tint(report, earner["name"], fg)
                self._link(
                    self._label(card, text, role, fg=tinted), earner["name"]
                ).grid(
                    row=row, column=column, sticky="w", padx=(0, tok.MD), pady=tok.XS
                )

    def _draw_todo(self, report: Report) -> None:
        if not report["todo"]:
            self._label(self._body, gl.ALL_EARNED, "title", fg=tok.SUCCESS).pack(
                anchor="w", pady=(tok.MD, 0)
            )
            return
        # One row per earner still to do: its glyph → the shutdown it earns.
        for index, row in enumerate(report["todo"]):
            unknown = row["status"] == "unknown"
            self._link(
                self._label(
                    self._body,
                    f"{gl.earner(row['name'])}  →  {gl.SHUTDOWN} "
                    f"{row['shutdown_after']}" + ("  ?" if unknown else ""),
                    "body",
                    fg=self._tint(
                        report,
                        row["name"],
                        tok.MUTED_ON_DARK if unknown else tok.TEXT_ON_DARK,
                    ),
                ),
                row["name"],
            ).pack(anchor="w", pady=(tok.MD if index == 0 else 0, 0))

    def _draw_sick_days(self, report: Report) -> None:
        row = tk.Frame(self._body, bg=tok.INK)
        row.pack(fill="x", pady=(tok.LG, 0))
        self._notice = self._label(row, "", "title", fg=tok.WARNING)
        notice = self._notice

        def open_picker() -> None:
            self._warn(_sick_picker.launch())

        # A ghost button (accent cross, one-pixel accent border on INK) that
        # opens the sickdays picker.
        tk.Button(
            row,
            text=gl.SICK,
            command=open_picker,
            fg=tok.ACCENT,
            bg=tok.INK,
            activeforeground=tok.ACCENT,
            activebackground=tok.INK_RAISED_1,
            highlightbackground=tok.ACCENT,
            highlightcolor=tok.ACCENT,
            highlightthickness=1,
            relief="flat",
            borderwidth=0,
            padx=tok.MD,
            pady=tok.XS,
            cursor="hand2",
            font=self._font("label", bold=True),
        ).pack(side="left")
        if report["sick"]:
            # Today is a sick day: an accent check by the sick-day button.
            self._label(row, gl.STATUS["done"], "title", fg=tok.ACCENT).pack(
                side="left", padx=(tok.MD, 0)
            )
        notice.pack(side="left", padx=(tok.MD, 0))


def _budget_glyph(report: Report) -> str:
    """The leisure sun once the leisure budget is live (Phase 2), else the pawn."""
    return gl.LEISURE if report.get("leisure_active") else gl.GAMING


def run() -> int:
    """Open the popup and block until it is closed."""
    root = tk.Tk(className="daily-limits")
    Popup(root)
    root.mainloop()
    return 0
