from __future__ import annotations

from typing import IO


class S3Storage:
    """
    S3-ready placeholder.
    For interview story: you'd implement presigned uploads and store the object key instead of a local path.
    """

    def __init__(self, bucket: str):
        self.bucket = bucket

    def store_upload(self, dataset_id: str, original_filename: str, fileobj: IO[bytes]) -> str:
        raise NotImplementedError("S3 storage not wired in this demo. Use LocalStorage.")

    def delete(self, path: str) -> None:
        raise NotImplementedError("S3 storage not wired in this demo. Use LocalStorage.")

