from __future__ import annotations

import re
from typing import Any

import pandas as pd


def explain_spike(df: pd.DataFrame, analysis: dict[str, Any], anomaly_index: int) -> dict[str, Any]:
    """
    Given an anomaly index from analysis["anomalies"], explain it by comparing the spike period
    vs the previous period for the same time grain.

    Returns:
      { text, table, chart, citations }
    """
    anomalies = (analysis.get("anomalies") or []) if isinstance(analysis, dict) else []
    if not isinstance(anomalies, list) or anomaly_index < 0 or anomaly_index >= len(anomalies):
        raise ValueError("Invalid anomaly index")
    a = anomalies[anomaly_index]
    if not isinstance(a, dict) or a.get("type") != "spike":
        raise ValueError("Selected anomaly is not a spike")

    x_col = str(a.get("x_col"))
    y_col = str(a.get("y_col"))
    x_val = a.get("x")
    grain = str(a.get("time_grain") or "day")

    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError("Columns for anomaly not found in dataset")

    dx = pd.to_datetime(df[x_col], errors="coerce", infer_datetime_format=True)
    dy = pd.to_numeric(df[y_col], errors="coerce")
    base = pd.DataFrame({"x": dx, "y": dy})
    base = base.dropna(subset=["x", "y"])

    # Bucket timestamp for comparing periods
    spike_ts = pd.Timestamp(x_val) if x_val else None
    if spike_ts is None or pd.isna(spike_ts):
        raise ValueError("Invalid spike timestamp")

    if grain == "month":
        bucket = base["x"].dt.to_period("M").dt.to_timestamp()
        spike_bucket = spike_ts.to_period("M").to_timestamp()
        prev_bucket = (spike_ts - pd.offsets.MonthBegin(1)).to_period("M").to_timestamp()
    elif grain == "week":
        bucket = base["x"].dt.to_period("W").dt.start_time
        spike_bucket = spike_ts.to_period("W").start_time
        prev_bucket = (spike_ts - pd.Timedelta(days=7)).to_period("W").start_time
    else:
        bucket = base["x"].dt.floor("D")
        spike_bucket = spike_ts.floor("D")
        prev_bucket = (spike_ts - pd.Timedelta(days=1)).floor("D")

    base = base.assign(_bucket=bucket)
    spike_df = base[base["_bucket"] == spike_bucket]
    prev_df = base[base["_bucket"] == prev_bucket]

    if spike_df.empty:
        raise ValueError("No rows found in spike period")

    # Pick up to 2 good categorical dimensions for attribution
    types = (analysis.get("types") or {}) if isinstance(analysis, dict) else {}
    cat_cols = [c for c, t in types.items() if t == "categorical"]
    dims = _pick_dims(df, cat_cols, limit=2)

    attribution_rows: list[dict[str, Any]] = []
    if dims:
        dim = dims[0]
        d_spike = df.loc[spike_df.index, [dim, y_col]].copy()
        d_prev = df.loc[prev_df.index, [dim, y_col]].copy() if not prev_df.empty else df.loc[[], [dim, y_col]].copy()
        d_spike[y_col] = pd.to_numeric(d_spike[y_col], errors="coerce")
        d_prev[y_col] = pd.to_numeric(d_prev[y_col], errors="coerce")
        d_spike = d_spike.dropna(subset=[dim, y_col])
        d_prev = d_prev.dropna(subset=[dim, y_col])

        g_spike = d_spike.groupby(dim, dropna=True)[y_col].sum()
        g_prev = d_prev.groupby(dim, dropna=True)[y_col].sum() if not d_prev.empty else pd.Series(dtype=float)
        keys = set(map(str, g_spike.index.tolist())) | set(map(str, g_prev.index.tolist()))

        rows = []
        for k in keys:
            s = float(g_spike.get(k, 0.0))
            p = float(g_prev.get(k, 0.0))
            rows.append({"category": str(k), "spike_sum": s, "prev_sum": p, "delta": s - p})
        rows.sort(key=lambda r: abs(float(r["delta"])), reverse=True)
        attribution_rows = rows[:12]

    spike_sum = float(spike_df["y"].sum())
    prev_sum = float(prev_df["y"].sum()) if not prev_df.empty else 0.0
    delta = spike_sum - prev_sum

    # Build a small chart for spike vs previous
    chart = {
        "type": "bar",
        "title": f"Spike period vs previous ({grain})",
        "x": "period",
        "y": y_col,
        "data": [
            {"x": f"prev {prev_bucket.date().isoformat()}", "y": prev_sum},
            {"x": f"spike {spike_bucket.date().isoformat()}", "y": spike_sum},
        ],
        "section": "Recommended",
        "reason": "Compares the detected spike bucket against the previous bucket.",
    }

    text = f"Spike explanation for {y_col}: {spike_sum:,.4g} vs {prev_sum:,.4g} (Δ {delta:,.4g}) at {spike_bucket.date().isoformat()} ({grain})."
    if attribution_rows:
        text += f" Biggest contributors by {dims[0]} are shown below."

    citations = {
        "computed": True,
        "question": "explain spike",
        "anomaly_index": anomaly_index,
        "columns_used": [x_col, y_col, *dims],
        "operations": [
            {"op": "time_bucket", "col": x_col, "grain": grain, "spike_bucket": str(spike_bucket), "prev_bucket": str(prev_bucket)},
            {"op": "sum", "col": y_col, "scope": "bucket"},
            *([{"op": "groupby", "by": dims[0], "agg": "sum", "col": y_col}] if attribution_rows else []),
        ],
        "rows_scanned": int(df.shape[0]),
        "rows_in_spike_bucket": int(spike_df.shape[0]),
        "rows_in_prev_bucket": int(prev_df.shape[0]),
    }

    table = None
    if attribution_rows:
        table = {"columns": ["category", "spike_sum", "prev_sum", "delta"], "rows": attribution_rows}

    return {"type": "table" if table else "chart", "text": text, "table": table, "chart": chart, "citations": citations}


def _pick_dims(df: pd.DataFrame, cat_cols: list[str], limit: int) -> list[str]:
    dims = []
    for c in cat_cols:
        name = str(c).lower()
        if re.search(r"(id|uuid|guid|email|phone|mobile|address|lat|lon|zip|postal)", name):
            continue
        uniq = int(df[c].dropna().nunique())
        if 2 <= uniq <= 50:
            dims.append(c)
        if len(dims) >= limit:
            break
    return dims

