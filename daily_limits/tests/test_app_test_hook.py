# Copyright (c) 2026 Krzysztof Rudnicki
"""The ``flutter test (app)`` pre-commit hook must fit capped.sh's 2 GiB.

At flutter's default concurrency (cores - 2, 14 on kuhy's 16-core PC) the
test isolates peaked at 2.2 GB: the kernel OOM-killed the frontend server and
systemd stopped the capped scope with SIGTERM, so the board's checks run died
with exit -15 in the middle of the hook (2026-11-11). Two at a time peaks at
1.4 GB.
"""

from __future__ import annotations

from pathlib import Path
import re

CONFIG = Path(__file__).resolve().parents[2] / ".pre-commit-config.yaml"
MAX_JOBS = 2


def _app_test_entry() -> str:
    lines = CONFIG.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if "id: app-test" in line)
    return next(line for line in lines[start:] if "entry:" in line)


def test_app_test_hook_caps_concurrency() -> None:
    found = re.search(
        r"flutter test\b.*?(?:-j|--concurrency[= ])\s*(\d+)", _app_test_entry()
    )
    assert found, "flutter test hook runs at default concurrency (OOMs under capped.sh)"
    assert int(found.group(1)) <= MAX_JOBS
