# Copyright (c) 2026 Krzysztof Rudnicki
"""A fake tk module and helpers for the popup tests -- never a real window."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from daily_limits import _gui, _report

if TYPE_CHECKING:
    from collections.abc import Callable
    import tkinter as tk

    import pytest


class FakeWidget:
    """Just enough of a Tk widget: options, children, bindings, timers."""

    def __init__(self, master: FakeWidget | None = None, **options: object) -> None:
        self.master = master
        self.options: dict[str, object] = dict(options)
        self.children: list[FakeWidget] = []
        self.bindings: dict[str, Callable[[object], object]] = {}
        self.timers: list[tuple[int, Callable[[], None]]] = []
        self.destroyed = False
        self.looped = False
        if master is not None:
            master.children.append(self)

    def configure(self, **options: object) -> None:
        self.options.update(options)

    def cget(self, key: str) -> object:
        return self.options.get(key, "")

    def pack(self, **_options: object) -> None:
        return None

    def grid(self, **_options: object) -> None:
        return None

    def winfo_children(self) -> list[FakeWidget]:
        return list(self.children)

    def destroy(self) -> None:
        self.destroyed = True
        if self.master is not None:
            self.master.children.remove(self)

    def title(self, text: str) -> None:
        self.options["title"] = text

    def resizable(self, **_options: object) -> None:
        return None

    def bind(self, sequence: str, handler: Callable[[object], object]) -> None:
        self.bindings[sequence] = handler

    def after(self, delay: int, callback: Callable[[], None]) -> None:
        self.timers.append((delay, callback))

    def mainloop(self) -> None:
        self.looped = True


def texts(widget: FakeWidget) -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    for child in widget.children:
        if "text" in child.options:
            found.append((str(child.options["text"]), child.options["fg"]))
        found.extend(texts(child))
    return found


def popup(
    monkeypatch: pytest.MonkeyPatch, report: _report.Report
) -> tuple[FakeWidget, list[tuple[str, object]]]:
    monkeypatch.setattr(_report, "build", lambda: report)
    root = FakeWidget()
    _gui.Popup(cast("tk.Tk", root))
    return root, texts(root)


def click(widget: FakeWidget, text: str) -> FakeWidget:
    """Invoke the button labelled ``text`` anywhere under ``widget``."""
    stack = [widget]
    while stack:
        found = stack.pop()
        if found.options.get("text") == text:
            cast("Callable[[], None]", found.options["command"])()
            return found
        stack.extend(found.children)
    raise LookupError(text)


def clickable(widget: FakeWidget) -> list[FakeWidget]:
    """Every widget under ``widget`` that reacts to a left click."""
    found = [child for child in widget.children if "<Button-1>" in child.bindings]
    for child in widget.children:
        found.extend(clickable(child))
    return found
