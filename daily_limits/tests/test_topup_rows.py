# Copyright (c) 2026 Krzysztof Rudnicki
"""A top-up earner (the review) shows only once credited, never as a to-do."""

from __future__ import annotations

from datetime import date
import json
from typing import TYPE_CHECKING

from daily_limits import _answers, _compat, _report
from daily_limits.tests._samples import at

if TYPE_CHECKING:
    import pytest

    from daily_limits._answers import Answer

# The first day earned_time's registry lists the review top-up.
DAY = date(2026, 11, 23)
REGISTRY = _compat.earners(DAY)
TOPUPS = [item.name for item in REGISTRY if item.topup]
OTHERS = [item.name for item in REGISTRY if not item.topup]


def _build(monkeypatch: pytest.MonkeyPatch, topup: Answer) -> _report.Report:
    """The report for DAY; every paying earner open, top-ups answered ``topup``."""
    answers: dict[str, Answer] = {
        item.name: topup if item.topup else 0 for item in REGISTRY
    }
    monkeypatch.setattr(_answers, "answers_for", lambda *_args: answers)
    return _report.build(at("2026-11-23T10:00"))


def test_the_registry_has_a_topup_to_test() -> None:
    assert TOPUPS
    assert OTHERS


def test_a_topup_not_credited_has_no_row_anywhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _build(monkeypatch, topup=False)
    assert [row["name"] for row in report["earners"]] == OTHERS
    assert [row["name"] for row in report["todo"]] == OTHERS
    for item in REGISTRY:
        if item.topup:
            assert item.label not in json.dumps(report)


def test_a_topup_that_could_not_be_checked_has_no_row_either(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _build(monkeypatch, topup=None)
    assert [row["name"] for row in report["earners"]] == OTHERS
    assert [row["name"] for row in report["todo"]] == OTHERS


def test_a_credited_topup_shows_as_earned_and_is_never_a_todo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missed = _build(monkeypatch, topup=False)
    report = _build(monkeypatch, topup=True)
    rows = {row["name"]: row for row in report["earners"]}
    for name in TOPUPS:
        assert rows[name]["status"] == "done"
        assert rows[name]["shutdown_minutes"] == 0
    assert [row["name"] for row in report["earners"]] == [
        item.name for item in REGISTRY
    ]
    assert [row["name"] for row in report["todo"]] == OTHERS
    # The credit still moves the shutdown the review paid for.
    assert report["shutdown"]["resolved"] > missed["shutdown"]["resolved"]
