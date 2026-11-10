# Copyright (c) 2026 Krzysztof Rudnicki
"""The popup's focus row, against the fake tk module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from daily_limits import _report
from daily_limits import _tokens as tok
from daily_limits.tests import _samples
from daily_limits.tests._fake_tk import clickable, popup, texts

if TYPE_CHECKING:
    import pytest

    from daily_limits.tests._fake_tk import FakeWidget


def _focus_report() -> _report.Report:
    """The sample report with its second earner (todo) named ``focus``."""
    report = _samples.report()
    report["earners"][1]["name"] = "focus"
    report["todo"][0]["name"] = "focus"
    return report


def test_the_focus_row_opens_the_focus_work(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    opened: list[str] = []
    monkeypatch.setattr("daily_limits._focus_open.launch", lambda: opened.append("go"))
    root, _texts_drawn = popup(monkeypatch, _focus_report())
    cells = clickable(root)
    # Four cells of the earner row plus the row under "To extend".
    assert len(cells) == 5
    assert {str(w.options["cursor"]) for w in cells} == {"hand2"}
    for widget in cells:
        widget.bindings["<Button-1>"](object())
    assert opened == ["go"] * 5


def test_other_rows_are_notclickable(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    root, _texts_drawn = popup(monkeypatch, _samples.report())
    assert clickable(root) == []


def test_a_failed_focus_launch_warns_in_thepopup(
    monkeypatch: pytest.MonkeyPatch,
    roots: list[FakeWidget],
    caplog: pytest.LogCaptureFixture,
) -> None:
    del roots
    monkeypatch.setattr("daily_limits._focus_open.launch", lambda: "could not open")
    root, _texts_drawn = popup(monkeypatch, _focus_report())
    clickable(root)[0].bindings["<Button-1>"](object())
    assert dict(texts(root))["⚠"] == tok.WARNING
    assert "could not open" in caplog.text


def _missed_report(*, missed: bool) -> _report.Report:
    report = _focus_report()
    report["focus"] = {"project": "p", "missed": missed, "milestones": []}
    return report


def test_a_missed_milestone_turns_every_focus_cell_red(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    root, _texts_drawn = popup(monkeypatch, _missed_report(missed=True))
    cells = clickable(root)
    assert len(cells) == 5
    assert {str(w.options["fg"]) for w in cells} == {tok.DANGER}


def test_no_missed_milestone_keeps_the_usual_colours(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    root, _texts_drawn = popup(monkeypatch, _missed_report(missed=False))
    assert tok.DANGER not in {str(w.options["fg"]) for w in clickable(root)}


def test_missed_does_not_redden_other_rows(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    report = _missed_report(missed=True)
    _root, drawn = popup(monkeypatch, report)
    others = [fg for text, fg in drawn if text == "•"]
    assert others
    assert tok.DANGER not in others
