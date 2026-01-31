from __future__ import annotations

import datetime as dt
import json
import traceback
from typing import Any

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Dataset, DatasetJob
from app.services.analysis import analyze_dataframe
from app.services.data_loader import file_size_bytes, load_dataframe


def enqueue_dataset_analysis(dataset_id: str) -> None:
    """
    Background job entrypoint. Uses its own DB session.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(DatasetJob).filter(DatasetJob.dataset_id == dataset_id).order_by(DatasetJob.id.desc()).first()
        if not job:
            job = DatasetJob(dataset_id=dataset_id, status="queued", progress=0)
            db.add(job)
            db.commit()
            db.refresh(job)

        _set_job(db, job, status="running", progress=5)
        ds = db.get(Dataset, dataset_id)
        if not ds:
            _set_job(db, job, status="failed", progress=100, error="Dataset not found")
            return

        try:
            df = load_dataframe(ds.stored_path)
        except Exception as e:
            ds.status = "failed"
            ds.error = f"Failed to parse file: {e}"
            db.commit()
            _set_job(db, job, status="failed", progress=100, error=ds.error)
            return

        _set_job(db, job, status="running", progress=35)
        analysis = analyze_dataframe(df)
        analysis["meta"] = {
            "analysis_time_ms": None,
            "chart_count": int(len(analysis.get("charts") or [])),
            "row_count": int(df.shape[0]),
            "col_count": int(df.shape[1]),
        }
        analysis["file"] = {
            "original_filename": ds.original_filename,
            "stored_path": str(ds.stored_path).split("/")[-1],
            "size_bytes": file_size_bytes(ds.stored_path),
        }

        ds.analysis_json = json.dumps(analysis)
        ds.status = "ready"
        ds.error = ""
        db.commit()
        _set_job(db, job, status="succeeded", progress=100)
    except Exception:
        err = traceback.format_exc(limit=8)
        try:
            ds = db.get(Dataset, dataset_id)
            if ds:
                ds.status = "failed"
                ds.error = err[:2000]
                db.commit()
            job = db.query(DatasetJob).filter(DatasetJob.dataset_id == dataset_id).order_by(DatasetJob.id.desc()).first()
            if job:
                _set_job(db, job, status="failed", progress=100, error=err[:2000])
        except Exception:
            pass
    finally:
        db.close()


def get_latest_job(db: Session, dataset_id: str) -> dict[str, Any] | None:
    job = db.query(DatasetJob).filter(DatasetJob.dataset_id == dataset_id).order_by(DatasetJob.id.desc()).first()
    if not job:
        return None
    return {
        "id": int(job.id),
        "status": str(job.status),
        "progress": int(job.progress or 0),
        "error": str(job.error or ""),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _set_job(db: Session, job: DatasetJob, status: str, progress: int, error: str | None = None) -> None:
    job.status = status
    job.progress = int(progress)
    job.error = str(error or "")
    # Keep naive UTC for SQLite consistency
    job.updated_at = dt.datetime.utcnow()
    db.commit()

