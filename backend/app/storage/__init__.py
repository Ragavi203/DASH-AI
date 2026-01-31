from __future__ import annotations

from app.storage.local import LocalStorage


def get_storage():
    # Demo default (local disk). Can be swapped for S3 later.
    return LocalStorage()

