# Copyright (c) 2026 Krzysztof Rudnicki
"""The ``leisure_shadow`` block (contract C5) from the enforcer's C4 fields."""

from __future__ import annotations

from datetime import date
import json

import pytest

from daily_limits import _leisure_now, _paths, _shadow

DAY = date(2026, 10, 19)


def write_state(**fields: object) -> None:
    """Write a playtime state for ``DAY`` with ``fields`` on top."""
    state: dict[str, object] = {"day_key": DAY.isoformat(), "seconds": 0.0}
    state.update(fields)
    _paths.PLAYTIME_STATE.write_text(json.dumps(state), encoding="utf-8")


def c4(used: float, budget: float, **per_source: float) -> dict[str, object]:
    """The four C4 fields."""
    return {
        "shadow_seconds": used,
        "shadow_budget_seconds": budget,
        "shadow_per_source": per_source,
        "shadow_paused_seconds": 0.0,
    }


NO_DATA: _shadow.LeisureShadow = {
    "day": DAY.isoformat(),
    "budget_minutes": None,
    "used_minutes": None,
    "left_minutes": None,
    "would_block": False,
    "sources": [],
}


def test_a_state_without_the_c4_fields_says_no_data() -> None:
    write_state(budget_seconds=14400.0)
    assert _shadow.build(_paths.PLAYTIME_STATE, DAY, {}) == NO_DATA


def test_an_unreadable_state_says_no_data() -> None:
    assert _shadow.build(_paths.PLAYTIME_STATE, DAY, {}) == NO_DATA
    _paths.PLAYTIME_STATE.write_text("[1]", encoding="utf-8")
    assert _shadow.build(_paths.PLAYTIME_STATE, DAY, {}) == NO_DATA


@pytest.mark.parametrize("day_key", ["2026-10-18", "2026-10-20"])
def test_another_gaming_day_says_no_data(day_key: str) -> None:
    write_state(day_key=day_key, **c4(600, 36000))
    assert _shadow.build(_paths.PLAYTIME_STATE, DAY, {}) == NO_DATA


def test_malformed_per_source_says_no_data() -> None:
    write_state(**{**c4(600, 36000), "shadow_per_source": [1]})
    assert _shadow.build(_paths.PLAYTIME_STATE, DAY, {}) == NO_DATA
    write_state(**{**c4(600, 36000), "shadow_per_source": {"app:mpv": "x"}})
    assert _shadow.build(_paths.PLAYTIME_STATE, DAY, {}) == NO_DATA


def test_numbers_and_sources_largest_first() -> None:
    write_state(
        **c4(108 * 60 + 30, 300 * 60, **{"app:mpv": 59.0, "domain:youtube.com": 6450})
    )
    block = _shadow.build(
        _paths.PLAYTIME_STATE, DAY, {"domain:youtube.com": "YouTube — Helium"}
    )
    assert block == {
        "day": "2026-10-19",
        "budget_minutes": 300,
        "used_minutes": 108,
        "left_minutes": 192,
        "would_block": False,
        "sources": [
            {"key": "domain:youtube.com", "label": "YouTube — Helium", "minutes": 107},
            {"key": "app:mpv", "label": "app:mpv", "minutes": 0},
        ],
    }


def test_a_zero_second_source_is_left_out() -> None:
    write_state(**c4(60, 600, **{"app:mpv": 0.0, "app:vlc": 60}))
    block = _shadow.build(_paths.PLAYTIME_STATE, DAY, {})
    assert [row["key"] for row in block["sources"]] == ["app:vlc"]


@pytest.mark.parametrize(("used", "left"), [(600.0, 0), (605.0, 0)])
def test_at_or_over_the_budget_would_block(used: float, left: int) -> None:
    write_state(**c4(used, 600))
    block = _shadow.build(_paths.PLAYTIME_STATE, DAY, {})
    assert (block["left_minutes"], block["would_block"]) == (left, True)


def test_one_second_under_does_not_block() -> None:
    write_state(**c4(599.0, 600))
    assert not _shadow.build(_paths.PLAYTIME_STATE, DAY, {})["would_block"]


def test_labels_come_from_the_reasons() -> None:
    facts = _leisure_now.Facts(
        state="leisure",
        paused_by=None,
        reasons=(
            _leisure_now.Reason(source="game", key="steam:1", pid=None, label="Game"),
        ),
    )
    assert _shadow.labels(facts) == {"steam:1": "Game"}
    assert _shadow.labels(None) == {}


def test_leisure_shadow_for_the_gaming_day_with_live_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from daily_limits import _answers, _compat, _report
    from daily_limits.tests import test_leisure_now as c3
    from daily_limits.tests._samples import at

    names = [item.name for item in _compat.earners(date(2026, 10, 9))]
    monkeypatch.setattr(
        _answers, "answers_for", lambda day, moment: dict.fromkeys(names, 0)
    )
    moment = at("2026-10-09T10:00")
    _paths.PLAYTIME_STATE.write_text(
        json.dumps(
            {
                "day_key": "2026-10-09",
                "seconds": 0,
                "shadow_seconds": 7200,
                "shadow_budget_seconds": 36000,
                "shadow_per_source": {"app:mpv": 7200},
                "shadow_paused_seconds": 0,
            }
        ),
        encoding="utf-8",
    )
    c3.write_now(c3.sign(c3.now_doc(ts=moment.timestamp())))
    shadow = _report.build(moment)["leisure_shadow"]
    assert shadow == {
        "day": "2026-10-09",
        "budget_minutes": 600,
        "used_minutes": 120,
        "left_minutes": 480,
        "would_block": False,
        "sources": [{"key": "app:mpv", "label": "Film — mpv", "minutes": 120}],
    }
