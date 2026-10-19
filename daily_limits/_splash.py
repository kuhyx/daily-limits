# Copyright (c) 2026 Krzysztof Rudnicki
"""The shadow week's would-be-0 splash: what would be killed or blocked now.

Launched by ``_alerts`` in its own transient user unit. A large window centred
on the primary monitor, drawn with the unified design tokens. It must never
take the keyboard: it is override-redirect (i3 never manages, so never
focuses it), grabs nothing, and no widget takes focus. A click anywhere
dismisses it. Every 5 s it re-reads the cache and ``now.json``, raises
itself (a raise is not a focus change) and closes once no longer over.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import font as tkfont
from typing import TYPE_CHECKING, Final, cast

from daily_limits import _leisure_now, _paths, _render
from daily_limits import _tokens as tok

if TYPE_CHECKING:
    from pathlib import Path

    from daily_limits._leisure_now import Facts
    from daily_limits._shadow import LeisureShadow

_logger: Final = logging.getLogger(__name__)
_REFRESH_MS: Final = 5_000
Monitor = tuple[int, int, int, int]  # width, height, x, y
# `` 0: +*DP-0 3840/620x2160/340+0+0  DP-0`` from ``xrandr --listmonitors``.
_MONITOR: Final = re.compile(
    r"^\s*\d+:\s+\+?(\*?)\S+\s+(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)"
)


def primary_monitor(listing: str) -> Monitor | None:
    """The starred (primary) monitor in ``listing``, else the first one."""
    found = [m for m in map(_MONITOR.match, listing.splitlines()) if m is not None]
    for match in sorted(found, key=lambda m: m.group(1) != "*"):
        width, height, x, y = (int(match.group(n)) for n in range(2, 6))
        return (width, height, x, y)
    return None


def monitor() -> Monitor | None:
    """The primary monitor from ``xrandr --listmonitors``; ``None`` when unknown."""
    path = shutil.which(_paths.XRANDR)
    if path is None:
        _logger.warning(
            "%s is not on PATH; centring on the whole screen", _paths.XRANDR
        )
        return None
    try:
        done = subprocess.run(
            [path, "--listmonitors"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.warning("xrandr failed (%s); centring on the whole screen", exc)
        return None
    return primary_monitor(done.stdout)


def geometry(area: Monitor) -> str:
    """A ``WxH+X+Y`` 60 % x 50 % of ``area``, centred on it."""
    width, height, x, y = area
    w, h = width * 3 // 5, height // 2
    return f"{w}x{h}+{x + (width - w) // 2}+{y + (height - h) // 2}"


def lines(facts: Facts | None) -> list[str]:
    """What Phase 2 would kill or block right now, one line each."""
    if facts is None:
        return ["leisure-watch is silent: every focused app would count (fail closed)"]
    if facts.state == "paused":
        return [f"Nothing right now: paused by {facts.paused_by}"]
    if not facts.reasons:
        return ["Nothing is counting right now"]
    shown: list[str] = []
    for reason in facts.reasons:
        if reason.key.startswith("domain:"):
            shown.append(
                f"Block  {reason.label} (redirect to the 'leisure spent' page)"
            )
        else:
            pid = "" if reason.pid is None else f" (pid {reason.pid})"
            shown.append(f"Kill   {reason.label}{pid}")
    return shown


def read_shadow(cache: Path | None) -> LeisureShadow | None:
    """The cache's ``leisure_shadow``; ``None`` (logged) when unreadable.

    Also ``None`` once the leisure budget is live (``leisure_active``): the
    shadow week is over, so a splash still up closes and a new one never shows.
    """
    if cache is None:
        return None
    try:
        report = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _logger.warning("Cannot read the cache %s (%s)", cache, exc)
        return None
    report = report if isinstance(report, dict) else {}
    if report.get("leisure_active") is True:
        return None
    shadow = report.get("leisure_shadow")
    if not isinstance(shadow, dict):
        _logger.warning("The cache %s has no leisure_shadow", cache)
        return None
    return cast("LeisureShadow", shadow)


class Splash:
    """The window; :meth:`refresh` redraws it or closes it once not over."""

    def __init__(self, root: tk.Tk, cache: Path | None) -> None:
        """Place ``root`` (unmanaged, centred) and draw the first state."""
        self._root, self._cache = root, cache
        self._family = tkfont.nametofont("TkDefaultFont").actual("family")
        root.overrideredirect(boolean=True)
        area = monitor() or (root.winfo_screenwidth(), root.winfo_screenheight(), 0, 0)
        root.geometry(geometry(area))
        root.configure(bg=tok.INK, padx=tok.XL, pady=tok.XL, takefocus=0)
        root.bind("<Button-1>", self._dismiss)
        self._body = tk.Frame(root, bg=tok.INK, takefocus=0)
        self._body.pack(fill="both", expand=True)
        self._body.bind("<Button-1>", self._dismiss)
        self.refresh()

    def _dismiss(self, _event: object) -> None:
        self._root.destroy()

    def _line(
        self, text: str, role: tok.TypeRole, fg: str, *, bold: bool = False
    ) -> None:
        _family, size, weight = tok.font(role, bold=bold)
        label = tk.Label(
            self._body,
            text=text,
            fg=fg,
            bg=tok.INK,
            font=(self._family, size, weight),
            takefocus=0,
            anchor="w",
            justify="left",
        )
        label.pack(anchor="w", pady=(0, tok.SM))
        label.bind("<Button-1>", self._dismiss)

    def refresh(self) -> None:
        """Redraw from the cache and ``now.json``; close once not over."""
        shadow = read_shadow(self._cache)
        if shadow is None or not shadow["would_block"]:
            self._root.destroy()
            return
        for child in self._body.winfo_children():
            child.destroy()
        used, budget = shadow["used_minutes"] or 0, shadow["budget_minutes"] or 0
        self._line(
            "🛋 SHADOW: LEISURE WOULD BE BLOCKED NOW", "display", tok.DANGER, bold=True
        )
        self._line(
            f"{_render.duration(used)} used of {_render.duration(budget)}"
            " · shadow week: nothing is blocked yet",
            "subtitle",
            tok.TEXT_ON_DARK,
        )
        self._line(
            "From the switch-on day, at 0 this would:", "body", tok.MUTED_ON_DARK
        )
        for text in lines(_leisure_now.read()):
            self._line(text, "title", tok.WARNING, bold=True)
        self._line(
            "Click anywhere to dismiss · shown again every 15 min while over",
            "caption",
            tok.MUTED_ON_DARK,
        )
        self._root.lift()
        self._root.after(_REFRESH_MS, self.refresh)


def run(cache: Path | None) -> int:
    """Show the splash and block until it is dismissed or no longer over."""
    root = tk.Tk(className="daily-limits-splash")
    Splash(root, cache)
    root.mainloop()
    return 0
