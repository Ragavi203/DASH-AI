from __future__ import annotations

import json
import logging
import os
import secrets
import time
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_current_user
from app.db import get_db, init_db
from app.middleware.logging_filter import RequestIdFilter
from app.middleware.request_id import RequestIdMiddleware
from app.models import AiEvent, ChatMessage, Dataset, User
from app.schemas import (
    AuthRequestCodeRequest,
    AuthRequestCodeResponse,
    AuthVerifyCodeRequest,
    AuthVerifyCodeResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    DatasetCreateResponse,
    DatasetGetResponse,
    DatasetListItem,
    DatasetListResponse,
    PivotRequest,
    PivotResponse,
)
from app.services.analysis import analyze_dataframe
from app.services.auth import request_login_code, verify_login_code
from app.services.chat import answer_question
from app.services.data_loader import file_size_bytes, load_dataframe, store_upload
from app.services.dataset_jobs import enqueue_dataset_analysis, get_latest_job
from app.services.reports import render_pdf_report
from app.services.spike_explain import explain_spike
from app.services.pivot import run_pivot
from app.middleware.request_id import request_id_var
from app.storage import get_storage


settings = get_settings()
log = logging.getLogger("dashai")
if not any(isinstance(f, RequestIdFilter) for f in log.filters):
    log.addFilter(RequestIdFilter())

app = FastAPI(title="CSV → Dashboard API", version="0.1.0")

app.add_middleware(RequestIdMiddleware)
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

