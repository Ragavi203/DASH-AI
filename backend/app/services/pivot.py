from __future__ import annotations

from typing import Any, Literal

import pandas as pd


Agg = Literal["sum", "mean", "count", "min", "max"]
ChartType = Literal["bar", "line", "table"]
Grain = Literal["day", "week", "month"]


def run_pivot(
    df: pd.DataFrame,
    *,
    group_by: list[str],
    metric: str | None,
    agg: Agg,
    date_col: str | None = None,
    time_grain: Grain | None = None,
    top_n: int = 12,
    filters: dict[str, Any] | None = None,
    chart_type: ChartType = "bar",
) -> dict[str, Any]:
    """
    Deterministic pivot/groupby for analyst workflows.
    Returns { type, text, table?, chart?, citations }.
    """
    if not group_by and not date_col:
        raise ValueError("Select at least one group_by or a date column")

    group_by = [g for g in (group_by or []) if g]
    for g in group_by:
        if g not in df.columns:
            raise ValueError(f"Unknown group_by column: {g}")

    if metric is not None and metric not in df.columns:
        raise ValueError(f"Unknown metric column: {metric}")

    d = df.copy()

    # Apply simple equality/inclusion filters
    filters = filters or {}
    for col, val in filters.items():
        if col not in d.columns:
            continue
        if isinstance(val, list):
            d = d[d[col].isin(val)]
        else:
            d = d[d[col] == val]

    # Time bucketing
    bucket_col = None
    if date_col:
        if date_col not in d.columns:
            raise ValueError(f"Unknown date column: {date_col}")
        if not time_grain:
            time_grain = "month"
        ts = pd.to_datetime(d[date_col], errors="coerce", infer_datetime_format=True)
        d = d.assign(_dt=ts).dropna(subset=["_dt"])
        if time_grain == "month":
            bucket = d["_dt"].dt.to_period("M").dt.to_timestamp()
        elif time_grain == "week":
            bucket = d["_dt"].dt.to_period("W").dt.start_time
        else:
            bucket = d["_dt"].dt.floor("D")
        bucket_col = "_bucket"
        d = d.assign(_bucket=bucket)

    # Build group keys
    keys: list[str] = []
    if bucket_col:
        keys.append(bucket_col)
    keys.extend(group_by)

    # Aggregate
    if metric is None or agg == "count":
        g = d.groupby(keys, dropna=True).size().reset_index().rename(columns={0: "y"})
        y_label = "count"
    else:
        d[metric] = pd.to_numeric(d[metric], errors="coerce")
        d = d.dropna(subset=[metric])
        if agg == "sum":
            g = d.groupby(keys, dropna=True)[metric].sum().reset_index().rename(columns={metric: "y"})
        elif agg == "mean":
            g = d.groupby(keys, dropna=True)[metric].mean().reset_index().rename(columns={metric: "y"})
        elif agg == "min":
            g = d.groupby(keys, dropna=True)[metric].min().reset_index().rename(columns={metric: "y"})
        else:
            g = d.groupby(keys, dropna=True)[metric].max().reset_index().rename(columns={metric: "y"})
        y_label = f"{agg}({metric})"

    # Sort + limit (only for categorical pivots; for time-series we keep full series)
    if bucket_col and len(keys) == 1:
        # pure time series: keep sorted by time
        g = g.sort_values(bucket_col)
    else:
        g = g.sort_values("y", ascending=False).head(max(1, int(top_n)))

    # Materialize response
    ops: list[dict[str, Any]] = []
    cols_used = [*keys] + ([metric] if metric else [])
    if filters:
        ops.append({"op": "filter", "filters": filters})
    if bucket_col:
        ops.append({"op": "time_bucket", "col": date_col, "grain": time_grain})
    if keys:
        ops.append({"op": "groupby", "by": keys})
    ops.append({"op": agg if metric else "count", "col": metric or "__rows__"})
    if not (bucket_col and len(keys) == 1):
        ops.append({"op": "sort", "by": "y", "order": "desc"})
        ops.append({"op": "limit", "n": int(top_n)})

    citations = {"computed": True, "source": "pivot", "columns_used": cols_used, "operations": ops, "rows_scanned": int(df.shape[0]), "rows_returned": int(g.shape[0])}

    # Table
    table_rows = []
    for _, row in g.iterrows():
        r = {k: (row[k] if k != bucket_col else pd.Timestamp(row[k]).isoformat()) for k in keys}
        r["y"] = float(row["y"])
        table_rows.append(r)
    table = {"columns": [*keys, "y"], "rows": table_rows}

    # Chart
    if chart_type == "table":
        return {"type": "table", "text": f"Pivot result ({y_label}).", "table": table, "citations": citations}

    # x dimension for chart
    if bucket_col and len(keys) == 1:
        # time series
        data = [{"x": str(r[bucket_col])[:10], "y": float(r["y"])} for r in table_rows]
        chart = {"type": "line", "title": f"{y_label} over time", "x": "x", "y": "y", "data": data, "time_grain": time_grain, "agg": agg}
        return {"type": "chart", "text": f"{y_label} over time.", "chart": chart, "table": table, "citations": citations}

    # categorical bar
    x_key = keys[-1] if keys else "x"
    data = [{"x": str(r.get(x_key, ""))[:40], "y": float(r["y"])} for r in table_rows]
    chart = {"type": "bar", "title": f"{y_label} by {x_key}", "x": "x", "y": "y", "data": data, "agg": agg}
    return {"type": "chart", "text": f"{y_label} by {x_key}.", "chart": chart, "table": table, "citations": citations}

