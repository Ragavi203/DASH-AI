from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from app.services.anomalies import detect_anomalies
from app.services.openai_chat import openai_answer
from app.services.profiling import infer_column_types
from app.services.query_engine import try_compute_answer


def answer_question(df: pd.DataFrame, question: str, analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    q = question.strip()
    ql = q.lower()
    types = infer_column_types(df)

    # Prefer deterministic computed answers with citations
    computed = try_compute_answer(df, q, types, analysis)
    if computed and isinstance(computed.answer, dict):
        return computed.answer

    # If OpenAI is configured, prefer LLM-backed answers (with fallback)
    try:
        ctx = build_dataset_context(df, types, analysis)
        llm = openai_answer(q, ctx)
        # If model returns an empty text, fall back
        if isinstance(llm, dict) and str(llm.get("text") or "").strip():
            return llm
    except Exception:
        pass

    # "top N customers by revenue"
    m = re.search(r"top\s+(\d+)\s+(\w[\w\s\-]*)\s+by\s+(\w[\w\s\-]*)", ql)
    if m:
        n = int(m.group(1))
        dim = _best_matching_col(df, m.group(2))
        metric = _best_matching_col(df, m.group(3))
        if dim and metric:
            d = df[[dim, metric]].copy()
            d[metric] = pd.to_numeric(d[metric], errors="coerce")
            d = d.dropna(subset=[dim, metric])
            g = d.groupby(dim, dropna=True)[metric].sum().sort_values(ascending=False).head(n)
            rows = [{"name": str(k), "value": float(v)} for k, v in g.items()]
            return {
                "type": "table",
                "text": f"Top {n} {dim} by total {metric}.",
                "table": {"columns": [dim, metric], "rows": rows},
            }

    # "average/mean X", "sum X", "max X", "min X"
    m = re.search(r"\b(average|mean|sum|max|min)\b\s+(.+)", ql)
    if m:
        op = m.group(1)
        col = _best_matching_col(df, m.group(2))
        if col:
            s = pd.to_numeric(df[col], errors="coerce")
            val = None
            if op in {"average", "mean"}:
                val = s.mean()
            elif op == "sum":
                val = s.sum()
            elif op == "max":
                val = s.max()
            elif op == "min":
                val = s.min()
            if val is not None and not pd.isna(val):
                return {"type": "text", "text": f"{op.title()} of {col}: {float(val):,.4g}"}

    # "why did X spike in March" / "spike"
    if "spike" in ql or "anomal" in ql or "outlier" in ql:
        anomalies = detect_anomalies(df, types)
        if not anomalies:
            return {"type": "text", "text": "I didn’t detect strong anomalies with the default rules. Try asking about a specific column."}
        a0 = anomalies[0]
        if a0.get("type") == "spike":
            return {
                "type": "text",
                "text": f"Biggest spike detected in {a0['y_col']} around {a0['x']} (score≈{a0['score']:.2f}). "
                "Common causes: one-off large transactions, reporting changes, or missing/duplicated rows around that date.",
            }
        return {"type": "text", "text": f"Outliers detected in {a0.get('col')} beyond IQR bounds."}

    # "show preview"
    if "preview" in ql or "show rows" in ql:
        rows = df.head(25).fillna("").to_dict(orient="records")
        return {"type": "table", "text": "Here are the first 25 rows.", "table": {"rows": rows}}

    # fallback
    cols = ", ".join(map(str, df.columns[:25]))
    return {
        "type": "text",
        "text": "I can answer questions like:\n"
        "- 'top 10 customers by revenue'\n"
        "- 'average order_value'\n"
        "- 'what caused the spike in March?'\n\n"
        f"Try referencing column names. I see: {cols}",
    }


def build_dataset_context(df: pd.DataFrame, types: dict[str, str], analysis: dict[str, Any] | None) -> dict[str, Any]:
    """
    Keep context compact and safe to send:
    - schema + inferred types
    - profiling stats / top values (from stored analysis if present)
    - correlations + anomalies (from stored analysis if present)
    - small sample rows
    """
    shape = {"rows": int(df.shape[0]), "cols": int(df.shape[1])}
    cols = [str(c) for c in df.columns.tolist()]

    profile = (analysis or {}).get("profile") if isinstance(analysis, dict) else None
    corrs = (profile or {}).get("strong_correlations") if isinstance(profile, dict) else None
    anomalies = (analysis or {}).get("anomalies") if isinstance(analysis, dict) else None

    # Keep a small sample; stringify to avoid numpy/pandas types
    sample = df.head(20).fillna("").to_dict(orient="records")
    try:
        sample_json = json.loads(json.dumps(sample, default=str))
    except Exception:
        sample_json = []

    # Keep per-column summary small
    col_summary: dict[str, Any] = {}
    if isinstance(profile, dict):
        cols_prof = profile.get("columns") or {}
        if isinstance(cols_prof, dict):
            for c in cols[:40]:
                info = cols_prof.get(c) or {}
                if not isinstance(info, dict):
                    continue
                # include only a few fields
                keep = {k: info.get(k) for k in ["type", "missing", "count", "mean", "std", "min", "max", "unique", "parse_rate"] if k in info}
                if "top_values" in info:
                    keep["top_values"] = (info.get("top_values") or [])[:6]
                col_summary[c] = keep

    return {
        "shape": shape,
        "columns": cols[:60],
        "types": types,
        "column_summary": col_summary,
        "strong_correlations": corrs[:8] if isinstance(corrs, list) else [],
        "anomalies": anomalies[:12] if isinstance(anomalies, list) else [],
        "sample_rows": sample_json,
    }


def _best_matching_col(df: pd.DataFrame, raw: str) -> str | None:
    raw = raw.strip().lower()
    # exact-ish match
    for c in df.columns:
        if str(c).lower() == raw:
            return str(c)
    # contains match
    for c in df.columns:
        if raw in str(c).lower():
            return str(c)
    # tokenize match
    toks = [t for t in re.split(r"[^a-z0-9]+", raw) if t]
    best = None
    best_score = 0
    for c in df.columns:
        cl = str(c).lower()
        score = sum(1 for t in toks if t in cl)
        if score > best_score:
            best_score = score
            best = str(c)
    return best if best_score > 0 else None



