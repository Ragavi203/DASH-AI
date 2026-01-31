from __future__ import annotations

from typing import IO

from app.config import get_settings
from app.services.data_loader import store_upload as _store_upload


class LocalStorage:
    def store_upload(self, dataset_id: str, original_filename: str, fileobj: IO[bytes]) -> str:
        settings = get_settings()
        return _store_upload(settings.upload_dir, dataset_id, original_filename, fileobj)

    def delete(self, path: str) -> None:
        import os

        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

