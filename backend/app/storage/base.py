from __future__ import annotations

from typing import IO, Protocol


class Storage(Protocol):
    def store_upload(self, dataset_id: str, original_filename: str, fileobj: IO[bytes]) -> str: ...
    def delete(self, path: str) -> None: ...

