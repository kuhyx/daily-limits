# Copyright (c) 2026 Krzysztof Rudnicki
"""An in-memory stand-in for crdt_sync's ``FirebaseSyncClient``.

Only the four calls ``--sync`` makes. Paths are logical (``a/b.json``); a
value that is not a ``str`` models an RTDB leaf written as an object, which
``get_string_map`` leaves out -- exactly like the real client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from crdt_sync import FirebaseSyncClient


class FakeStore:
    """Files keyed by logical path; records every write and delete."""

    def __init__(self, files: dict[str, object] | None = None) -> None:
        self.files: dict[str, object] = dict(files or {})
        self.puts: list[str] = []
        self.deletes: list[str] = []

    def _children(self, path: str) -> dict[str, object]:
        prefix = f"{path}/"
        return {
            name.removeprefix(prefix): value
            for name, value in self.files.items()
            if name.startswith(prefix) and "/" not in name.removeprefix(prefix)
        }

    def list_directory(self, path: str) -> list[str]:
        return sorted(self._children(path))

    def get_string_map(self, path: str) -> dict[str, str]:
        return {
            name: value
            for name, value in self._children(path).items()
            if isinstance(value, str)
        }

    def put_file_text(self, path: str, text: str, *, message: str) -> None:
        assert message
        self.files[path] = text
        self.puts.append(path)

    def delete_file(self, path: str, *, message: str = "") -> None:
        assert message
        self.files.pop(path, None)
        self.deletes.append(path)

    def client(self) -> FirebaseSyncClient:
        """This fake, typed as the client the app expects."""
        return cast("FirebaseSyncClient", self)
