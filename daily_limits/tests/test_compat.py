# Copyright (c) 2026 Krzysztof Rudnicki
"""Newer earned_time helpers when present, the 0.3.0 fields when not."""

from __future__ import annotations

from datetime import date
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

import earned_time

from daily_limits import _compat
from daily_limits.tests._samples import at

if TYPE_CHECKING:
    import pytest

DAY = date(2026, 10, 9)
ITEM = earned_time.Earner(name="x", label="X", gaming_minutes=7, shutdown_minutes=11)


def test_version_reads_the_installed_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dist = type("Dist", (), {"version": "9.9.9"})()
    monkeypatch.setattr(metadata, "distributions", lambda name: iter([dist]))
    assert _compat.version() == "9.9.9"


def test_version_without_a_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(metadata, "distributions", lambda name: iter([]))
    assert _compat.version() == "(source tree)"


def test_shutdown_minutes_uses_the_day_aware_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        earned_time, "shutdown_minutes_for", lambda item, day: 3, raising=False
    )
    assert _compat.shutdown_minutes(ITEM, DAY) == 3


def test_shutdown_minutes_falls_back_to_the_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(earned_time, "shutdown_minutes_for", raising=False)
    assert _compat.shutdown_minutes(ITEM, DAY) == 11


def test_shutdown_ceiling_uses_the_day_aware_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        earned_time, "shutdown_ceiling_for", lambda day: 5, raising=False
    )
    assert _compat.shutdown_ceiling(DAY) == 5


def test_shutdown_ceiling_falls_back_to_the_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(earned_time, "shutdown_ceiling_for", raising=False)
    assert _compat.shutdown_ceiling(DAY) == earned_time.SHUTDOWN_CEILING_MINUTES


def test_credit_units_uses_the_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []

    def units(item: object, ledger: Path, key: Path, day: date) -> int:
        seen.append((item, ledger, key, day))
        return 2

    monkeypatch.setattr(earned_time, "credit_units", units, raising=False)
    result = _compat.credit_units(
        ITEM, Path("l"), Path("k"), DAY, at("2026-10-09T10:00")
    )
    assert result == 2
    assert seen == [(ITEM, Path("l"), Path("k"), DAY)]


def test_credit_units_falls_back_to_done_today(monkeypatch: pytest.MonkeyPatch) -> None:
    cutoff = at("2026-10-09T10:00")
    seen: list[object] = []

    def done(item: object, ledger: Path, key: Path, *, now: object) -> bool:
        seen.append((item, ledger, key, now))
        return True

    monkeypatch.delattr(earned_time, "credit_units", raising=False)
    monkeypatch.setattr(earned_time, "done_today", done)
    assert _compat.credit_units(ITEM, Path("l"), Path("k"), DAY, cutoff) is True
    assert seen == [(ITEM, Path("l"), Path("k"), cutoff)]


class _Capped:
    """A capped counted gate (the tutor): 4 units, 13 shutdown minutes each."""

    max_units = 4
    gaming_minutes = 15
    max_gaming_minutes = 60

    def shutdown_for(self, units: int, day: date) -> int:
        del day
        return 13 * min(units, self.max_units)


def test_units_left_for_a_flat_and_a_capped_earner() -> None:
    capped = _Capped()
    assert [_compat.units_left(ITEM, a) for a in (None, 0, 1)] == [1, 1, 0]
    assert [_compat.units_left(capped, a) for a in (None, 1, 4, 5)] == [4, 3, 0, 0]


def test_shutdown_left_and_gaming_most() -> None:
    capped = _Capped()
    assert _compat.shutdown_left(capped, 1, DAY) == 39
    assert _compat.shutdown_left(capped, None, DAY) == 52
    assert _compat.shutdown_left(ITEM, 0, DAY) == _compat.shutdown_minutes(ITEM, DAY)
    assert _compat.gaming_most(capped) == 60
    assert _compat.gaming_most(ITEM) == 7


def test_earners_falls_back_to_the_static_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(earned_time, "earners_for", raising=False)
    assert _compat.earners(DAY) == tuple(earned_time.EARNERS)
    monkeypatch.setattr(earned_time, "earners_for", lambda day: (ITEM,), raising=False)
    assert _compat.earners(DAY) == (ITEM,)
