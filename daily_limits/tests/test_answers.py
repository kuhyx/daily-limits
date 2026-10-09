# Copyright (c) 2026 Krzysztof Rudnicki
"""Every earner is read generically from its own signed ledger."""

from __future__ import annotations

from datetime import date, datetime
import json
from typing import TYPE_CHECKING

import earned_time
import pytest

from daily_limits import _answers, _compat, _paths
from daily_limits.tests._samples import at
from daily_limits.tests.conftest import TEST_KEY

if TYPE_CHECKING:
    from pathlib import Path

DAY = date(2026, 10, 9)


def _always(row: dict[str, object], window: tuple[float, float]) -> bool:
    del window
    detail = row.get("detail")
    return isinstance(detail, dict) and detail.get("counts") == "1"


FLAT = earned_time.Earner(
    name="flat",
    label="Flat",
    gaming_minutes=10,
    shutdown_minutes=10,
    ledger=".local/share/flat/ledger.json",
    match=_always,
)
COUNTED = earned_time.Earner(
    name="counted",
    label="Counted",
    gaming_minutes=10,
    shutdown_minutes=10,
    kind="counted",
    ledger=".local/share/counted/ledger.json",
    match=_always,
)
BARE = earned_time.Earner(
    name="bare", label="Bare", gaming_minutes=1, shutdown_minutes=1, kind="counted"
)


def _write_ledger(item: earned_time.Earner, counts: str) -> None:
    assert item.ledger is not None
    row: dict[str, object] = {"kind": "credit", "detail": {"counts": counts}}
    row["hmac"] = earned_time.entry_signature(row, TEST_KEY)
    path = _paths.HOME / item.ledger
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"entries": [row]}), encoding="utf-8")


@pytest.mark.parametrize(
    ("moment", "expected"),
    [("2026-10-09T03:00", date(2026, 10, 8)), ("2026-10-09T06:00", DAY)],
)
def test_gaming_day_rolls_at_six(moment: str, expected: date) -> None:
    assert _answers.gaming_day(at(moment)) == expected


def test_cutoff_is_now_today_and_the_last_second_of_a_past_day() -> None:
    moment = at("2026-10-09T03:00")
    assert _answers._cutoff(DAY, moment) == moment
    past = _answers._cutoff(date(2026, 10, 8), moment)
    assert past.date() == date(2026, 10, 8)
    assert (past.hour, past.minute, past.second) == (23, 59, 59)


def test_an_earner_without_a_ledger_is_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert _answers.answer(BARE, DAY, at("2026-10-09T10:00")) is None
    assert f"has no ledger in earned_time {_compat.version()}" in caplog.text


@pytest.mark.parametrize(("counts", "expected"), [("1", True), ("0", False)])
def test_a_flat_earner_reads_its_real_signed_ledger(
    counts: str, expected: bool
) -> None:
    _write_ledger(FLAT, counts)
    assert _answers.answer(FLAT, DAY, datetime.now().astimezone()) is expected


def test_a_flat_earner_with_an_unreadable_ledger_is_unknown() -> None:
    assert _answers.answer(FLAT, DAY, at("2026-10-09T10:00")) is None


def test_a_counted_earner_goes_through_credit_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[object] = []

    def units(item: object, ledger: Path, key: Path, day: date, cutoff: object) -> int:
        seen.append((item, ledger, key, day, cutoff))
        return 3

    monkeypatch.setattr(_compat, "credit_units", units)
    moment = at("2026-10-09T10:00")
    assert _answers.answer(COUNTED, DAY, moment) == 3
    assert COUNTED.ledger is not None
    assert seen == [
        (COUNTED, _paths.HOME / COUNTED.ledger, _paths.KEY_FILE, DAY, moment)
    ]


def test_answers_for_asks_every_registered_earner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_answers, "answer", lambda item, day, moment: item.name)
    answers = _answers.answers_for(DAY, at("2026-10-09T10:00"))
    assert answers == {item.name: item.name for item in _compat.earners(DAY)}
