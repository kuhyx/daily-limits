# Copyright (c) 2026 Krzysztof Rudnicki
"""The popup's glyphs: every registry earner is recognisable without a word."""

from __future__ import annotations

import re

import earned_time

from daily_limits import _glyphs as gl


def test_every_registry_earner_has_its_own_glyph() -> None:
    # Labels are no longer drawn, so a registry earner left on the bullet
    # would be anonymous in the popup. A registry bump must add a glyph here.
    names = [earner.name for earner in earned_time.EARNERS]
    glyphs = [gl.earner(name) for name in names]
    assert "•" not in glyphs
    assert len(set(glyphs)) == len(glyphs)


def test_an_unknown_earner_falls_back_to_a_bullet() -> None:
    assert gl.earner("not-a-registry-earner") == "•"


def test_glyphs_carry_no_words() -> None:
    every = [
        gl.SHUTDOWN,
        gl.GAMING,
        gl.LEISURE,
        gl.RESOLVED,
        gl.CEILING,
        gl.SICK,
        gl.ALL_EARNED,
        gl.PROBLEM,
        *gl.STATUS.values(),
        *(gl.earner(e.name) for e in earned_time.EARNERS),
    ]
    assert [g for g in every if re.search("[A-Za-z]{2,}", g)] == []
