from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.pii_scan import pii_scan


def build_overview(df: pd.DataFrame, analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Produces a compact, highly useful overview payload:
    - KPI cards (date range, primary metric total/avg, missing rate, duplicates)
    - Suggested questions tailored to columns
    - Quick highlights derived from analysis
    - Senior-analyst extras: executive brief (change + drivers) + data dictionary
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
        "privacy": pii_scan(df),
        "executive_brief": _build_executive_brief(df, profile, types),
        "data_dictionary": _build_data_dictionary(df, profile, types),
    }


def _build_executive_brief(df: pd.DataFrame, profile: dict[str, Any], types: dict[str, str]) -> dict[str, Any] | None:
    """
    Analyst-style summary:
    - pick a primary numeric metric + date column
    - compute last vs previous period delta (month/week/day)
    - attribute delta to a best categorical dimension if possible
    """
    dt_cols = [c for c, t in types.items() if t == "datetime"]
    num_cols = [c for c, t in types.items() if t == "numeric"]
    cat_cols = [c for c, t in types.items() if t == "categorical"]
    if not dt_cols or not num_cols:
        return None

    dt_col = str(dt_cols[0])
    metric = _pick_primary_metric(num_cols)
    if not metric:
        return None

    d = df[[dt_col, metric] + ([cat_cols[0]] if cat_cols else [])].copy()
    d[dt_col] = pd.to_datetime(d[dt_col], errors="coerce", infer_datetime_format=True)
    d[metric] = pd.to_numeric(d[metric], errors="coerce")
    d = d.dropna(subset=[dt_col, metric])
    if d.empty:
        return None

    # choose a stable grain based on date span
    col_info = ((profile.get("columns") or {}).get(dt_col) or {}) if isinstance(profile.get("columns"), dict) else {}
    min_dt = col_info.get("min")
    max_dt = col_info.get("max")
    grain = "month"
    try:
        if min_dt and max_dt:
            span_days = (pd.Timestamp(max_dt) - pd.Timestamp(min_dt)).days
            if span_days <= 14:
                grain = "day"
            elif span_days <= 120:
                grain = "week"
    except Exception:
        grain = "month"

    if grain == "day":
        bucket = d[dt_col].dt.floor("D")
    elif grain == "week":
        bucket = d[dt_col].dt.to_period("W").dt.start_time
    else:
        bucket = d[dt_col].dt.to_period("M").dt.to_timestamp()

    g = d.assign(_bucket=bucket).groupby("_bucket")[metric].sum().sort_index()
    if g.shape[0] < 2:
        return None

    # last + previous
    buckets = list(g.index)
    cur_b = buckets[-1]
    prev_b = buckets[-2]
    cur_v = float(g.loc[cur_b])
    prev_v = float(g.loc[prev_b])
    delta = cur_v - prev_v
    pct = (delta / abs(prev_v)) if prev_v not in (0.0, -0.0) else None

    # trend chart (last 12 buckets)
    tail = g.tail(12)
    trend_chart = {
        "type": "line",
        "title": f"{metric} trend ({grain})",
        "x": "x",
        "y": "y",
        "time_grain": grain,
        "data": [{"x": pd.Timestamp(k).date().isoformat(), "y": float(v)} for k, v in tail.items()],
        "section": "Recommended",
        "reason": "Auto-generated executive trend for the primary metric.",
    }

    bullets: list[str] = []
    bullets.append(f"Primary metric: {metric}.")
    bullets.append(
        f"Latest {grain}: {cur_v:,.4g} vs previous {prev_v:,.4g} (Δ {delta:,.4g}"
        + (f", {pct*100:.1f}%." if isinstance(pct, float) else ").")
    )

    drivers = None
    driver_dim = _pick_driver_dimension(profile, cat_cols)
    if driver_dim:
        dd = df[[dt_col, metric, driver_dim]].copy()
        dd[dt_col] = pd.to_datetime(dd[dt_col], errors="coerce", infer_datetime_format=True)
        dd[metric] = pd.to_numeric(dd[metric], errors="coerce")
        dd = dd.dropna(subset=[dt_col, metric, driver_dim])
        if not dd.empty:
            if grain == "day":
                b2 = dd[dt_col].dt.floor("D")
            elif grain == "week":
                b2 = dd[dt_col].dt.to_period("W").dt.start_time
            else:
                b2 = dd[dt_col].dt.to_period("M").dt.to_timestamp()
            dd = dd.assign(_bucket=b2)
            cur = dd[dd["_bucket"] == cur_b].groupby(driver_dim)[metric].sum()
            prev = dd[dd["_bucket"] == prev_b].groupby(driver_dim)[metric].sum()
            keys = set(map(str, cur.index.tolist())) | set(map(str, prev.index.tolist()))
            rows = []
            for k in keys:
                cv = float(cur.get(k, 0.0))
                pv = float(prev.get(k, 0.0))
                rows.append({"segment": str(k), "current": cv, "previous": pv, "delta": cv - pv})
            rows.sort(key=lambda r: abs(float(r["delta"])), reverse=True)
            top = rows[:8]
            drivers = {"dimension": driver_dim, "rows": top}
            if top:
                bullets.append(f"Top drivers by {driver_dim}: {', '.join([str(r['segment']) for r in top[:3]])}.")

    return {
        "metric": metric,
        "date_col": dt_col,
        "grain": grain,
        "current_bucket": str(cur_b),
        "previous_bucket": str(prev_b),
        "current_value": cur_v,
        "previous_value": prev_v,
        "delta": delta,
        "pct_change": pct,
        "bullets": bullets[:6],
        "trend_chart": trend_chart,
        "drivers": drivers,
    }


