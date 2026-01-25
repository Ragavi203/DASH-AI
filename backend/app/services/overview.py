from __future__ import annotations

from typing import Any

import pandas as pd


def build_overview(df: pd.DataFrame, analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Produces a compact, highly useful overview payload:
    - KPI cards (date range, primary metric total/avg, missing rate, duplicates)
    - Suggested questions tailored to columns
    - Quick highlights derived from analysis
    """
    profile = (analysis.get("profile") or {}) if isinstance(analysis, dict) else {}
    types = (analysis.get("types") or {}) if isinstance(analysis, dict) else {}
    columns = list(df.columns)

    shape = (profile.get("shape") or {}) if isinstance(profile, dict) else {}
    n_rows = int(shape.get("rows") or df.shape[0])

    quality = (profile.get("quality") or {}) if isinstance(profile, dict) else {}
    dup = int(quality.get("duplicate_rows") or 0)
    missing_by = (profile.get("missing_by_col") or {}) if isinstance(profile, dict) else {}
    total_missing = int(sum(int(v or 0) for v in missing_by.values())) if isinstance(missing_by, dict) else 0
    total_cells = max(n_rows * max(int(shape.get("cols") or df.shape[1]), 1), 1)
    missing_rate = total_missing / total_cells

    dt_cols = [c for c, t in types.items() if t == "datetime"]
    num_cols = [c for c, t in types.items() if t == "numeric"]
    cat_cols = [c for c, t in types.items() if t == "categorical"]

    # Date range
    date_range = None
    if dt_cols and isinstance(profile.get("columns"), dict):
        best_dt = dt_cols[0]
        info = (profile["columns"].get(best_dt) or {}) if isinstance(profile["columns"], dict) else {}
        if info.get("min") and info.get("max"):
            date_range = {"column": best_dt, "min": info.get("min"), "max": info.get("max")}

    # Choose a primary metric
    primary_metric = num_cols[0] if num_cols else None
    if num_cols:
        # prefer business-like names
        prefs = ["revenue", "sales", "amount", "total", "price", "profit", "cost", "spend", "qty", "quantity"]
        for p in prefs:
            for c in num_cols:
                if p in str(c).lower():
                    primary_metric = c
                    break
            if primary_metric and p in str(primary_metric).lower():
                break

    metric_total = None
    metric_mean = None
    if primary_metric:
        s = pd.to_numeric(df[primary_metric], errors="coerce").dropna()
        if not s.empty:
            metric_total = float(s.sum())
            metric_mean = float(s.mean())

    # Suggested questions
    qs: list[str] = []
    if primary_metric and cat_cols:
        qs.append(f"top 10 {cat_cols[0]} by {primary_metric}")
    if primary_metric:
        qs.append(f"mean {primary_metric}")
        qs.append(f"sum {primary_metric}")
    if dt_cols and primary_metric:
        qs.append(f"trend of {primary_metric} by month")
    if dt_cols:
        qs.append("rows over time")
    if cat_cols:
        qs.append(f"count by {cat_cols[0]}")

    # Highlights
    highlights: list[dict[str, Any]] = []
    if missing_rate >= 0.05:
        highlights.append({"type": "data_quality", "text": f"{missing_rate*100:.1f}% of cells are missing."})
    if dup > 0:
        highlights.append({"type": "data_quality", "text": f"{dup:,} duplicate rows detected."})
    corr = (profile.get("strong_correlations") or []) if isinstance(profile, dict) else []
    if isinstance(corr, list) and corr:
        c0 = corr[0]
        if c0.get("a") and c0.get("b") and c0.get("corr") is not None:
            highlights.append({"type": "correlation", "text": f"{c0['a']} and {c0['b']} correlate at {float(c0['corr']):.2f}."})

    kpis: list[dict[str, Any]] = [
        {"label": "Rows", "value": n_rows},
        {"label": "Columns", "value": int(shape.get("cols") or df.shape[1])},
        {"label": "Missing %", "value": round(missing_rate * 100.0, 2)},
        {"label": "Duplicates", "value": dup},
    ]
    if date_range:
        kpis.insert(0, {"label": "Date range", "value": f"{date_range['min']} → {date_range['max']}"})
    if primary_metric and metric_total is not None:
        kpis.insert(0, {"label": f"Total {primary_metric}", "value": metric_total})
    if primary_metric and metric_mean is not None:
        kpis.insert(0, {"label": f"Avg {primary_metric}", "value": metric_mean})

    return {
        "kpis": kpis[:8],
        "highlights": highlights[:6],
        "suggested_questions": qs[:8],
        "columns": [str(c) for c in columns[:60]],
    }

