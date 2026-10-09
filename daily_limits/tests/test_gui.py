# Copyright (c) 2026 Krzysztof Rudnicki
"""The Tk popup, drawn against a fake tk module -- never a real window."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from daily_limits import _gui, _report
from daily_limits import _tokens as tok
from daily_limits.tests import _samples

if TYPE_CHECKING:
    from collections.abc import Callable
    import tkinter as tk


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


def _texts(widget: FakeWidget) -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    for child in widget.children:
        if "text" in child.options:
            found.append((str(child.options["text"]), child.options["fg"]))
        found.extend(_texts(child))
    return found


@pytest.fixture
def roots(monkeypatch: pytest.MonkeyPatch) -> list[FakeWidget]:
    """Install the fake tk; returns the roots it creates."""
    created: list[FakeWidget] = []

    def make_root(**options: object) -> FakeWidget:
        root = FakeWidget()
        root.options.update(options)
        created.append(root)
        return root

    fake_tk = SimpleNamespace(Tk=make_root, Frame=FakeWidget, Label=FakeWidget)
    fake_font = SimpleNamespace(
        nametofont=lambda _name: SimpleNamespace(actual=lambda _key: "Fake Sans")
    )
    monkeypatch.setattr(_gui, "tk", fake_tk)
    monkeypatch.setattr(_gui, "tkfont", fake_font)
    return created


def _popup(
    monkeypatch: pytest.MonkeyPatch, report: _report.Report
) -> tuple[FakeWidget, list[tuple[str, object]]]:
    monkeypatch.setattr(_report, "build", lambda: report)
    root = FakeWidget()
    _gui.Popup(cast("tk.Tk", root))
    return root, _texts(root)


def test_popup_draws_the_report(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    root, texts = _popup(monkeypatch, _samples.report())
    labels = dict(texts)
    assert root.options["title"] == "Daily limits"
    assert root.options["bg"] == tok.INK
    assert "Shutdown 20:00" in labels
    assert "Gaming 3h · 1h34 used" in labels
    assert labels["ceiling 8h"] == tok.MUTED_ON_DARK
    assert labels["done"] == tok.SUCCESS
    assert labels["to do"] == tok.WARNING
    assert labels["could not check"] == tok.MUTED_ON_DARK
    assert labels["E1  →  shutdown 21:00"] == tok.TEXT_ON_DARK
    assert labels["E2  →  shutdown 22:00  (could not check)"] == tok.MUTED_ON_DARK


def test_popup_without_schedule_playtime_or_todo(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    report = _samples.report(
        applied=None, used=None, gaming_day="2026-10-08", statuses=("done",)
    )
    _root, texts = _popup(monkeypatch, report)
    labels = dict(texts)
    assert "Shutdown 18:00" in labels
    assert "Gaming 3h · used unknown" in labels
    assert "ceiling 8h (gaming day 2026-10-08)" in labels
    assert labels["Everything earned today."] == tok.SUCCESS
    assert "To extend" not in labels


def test_refresh_redraws_and_reschedules(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    root, _texts_first = _popup(monkeypatch, _samples.report())
    body = root.children[0]
    first_children = list(body.children)
    delay, callback = root.timers[0]
    assert delay == 60_000
    callback()
    assert all(child.destroyed for child in first_children)
    assert body.children
    assert len(root.timers) == 2


@pytest.mark.parametrize("key", ["<Escape>", "q"])
def test_escape_and_q_close(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget], key: str
) -> None:
    del roots
    root, _texts_drawn = _popup(monkeypatch, _samples.report())
    root.bindings[key](object())
    assert root.destroyed


def test_run_opens_a_classed_root_and_loops(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    monkeypatch.setattr(_report, "build", _samples.report)
    assert _gui.run() == 0
    assert [root.options["className"] for root in roots] == ["daily-limits"]
    assert roots[0].looped


def test_font_is_negative_pixels() -> None:
    assert tok.font("body") == (tok.FAMILY, -16, "normal")
    assert tok.font("title", bold=True) == (tok.FAMILY, -24, "bold")
