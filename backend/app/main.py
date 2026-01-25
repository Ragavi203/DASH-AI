from __future__ import annotations

import json
import os
import secrets
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, init_db
from app.models import ChatMessage, Dataset
from app.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    DatasetCreateResponse,
    DatasetGetResponse,
    DatasetListItem,
    DatasetListResponse,
)
from app.services.analysis import analyze_dataframe
from app.services.chat import answer_question
from app.services.data_loader import file_size_bytes, load_dataframe, store_upload
from app.services.reports import render_pdf_report


settings = get_settings()

app = FastAPI(title="CSV → Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    settings.ensure_dirs()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/datasets/upload", response_model=DatasetCreateResponse)
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    dataset_id = str(uuid.uuid4())
    share_id = secrets.token_urlsafe(18)
    stored_path = store_upload(settings.upload_dir, dataset_id, file.filename, file.file)

    # Load & analyze
    try:
        df = load_dataframe(stored_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}") from e

    analysis = analyze_dataframe(df)
    analysis["file"] = {
        "original_filename": file.filename,
        "stored_path": Path(stored_path).name,
        "size_bytes": file_size_bytes(stored_path),
    }

    row = Dataset(
        id=dataset_id,
        share_id=share_id,
        original_filename=file.filename,
        stored_path=stored_path,
        analysis_json=json.dumps(analysis),
    )
    db.add(row)
    db.commit()

    return DatasetCreateResponse(dataset_id=dataset_id, share_id=share_id, analysis=analysis)


@app.get("/api/datasets/{dataset_id}", response_model=DatasetGetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetGetResponse(dataset_id=row.id, share_id=row.share_id, analysis=json.loads(row.analysis_json))


@app.get("/api/datasets", response_model=DatasetListResponse)
def list_datasets(db: Session = Depends(get_db)):
    rows = db.query(Dataset).order_by(Dataset.created_at.desc()).limit(100).all()
    items: list[DatasetListItem] = []
    for r in rows:
        try:
            analysis = json.loads(r.analysis_json or "{}")
            shape = (analysis.get("profile") or {}).get("shape") or {}
            n_rows = shape.get("rows")
            n_cols = shape.get("cols")
        except Exception:
            n_rows = None
            n_cols = None
        items.append(
            DatasetListItem(
                dataset_id=r.id,
                share_id=r.share_id,
                original_filename=r.original_filename,
                created_at=r.created_at.isoformat(),
                rows=n_rows if isinstance(n_rows, int) else None,
                cols=n_cols if isinstance(n_cols, int) else None,
            )
        )
    return DatasetListResponse(items=items)


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # delete chats
    db.query(ChatMessage).filter(ChatMessage.dataset_id == dataset_id).delete()

    # delete files (best-effort)
    try:
        if row.stored_path and os.path.exists(row.stored_path):
            os.remove(row.stored_path)
    except Exception:
        pass
    try:
        pdf_path = Path(settings.report_dir) / f"{dataset_id}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()
    except Exception:
        pass

    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/share/{share_id}", response_model=DatasetGetResponse)
def get_shared_dataset(share_id: str, db: Session = Depends(get_db)):
    row = db.query(Dataset).filter(Dataset.share_id == share_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Share link not found")
    return DatasetGetResponse(dataset_id=row.id, share_id=row.share_id, analysis=json.loads(row.analysis_json))


@app.post("/api/datasets/{dataset_id}/chat", response_model=ChatResponse)
def chat(dataset_id: str, req: ChatRequest, db: Session = Depends(get_db)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        df = load_dataframe(row.stored_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}") from e

    analysis = json.loads(row.analysis_json) if row.analysis_json else None
    ans = answer_question(df, req.question, analysis=analysis)

    # store history
    try:
        db.add(
            ChatMessage(
                dataset_id=dataset_id,
                role="user",
                message_type="text",
                content_json=json.dumps({"text": req.question}),
            )
        )
        db.add(
            ChatMessage(
                dataset_id=dataset_id,
                role="ai",
                message_type=str(ans.get("type") or "text"),
                content_json=json.dumps(ans),
            )
        )
        db.commit()
    except Exception:
        db.rollback()

    return ChatResponse(dataset_id=dataset_id, answer=ans)  # type: ignore[arg-type]


@app.get("/api/datasets/{dataset_id}/chat/history", response_model=ChatHistoryResponse)
def chat_history(dataset_id: str, db: Session = Depends(get_db)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    msgs = db.query(ChatMessage).filter(ChatMessage.dataset_id == dataset_id).order_by(ChatMessage.id.asc()).all()
    out = []
    for m in msgs:
        try:
            payload = json.loads(m.content_json or "{}")
        except Exception:
            payload = {}
        out.append(
            {
                "id": int(m.id),
                "role": "user" if m.role == "user" else "ai",
                "type": str(m.message_type or "text"),
                "text": str(payload.get("text") or payload.get("message") or ""),
                "table": payload.get("table"),
                "chart": payload.get("chart"),
                "citations": payload.get("citations"),
                "created_at": m.created_at.isoformat(),
            }
        )
    return {"dataset_id": dataset_id, "messages": out}


@app.get("/api/datasets/{dataset_id}/report.pdf")
def report_pdf(dataset_id: str, db: Session = Depends(get_db)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    analysis = json.loads(row.analysis_json)
    pdf_path = render_pdf_report(settings.report_dir, dataset_id, analysis)
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{dataset_id}.pdf")



