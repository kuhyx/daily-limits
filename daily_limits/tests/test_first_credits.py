# Copyright (c) 2026 Krzysztof Rudnicki
"""Maturity only delays a penalty: a gate that never paid out costs nothing.

A penalised stand-in earner (``piano``) joins the registry; its signed ledger
lives under the hermetic ``HOME``. Whether it has ever paid out decides the
first day its cut applies (earned_time 0.6.0); on an earned_time without
``maturity`` the report resolves exactly as 0.5.0 did.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta
import json
from typing import TYPE_CHECKING

import earned_time

from daily_limits import _answers, _compat, _paths, _report
from daily_limits.tests._samples import at
from daily_limits.tests.conftest import TEST_KEY

if TYPE_CHECKING:
    import pytest

DAY = date(2026, 10, 9)
_DAY = timedelta(days=1)


def _on_its_day(row: dict[str, object], window: tuple[float, float]) -> bool:
    """Count a credit for the day its ``day`` field names."""
    named: tuple[float, float] = earned_time.day_window(
        date.fromisoformat(str(row["day"]))
    )
    return window == named


# Penalised well before DAY, never confirmed by kuhy: a new gate.
PIANO = earned_time.Earner(
    name="piano",
    label="Piano",
    gaming_minutes=30,
    shutdown_minutes=30,
    ledger=".local/share/piano_guard/ledger.json",
    match=_on_its_day,
    penalty_from=DAY - 5 * _DAY,
)


def _credit_on(day: date) -> None:
    """Write the stand-in's ledger with one signed credit at noon on ``day``."""
    assert PIANO.ledger is not None
    when = datetime.combine(day, time(12)).astimezone()
    row: dict[str, object] = {
        "kind": "credit",
        "entry_id": "piano:1",
        "day": day.isoformat(),
        "created_at": when.isoformat(),
        "amount": 1,
        "detail": {"source": "piano"},
    }
    row["hmac"] = earned_time.entry_signature(row, TEST_KEY)
    path = _paths.HOME / PIANO.ledger
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"entries": [row]}), encoding="utf-8")


def test_maps_each_penalised_reader_to_its_first_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bonus, a ledger-less earner and a matcher-less one are left out."""
    registry = (
        PIANO,
        replace(PIANO, name="bonus", penalty_from=None),
        replace(PIANO, name="no-ledger", ledger=None),
        replace(PIANO, name="no-match", match=None),
    )
    monkeypatch.setattr(_compat, "earners", lambda day: registry)
    _credit_on(DAY - _DAY)
    assert _answers.first_credits(DAY) == {"piano": DAY - _DAY}


def test_an_old_earned_time_gets_no_map(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(earned_time, "maturity")
    assert _answers.first_credits(DAY) is None


def _floor() -> int:
    """DAY's real-registry budget with nothing done, before ``piano`` joins."""
    names = [item.name for item in _compat.earners(DAY)]
    minutes: int = earned_time.resolve(dict.fromkeys(names, 0), day=DAY).gaming_minutes
    return minutes


def _budget(monkeypatch: pytest.MonkeyPatch) -> int:
    """DAY's gaming budget with ``piano`` registered and nothing done."""
    monkeypatch.setattr(earned_time, "EARNERS", (*earned_time.EARNERS, PIANO))
    names = [item.name for item in _compat.earners(DAY)]
    monkeypatch.setattr(
        _answers, "answers_for", lambda day, moment: dict.fromkeys(names, 0)
    )
    return _report.build(at("2026-10-09T10:00"))["gaming"]["budget_minutes"]


def test_a_gate_that_never_paid_out_costs_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    floor = _floor()
    assert _budget(monkeypatch) == floor


def test_once_it_has_paid_out_its_cut_applies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credited the day before: penalised from DAY, by exactly its term."""
    floor = _floor()
    _credit_on(DAY - _DAY)
    assert _budget(monkeypatch) == floor - PIANO.gaming_minutes


def test_an_old_earned_time_resolves_as_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ``maturity``, no ``first_credits``: ``penalty_from`` alone cuts."""
    floor = _floor()
    monkeypatch.delattr(earned_time, "maturity")
    assert _budget(monkeypatch) == floor - PIANO.gaming_minutes
