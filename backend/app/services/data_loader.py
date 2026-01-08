from __future__ import annotations

import os
from pathlib import Path
from typing import IO

import pandas as pd


SUPPORTED_EXTS = {".csv", ".tsv", ".xlsx", ".xls"}


def safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return ext if ext in SUPPORTED_EXTS else ""


def store_upload(upload_dir: str, dataset_id: str, original_filename: str, fileobj: IO[bytes]) -> str:
    ext = safe_ext(original_filename) or ".csv"
    dest = Path(upload_dir) / f"{dataset_id}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        while True:
            chunk = fileobj.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return str(dest)


def load_dataframe(stored_path: str, max_rows: int | None = None) -> pd.DataFrame:
    ext = Path(stored_path).suffix.lower()
    if ext == ".csv":
        return pd.read_csv(stored_path, nrows=max_rows)
    if ext == ".tsv":
        return pd.read_csv(stored_path, sep="\t", nrows=max_rows)
    if ext in {".xlsx", ".xls"}:
        df = pd.read_excel(stored_path)
        return df.head(max_rows) if max_rows else df
    # fallback
    return pd.read_csv(stored_path, nrows=max_rows)


def file_size_bytes(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0



