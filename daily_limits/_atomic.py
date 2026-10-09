# Copyright (c) 2026 Krzysztof Rudnicki
"""Atomic text writes: the cache and the sync state must never be half-written."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


def write_atomic(target: Path, text: str) -> None:
    """Write ``text`` to ``target`` via a same-directory temp file + rename."""
    handle, temp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    temp = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        temp.chmod(0o644)
        temp.replace(target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
