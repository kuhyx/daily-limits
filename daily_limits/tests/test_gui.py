# Copyright (c) 2026 Krzysztof Rudnicki
"""The Tk popup, drawn against a fake tk module -- never a real window."""

from __future__ import annotations

import re

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
    assert labels["2026-10-09"] == tok.MUTED_ON_DARK
    assert "⏻ 20:00" in labels
    assert labels["∑ 18:00   18:00 → 23:00"] == tok.MUTED_ON_DARK
    assert "♟ 1h34 / 3h" in labels
    assert labels["↑ 8h"] == tok.MUTED_ON_DARK
    assert ("✓", tok.SUCCESS) in texts
    # Only the todo and unknown rows show amounts; the done row's are blank.
    shown = [text for text, _fg in texts]
    assert shown.count("⏻ +1h") == 2
    assert shown.count("♟ +25m") == 2
    assert ("", tok.MUTED_ON_DARK) in texts
    assert ("○", tok.WARNING) in texts
    assert ("?", tok.MUTED_ON_DARK) in texts
    assert ("•  →  ⏻ 21:00", tok.TEXT_ON_DARK) in texts
    assert ("•  →  ⏻ 22:00  ?", tok.MUTED_ON_DARK) in texts


@pytest.mark.parametrize(
    "report",
    [
        _samples.report(),
        _samples.report(sick=True, applied=None, used=None, statuses=("done",)),
        _samples.report(leisure_active=True, gaming_day="2026-10-08"),
    ],
)
def test_popup_paints_no_words(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget], report: _report.Report
) -> None:
    """Textgate: no drawn label or button carries a run of 2+ letters."""
    del roots
    _root, drawn = popup(monkeypatch, report)
    assert drawn
    assert [text for text, _fg in drawn if re.search("[A-Za-z]{2,}", text)] == []


def test_earners_show_their_glyphs(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    report = _samples.report()
    for row, name in zip(
        report["earners"], ("workout", "leetcode", "zzz"), strict=True
    ):
        row["name"] = name
    shown = [text for text, _fg in popup(monkeypatch, report)[1]]
    assert {"♥", "{}", "•"} <= set(shown)


def test_popup_marks_a_sick_day(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    _root, texts = popup(monkeypatch, _samples.report(sick=True))
    assert "2026-10-09" in dict(texts)
    assert ("✓", tok.ACCENT) in texts


def test_popup_without_schedule_playtime_or_todo(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    report = _samples.report(
        applied=None, used=None, gaming_day="2026-10-08", statuses=("done",)
    )
    _root, texts = popup(monkeypatch, report)
    labels = dict(texts)
    assert "⏻ 18:00" in labels
    assert "♟ ? / 3h" in labels
    assert "↑ 8h   2026-10-08" in labels
    assert labels["★"] == tok.SUCCESS
    assert not [text for text in labels if "→  ⏻" in text]


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
    button = click(root, "✚")
    assert (button.options["fg"], button.options["bg"]) == (tok.ACCENT, tok.INK)
    assert launched == [["/b/sd", "gui"]]
    assert "⚠" not in dict(texts(root))


def test_sick_days_button_without_sickdays_warns(
    monkeypatch: pytest.MonkeyPatch,
    roots: list[FakeWidget],
    caplog: pytest.LogCaptureFixture,
) -> None:
    del roots
    root, drawn = popup(monkeypatch, _samples.report())
    assert ("✓", tok.ACCENT) not in drawn
    click(root, "✚")
    assert dict(texts(root))["⚠"] == tok.WARNING
    assert "sickdays is not installed" in caplog.text


def test_sick_day_caption_sits_by_the_button(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    _root, texts = popup(monkeypatch, _samples.report(sick=True))
    assert ("✓", tok.ACCENT) in texts


def test_font_is_negative_pixels() -> None:
    assert tok.font("body") == (tok.FAMILY, -16, "normal")
    assert tok.font("title", bold=True) == (tok.FAMILY, -24, "bold")


def test_popup_says_leisure_once_live(
    monkeypatch: pytest.MonkeyPatch, roots: list[FakeWidget]
) -> None:
    del roots
    report = _samples.report(leisure_active=True, gaming_day="2026-10-08")
    shown = [text for text, _fg in popup(monkeypatch, report)[1]]
    assert "☼ 1h34 / 3h" in shown
    assert "↑ 8h   2026-10-08" in shown
    assert shown.count("☼ +25m") == 2
    assert not [text for text in shown if "♟" in text]