@app.post("/api/auth/request_code", response_model=AuthRequestCodeResponse)
def auth_request_code(req: AuthRequestCodeRequest, db: Session = Depends(get_db)):
    try:
        return request_login_code(db, req.email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/auth/verify_code", response_model=AuthVerifyCodeResponse)
def auth_verify_code(req: AuthVerifyCodeRequest, db: Session = Depends(get_db)):
    try:
        return verify_login_code(db, req.email, req.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/datasets/upload", response_model=DatasetCreateResponse)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    dataset_id = str(uuid.uuid4())
    share_id = secrets.token_urlsafe(18)
    storage = get_storage()
    stored_path = storage.store_upload(dataset_id, file.filename, file.file)
    size_bytes = file_size_bytes(stored_path)

    # Async for large uploads; sync for small (better UX)
    if size_bytes >= int(settings.upload_async_threshold_bytes):
        row = Dataset(
            id=dataset_id,
            share_id=share_id,
            user_id=int(user.id),
            original_filename=file.filename,
            stored_path=stored_path,
            status="processing",
            analysis_json="{}",
        )
        db.add(row)
        db.commit()
        background_tasks.add_task(enqueue_dataset_analysis, dataset_id)
        return DatasetCreateResponse(
            dataset_id=dataset_id,
            share_id=share_id,
            status="processing",
            analysis={"status": "processing", "file": {"original_filename": file.filename, "stored_path": Path(stored_path).name, "size_bytes": size_bytes}},
        )

    t0 = time.perf_counter()
    try:
        df = load_dataframe(stored_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}") from e

    analysis = analyze_dataframe(df)
    analysis_time_ms = int((time.perf_counter() - t0) * 1000)
    analysis["meta"] = {
        "analysis_time_ms": analysis_time_ms,
        "chart_count": int(len(analysis.get("charts") or [])),
        "row_count": int(df.shape[0]),
        "col_count": int(df.shape[1]),
    }
    analysis["file"] = {"original_filename": file.filename, "stored_path": Path(stored_path).name, "size_bytes": size_bytes}

    log.info(
        "request_id=%s upload_analyzed dataset_id=%s filename=%s rows=%s cols=%s charts=%s ms=%s",
        request_id_var.get() or "-",
        dataset_id,
        file.filename,
        df.shape[0],
        df.shape[1],
        len(analysis.get("charts") or []),
        analysis_time_ms,
    )

    row = Dataset(
        id=dataset_id,
        share_id=share_id,
        user_id=int(user.id),
        original_filename=file.filename,
        stored_path=stored_path,
        status="ready",
        analysis_json=json.dumps(analysis),
    )
    db.add(row)
    db.commit()

    return DatasetCreateResponse(dataset_id=dataset_id, share_id=share_id, status="ready", analysis=analysis)


@app.get("/api/datasets/{dataset_id}", response_model=DatasetGetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id and int(row.user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    analysis = json.loads(row.analysis_json or "{}") if row.analysis_json else {}
    if str(row.status) != "ready":
        analysis = {"status": str(row.status), "job": get_latest_job(db, dataset_id)}
    return DatasetGetResponse(dataset_id=row.id, share_id=row.share_id, status=str(row.status), error=(row.error or None), analysis=analysis)


@app.get("/api/datasets", response_model=DatasetListResponse)
def list_datasets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Dataset).filter(Dataset.user_id == int(user.id)).order_by(Dataset.created_at.desc()).limit(100).all()
    items: list[DatasetListItem] = []
    for r in rows:
        try:
            analysis = json.loads(r.analysis_json or "{}")
            shape = (analysis.get("profile") or {}).get("shape") or {}
            n_rows = shape.get("rows")
            n_cols = shape.get("cols")
            overview = (analysis.get("overview") or {}) if isinstance(analysis, dict) else {}
            health = (overview.get("health") or {}) if isinstance(overview, dict) else {}
            executive = (overview.get("executive_brief") or {}) if isinstance(overview, dict) else {}
            insights = analysis.get("insights") or []
        except Exception:
            n_rows = None
            n_cols = None
            overview = {}
            health = {}
            executive = {}
            insights = []
        items.append(
            DatasetListItem(
                dataset_id=r.id,
                share_id=r.share_id,
                original_filename=r.original_filename,
                created_at=r.created_at.isoformat(),
                status=str(r.status) if r.status else None,
                rows=n_rows if isinstance(n_rows, int) else None,
                cols=n_cols if isinstance(n_cols, int) else None,
                primary_metric=str(executive.get("metric")) if executive.get("metric") else None,
                health_score=float(health.get("score")) if isinstance(health.get("score"), (int, float)) else None,
                missing_pct=float(health.get("missing_pct")) if isinstance(health.get("missing_pct"), (int, float)) else None,
                duplicate_rows=int(health.get("duplicate_rows")) if isinstance(health.get("duplicate_rows"), (int, float)) else None,
                insight_count=len(insights) if isinstance(insights, list) else None,
            )
        )
    return DatasetListResponse(items=items)


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id and int(row.user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # delete chats
    db.query(ChatMessage).filter(ChatMessage.dataset_id == dataset_id).delete()

    # delete files (best-effort)
    try:
        get_storage().delete(row.stored_path)
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
def chat(dataset_id: str, req: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id and int(row.user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if str(row.status) != "ready":
        raise HTTPException(status_code=409, detail="Dataset still processing")
    try:
        df = load_dataframe(row.stored_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}") from e

    analysis = json.loads(row.analysis_json) if row.analysis_json else None
    t0 = time.perf_counter()
    ans = answer_question(df, req.question, analysis=analysis)
    ms = int((time.perf_counter() - t0) * 1000)
    log.info("request_id=%s chat dataset_id=%s ms=%s type=%s", request_id_var.get() or "-", dataset_id, ms, ans.get("type"))

    # persist AI metrics (source/model/usage) for observability
    try:
        citations = ans.get("citations") if isinstance(ans, dict) else None
        source = ""
        model = ""
        prompt_version = ""
        usage = {}
        err = ""
        if isinstance(citations, dict):
            source = str(citations.get("source") or "")
            model = str(citations.get("model") or "")
            prompt_version = str(citations.get("prompt_version") or "")
            usage = citations.get("usage") or {}
            err = str(citations.get("openai_error") or "")

        db.add(
            AiEvent(
                dataset_id=dataset_id,
                request_id=request_id_var.get() or "",
                source=source or ("computed_engine" if citations and citations.get("computed") else "heuristic"),
                latency_ms=ms,
                model=model,
                prompt_version=prompt_version,
                usage_json=json.dumps(usage),
                error=err,
            )
        )
        db.commit()
    except Exception:
        db.rollback()

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

@app.get("/api/datasets/{dataset_id}/anomalies/{anomaly_index}/explain")
def explain_anomaly(dataset_id: str, anomaly_index: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id and int(row.user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if str(row.status) != "ready":
        raise HTTPException(status_code=409, detail="Dataset still processing")
    analysis = json.loads(row.analysis_json) if row.analysis_json else None
    if not isinstance(analysis, dict):
        raise HTTPException(status_code=400, detail="No analysis found")
    try:
        df = load_dataframe(row.stored_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}") from e
    try:
        return explain_spike(df, analysis, anomaly_index)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/datasets/{dataset_id}/chat/history", response_model=ChatHistoryResponse)
def chat_history(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id and int(row.user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
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
def report_pdf(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id and int(row.user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if str(row.status) != "ready":
        raise HTTPException(status_code=409, detail="Dataset still processing")
    analysis = json.loads(row.analysis_json)
    pdf_path = render_pdf_report(settings.report_dir, dataset_id, analysis)
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{dataset_id}.pdf")


@app.post("/api/datasets/{dataset_id}/pivot", response_model=PivotResponse)
def pivot(dataset_id: str, req: PivotRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(Dataset, dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id and int(row.user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if str(row.status) != "ready":
        raise HTTPException(status_code=409, detail="Dataset still processing")
    try:
        df = load_dataframe(row.stored_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}") from e
    try:
        out = run_pivot(
            df,
            group_by=req.group_by,
            metric=req.metric,
            agg=req.agg,
            date_col=req.date_col,
            time_grain=req.time_grain,
            top_n=req.top_n,
            filters=req.filters,
            chart_type=req.chart_type,
        )
        return out  # type: ignore[return-value]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e