def _pick_primary_metric(num_cols: list[str]) -> str | None:
    if not num_cols:
        return None
    prefs = ["revenue", "sales", "amount", "total", "price", "profit", "cost", "spend", "qty", "quantity", "score"]
    for p in prefs:
        for c in num_cols:
            if p in str(c).lower():
                return c
    return num_cols[0]


def _pick_driver_dimension(profile: dict[str, Any], cat_cols: list[str]) -> str | None:
    cols_prof = profile.get("columns") or {}
    if not isinstance(cols_prof, dict):
        return cat_cols[0] if cat_cols else None
    # choose low-ish cardinality categorical (avoid IDs)
    best = None
    best_score = -1.0
    for c in cat_cols[:15]:
        info = cols_prof.get(c) or {}
        if not isinstance(info, dict):
            continue
        ur = info.get("unique_ratio")
        uniq = info.get("unique")
        if isinstance(ur, (int, float)) and ur > 0.8:
            continue
        if isinstance(uniq, int) and uniq > 200:
            continue
        score = 0.0
        if isinstance(ur, (int, float)):
            score += float(max(0.0, 0.35 - ur)) * 10.0
        if isinstance(info.get("top_values"), list):
            score += 2.0
        name = str(c).lower()
        if any(k in name for k in ["id", "uuid", "guid", "email", "phone"]):
            score -= 10.0
        if score > best_score:
            best_score = score
            best = c
    return best or (cat_cols[0] if cat_cols else None)


def _build_data_dictionary(df: pd.DataFrame, profile: dict[str, Any], types: dict[str, str]) -> dict[str, Any]:
    cols_prof = (profile.get("columns") or {}) if isinstance(profile, dict) else {}
    missing_by = (profile.get("missing_by_col") or {}) if isinstance(profile, dict) else {}
    n_rows = int((profile.get("shape") or {}).get("rows") or df.shape[0])
    entries: list[dict[str, Any]] = []
    for c in list(df.columns)[:60]:
        info = (cols_prof.get(c) or {}) if isinstance(cols_prof, dict) else {}
        t = str(types.get(c) or info.get("type") or "unknown")
        miss = int(missing_by.get(c, 0) or 0)
        miss_pct = (miss / n_rows) if n_rows else 0.0
        uniq = info.get("unique")
        ur = info.get("unique_ratio")
        top_vals = info.get("top_values") if isinstance(info, dict) else None
        examples = []
        if isinstance(top_vals, list):
            for tv in top_vals[:4]:
                if isinstance(tv, dict) and tv.get("value") is not None:
                    examples.append(str(tv["value"])[:40])
        notes = []
        name = str(c).lower()
        if miss_pct >= 0.3:
            notes.append("high missing")
        if t in {"categorical", "text"} and isinstance(ur, (int, float)) and float(ur) >= 0.9:
            notes.append("id-like (very high uniqueness)")
        if any(k in name for k in ["id", "uuid", "guid"]):
            notes.append("identifier column")
        if t == "numeric" and isinstance(info, dict) and info.get("std") == 0:
            notes.append("constant")
        entries.append(
            {
                "column": str(c),
                "type": t,
                "missing_pct": round(miss_pct * 100.0, 2),
                "unique": int(uniq) if isinstance(uniq, int) else None,
                "unique_ratio": round(float(ur), 4) if isinstance(ur, (int, float)) else None,
                "examples": examples,
                "notes": notes[:3],
            }
        )
    return {"columns": entries}

