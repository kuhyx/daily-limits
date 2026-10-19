# Copyright (c) 2026 Krzysztof Rudnicki
"""The would-be-0 splash, drawn against a fake tk module -- never a real window."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from daily_limits import _leisure_now, _paths, _splash
from daily_limits import _tokens as tok
from daily_limits.tests.test_gui import FakeWidget

if TYPE_CHECKING:
    from pathlib import Path
    import tkinter as tk

XRANDR = (
    "Monitors: 2\n"
    " 0: +*DP-0 3840/620x2160/340+0+0  DP-0\n"
    " 1: +HDMI-0 2560/698x1440/393+3840+0  HDMI-0\n"
)
MPV = _leisure_now.Reason(source="media", key="app:mpv", pid=42, label="Film — mpv")
YT = _leisure_now.Reason(source="focus", key="domain:youtube.com", pid=7, label="YT")
GAME = _leisure_now.Reason(source="game", key="steam:9", pid=None, label="Hades")


class FakeRoot(FakeWidget):
    """A toplevel: the window-manager calls the splash makes."""

    def overrideredirect(self, *, boolean: bool) -> None:
        self.options["overrideredirect"] = boolean

    def geometry(self, spec: str) -> None:
        self.options["geometry"] = spec

    def lift(self) -> None:
        self.options["lifted"] = int(cast("int", self.options.get("lifted", 0))) + 1

    def winfo_screenwidth(self) -> int:
        return 1920

    def winfo_screenheight(self) -> int:
        return 1080


@pytest.fixture
def roots(monkeypatch: pytest.MonkeyPatch) -> list[FakeRoot]:
    created: list[FakeRoot] = []

    def make_root(**options: object) -> FakeRoot:
        root = FakeRoot()
        root.options.update(options)
        created.append(root)
        return root

    fake_tk = SimpleNamespace(Tk=make_root, Frame=FakeWidget, Label=FakeWidget)
    fake_font = SimpleNamespace(
        nametofont=lambda _name: SimpleNamespace(actual=lambda _key: "Fake Sans")
    )
    monkeypatch.setattr(_splash, "tk", fake_tk)
    monkeypatch.setattr(_splash, "tkfont", fake_font)
    return created


def write_cache(path: Path, *, would_block: bool = True, used: int = 605) -> Path:
    shadow = {
        "day": "2026-10-19",
        "budget_minutes": 600,
        "used_minutes": used,
        "left_minutes": 0 if would_block else 600 - used,
        "would_block": would_block,
        "sources": [],
    }
    path.write_text(json.dumps({"leisure_shadow": shadow}), encoding="utf-8")
    return path


def texts(widget: FakeWidget) -> list[str]:
    found: list[str] = []
    for child in widget.children:
        if "text" in child.options:
            found.append(str(child.options["text"]))
        found.extend(texts(child))
    return found


def every(widget: FakeWidget) -> list[FakeWidget]:
    found = [widget]
    for child in widget.children:
        found.extend(every(child))
    return found


def test_primary_monitor_from_xrandr() -> None:
    assert _splash.primary_monitor(XRANDR) == (3840, 2160, 0, 0)
    no_star = XRANDR.replace("+*DP-0", "+DP-0")
    assert _splash.primary_monitor(no_star) == (3840, 2160, 0, 0)
    assert _splash.primary_monitor("Monitors: 0\n") is None


def test_geometry_is_centred_on_the_monitor() -> None:
    assert _splash.geometry((3840, 2160, 0, 0)) == "2304x1080+768+540"
    assert _splash.geometry((2560, 1440, 3840, 0)) == "1536x720+4352+360"


def test_monitor_asks_xrandr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "xrandr"
    fake.write_text(f"#!/bin/bash\nprintf '%s' '{XRANDR}'\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setattr(_paths, "XRANDR", str(fake))
    assert _splash.monitor() == (3840, 2160, 0, 0)


def test_monitor_without_xrandr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    assert _splash.monitor() is None
    broken = tmp_path / "xrandr"
    broken.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    broken.chmod(0o755)
    monkeypatch.setattr(_paths, "XRANDR", str(broken))
    with caplog.at_level(logging.WARNING):
        assert _splash.monitor() is None
    assert "xrandr failed" in caplog.text


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (
            _leisure_now.Facts(
                state="leisure", paused_by=None, reasons=(MPV, YT, GAME)
            ),
            [
                "Kill   Film — mpv (pid 42)",
                "Block  YT (redirect to the 'leisure spent' page)",
                "Kill   Hades",
            ],
        ),
        (
            None,
            ["leisure-watch is silent: every focused app would count (fail closed)"],
        ),
        (
            _leisure_now.Facts(state="paused", paused_by="i3lock", reasons=()),
            ["Nothing right now: paused by i3lock"],
        ),
        (
            _leisure_now.Facts(state="free", paused_by=None, reasons=()),
            ["Nothing is counting right now"],
        ),
    ],
)
def test_lines(facts: _leisure_now.Facts | None, expected: list[str]) -> None:
    assert _splash.lines(facts) == expected


def test_read_shadow(tmp_path: Path) -> None:
    assert _splash.read_shadow(None) is None
    assert _splash.read_shadow(tmp_path / "absent.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    assert _splash.read_shadow(bad) is None
    shadow = _splash.read_shadow(write_cache(tmp_path / "c.json"))
    assert shadow is not None
    assert shadow["used_minutes"] == 605


def test_splash_draws_what_would_be_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, roots: list[FakeRoot]
) -> None:
    del roots
    facts = _leisure_now.Facts(state="leisure", paused_by=None, reasons=(MPV,))
    monkeypatch.setattr(_leisure_now, "read", lambda: facts)
    monkeypatch.setattr(_splash, "monitor", lambda: (3840, 2160, 0, 0))
    root = FakeRoot()
    _splash.Splash(cast("tk.Tk", root), write_cache(tmp_path / "c.json"))
    shown = texts(root)
    assert root.options["overrideredirect"] is True
    assert root.options["geometry"] == "2304x1080+768+540"
    assert root.options["bg"] == tok.INK
    assert "🛋 SHADOW: LEISURE WOULD BE BLOCKED NOW" in shown
    assert "10h05 used of 10h · shadow week: nothing is blocked yet" in shown
    assert "Kill   Film — mpv (pid 42)" in shown
    assert any("Click anywhere to dismiss" in text for text in shown)
    # No widget may take keyboard focus; a click anywhere dismisses.
    assert all(w.options.get("takefocus", 0) == 0 for w in every(root)[1:])
    every(root)[-1].bindings["<Button-1>"](object())
    assert root.destroyed


def test_refresh_redraws_lifts_and_closes_once_not_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, roots: list[FakeRoot]
) -> None:
    del roots
    monkeypatch.setattr(_leisure_now, "read", lambda: None)
    monkeypatch.setattr(_splash, "monitor", lambda: None)
    cache = write_cache(tmp_path / "c.json")
    root = FakeRoot()
    _splash.Splash(cast("tk.Tk", root), cache)
    assert root.options["geometry"] == "1152x540+384+270"
    delay, callback = root.timers[0]
    assert delay == 5_000
    callback()
    assert root.options["lifted"] == 2
    assert len(root.timers) == 2
    write_cache(cache, would_block=False, used=500)
    root.timers[1][1]()
    assert root.destroyed


def test_no_data_never_shows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, roots: list[FakeRoot]
) -> None:
    del roots
    monkeypatch.setattr(_leisure_now, "read", lambda: None)
    monkeypatch.setattr(_splash, "monitor", lambda: None)
    root = FakeRoot()
    _splash.Splash(cast("tk.Tk", root), tmp_path / "absent.json")
    assert root.destroyed


def test_run_opens_a_classed_root_and_loops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, roots: list[FakeRoot]
) -> None:
    monkeypatch.setattr(_leisure_now, "read", lambda: None)
    monkeypatch.setattr(_splash, "monitor", lambda: None)
    assert _splash.run(write_cache(tmp_path / "c.json")) == 0
    assert [root.options["className"] for root in roots] == ["daily-limits-splash"]
    assert roots[0].looped
