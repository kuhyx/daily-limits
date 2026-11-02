# Copyright (c) 2026 Krzysztof Rudnicki
"""The Tk popup, drawn against a fake tk module -- never a real window."""

from __future__ import annotations

import pytest

from daily_limits import _gui, _report
from daily_limits import _tokens as tok
from daily_limits.tests import _samples
from daily_limits.tests._fake_tk import FakeWidget, click, popup, texts


def test_popup_draws_the_report(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    root, texts = popup(monkeypatch, _samples.report())
    labels = dict(texts)
    assert root.options["title"] == "Daily limits"
    assert root.options["bg"] == tok.INK
    assert "Shutdown 20:00" in labels
    assert "Gaming 3h · 1h34 used" in labels
    assert labels["ceiling 8h"] == tok.MUTED_ON_DARK
    assert labels["done"] == tok.SUCCESS
    # Only the todo and unknown rows show amounts; the done row's are blank.
    assert [text for text, _fg in texts].count("+1h") == 2
    assert ("", tok.MUTED_ON_DARK) in texts
    assert labels["to do"] == tok.WARNING
    assert labels["could not check"] == tok.MUTED_ON_DARK
    assert labels["E1  →  shutdown 21:00"] == tok.TEXT_ON_DARK
    assert labels["E2  →  shutdown 22:00  (could not check)"] == tok.MUTED_ON_DARK


def test_popup_marks_a_sick_day(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    _root, texts = popup(monkeypatch, _samples.report(sick=True))
    assert "Today 2026-10-09 (sick day)" in dict(texts)


def test_popup_without_schedule_playtime_or_todo(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    report = _samples.report(
        applied=None, used=None, gaming_day="2026-10-08", statuses=("done",)
    )
    _root, texts = popup(monkeypatch, report)
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
    root, _texts_first = popup(monkeypatch, _samples.report())
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
    root, _texts_drawn = popup(monkeypatch, _samples.report())
    root.bindings[key](object())
    assert root.destroyed


def test_run_opens_a_classed_root_and_loops(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    monkeypatch.setattr(_report, "build", _samples.report)
    assert _gui.run() == 0
    assert [root.options["className"] for root in roots] == ["daily-limits"]
    assert roots[0].looped


def test_sick_days_button_launches_the_resolved_picker(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    launched: list[list[str]] = []
    monkeypatch.setattr("daily_limits._sick_picker.shutil.which", lambda _n: "/b/sd")
    monkeypatch.setattr(
        "daily_limits._detached.subprocess.Popen",
        lambda argv, **_kwargs: launched.append(argv),
    )
    root, _texts_drawn = popup(monkeypatch, _samples.report())
    button = click(root, "Sick days…")
    assert (button.options["fg"], button.options["bg"]) == (tok.ACCENT, tok.INK)
    assert launched == [["/b/sd", "gui"]]
    assert "sickdays is not installed" not in dict(texts(root))


def test_sick_days_button_without_sickdays_says_so(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    root, drawn = popup(monkeypatch, _samples.report())
    assert "Sick day" not in dict(drawn)
    click(root, "Sick days…")
    assert dict(texts(root))["sickdays is not installed"] == tok.WARNING


def test_sick_day_caption_sits_by_the_button(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    _root, texts = popup(monkeypatch, _samples.report(sick=True))
    assert dict(texts)["Sick day"] == tok.ACCENT


def test_font_is_negative_pixels() -> None:
    assert tok.font("body") == (tok.FAMILY, -16, "normal")
    assert tok.font("title", bold=True) == (tok.FAMILY, -24, "bold")


def test_popup_says_leisure_once_live(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    report = _samples.report(leisure_active=True, gaming_day="2026-10-08")
    shown = [text for text, _fg in popup(monkeypatch, report)[1]]
    assert "Leisure 3h · 1h34 used" in shown
    assert "ceiling 8h (leisure day 2026-10-08)" in shown
    assert shown.count("+25m leisure") == 2
    assert not [text for text in shown if "Gaming" in text or "game" in text]
