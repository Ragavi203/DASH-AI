from __future__ import annotations

import re
from typing import Any


def tokenize(text: str) -> set[str]:
    toks = [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]
    # drop tiny tokens
    return {t for t in toks if len(t) >= 3}


def retrieve_context(question: str, dataset_context: dict[str, Any], top_k: int = 10) -> dict[str, Any]:
    """
    Lightweight lexical retrieval over:
    - column names
    - column summaries
    - anomalies
    - correlations
    Returns: { snippets: [...], selected_columns: [...], score_debug: [...] }
    """
    q = question.strip()
    q_tokens = tokenize(q)
    if not q_tokens:
        return {"snippets": [], "selected_columns": [], "score_debug": []}

    cols = dataset_context.get("columns") or []
    col_summary = dataset_context.get("column_summary") or {}
    anomalies = dataset_context.get("anomalies") or []
    corrs = dataset_context.get("strong_correlations") or []

    scored: list[tuple[float, dict[str, Any]]] = []

    # Column names + summaries
    for c in cols:
        text = str(c)
        info = col_summary.get(c, {})
        if isinstance(info, dict) and info.get("top_values"):
            tv = info.get("top_values") or []
            text += " " + " ".join([str(x.get("value", "")) for x in tv[:4] if isinstance(x, dict)])
        score = _overlap_score(q_tokens, tokenize(text))
        if score > 0:
            scored.append((score, {"kind": "column", "key": c, "text": f"Column: {c} | summary: {info}"}))

    # Anomalies
    for i, a in enumerate(anomalies[:20]):
        text = str(a)
        score = _overlap_score(q_tokens, tokenize(text))
        if score > 0:
            scored.append((score + 0.3, {"kind": "anomaly", "key": f"anomaly[{i}]", "text": f"Anomaly: {a}"}))

    # Correlations
    for i, c in enumerate(corrs[:20]):
        text = str(c)
        score = _overlap_score(q_tokens, tokenize(text))
        if score > 0:
            scored.append((score + 0.2, {"kind": "correlation", "key": f"corr[{i}]", "text": f"Correlation: {c}"}))

    scored.sort(key=lambda x: x[0], reverse=True)
    snippets = [s for _, s in scored[:top_k]]

    selected_cols = []
    for s in snippets:
        if s.get("kind") == "column" and s.get("key"):
            selected_cols.append(str(s["key"]))

    return {
        "snippets": snippets,
        "selected_columns": selected_cols[:10],
        "score_debug": [{"score": float(sc), "key": item.get("key"), "kind": item.get("kind")} for sc, item in scored[:top_k]],
    }


def _overlap_score(q: set[str], doc: set[str]) -> float:
    if not q or not doc:
        return 0.0
    inter = q.intersection(doc)
    return float(len(inter)) / float(len(q) ** 0.5)

