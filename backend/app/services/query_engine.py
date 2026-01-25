from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd


Agg = Literal["sum", "mean", "count", "min", "max"]
Grain = Literal["day", "week", "month"]


@dataclass
class QueryResult:
    answer: dict[str, Any]
    citations: dict[str, Any]


def try_compute_answer(df: pd.DataFrame, question: str, types: dict[str, str], analysis: dict[str, Any] | None) -> QueryResult | None:
    """
    Deterministic, safe computations for common analytics questions.
    Returns ChatAnswer-like dict + citations describing exactly what was computed.
    """
    q = question.strip()
    ql = q.lower()

    # 1) Top N <dim> by <metric>
    m = re.search(r"\btop\s+(\d+)\s+(.+?)\s+by\s+(.+)$", ql)
    if m:
        n = int(m.group(1))
        dim = _best_matching_col(df, m.group(2))
        metric = _best_matching_col(df, m.group(3))
        if dim and metric:
            agg: Agg = "sum"
            out = _top_n(df, dim=dim, metric=metric, n=n, agg=agg)
            return QueryResult(
                answer={
                    "type": "table",
                    "text": f"Top {n} {dim} by {agg}({metric}).",
                    "table": {"columns": [dim, metric], "rows": out},
                    "citations": _cite(
                        question=q,
                        operations=[{"op": "groupby", "by": dim, "metric": metric, "agg": agg}, {"op": "sort", "by": metric, "order": "desc"}, {"op": "limit", "n": n}],
                        columns_used=[dim, metric],
                        rows_scanned=int(df.shape[0]),
                        rows_returned=len(out),
                    ),
                },
                citations={},
            )

    # 2) Average/mean/sum/min/max of a column
    m = re.search(r"\b(average|mean|sum|max|min)\b\s+(.+)$", ql)
    if m:
        op_raw = m.group(1)
        col = _best_matching_col(df, m.group(2))
        if col:
            op: Agg = "mean" if op_raw in {"average", "mean"} else op_raw  # type: ignore[assignment]
            val = _scalar_agg(df, col=col, agg=op)
            if val is not None:
                return QueryResult(
                    answer={
                        "type": "text",
                        "text": f"{op.upper()}({col}) = {val:,.6g}",
                        "citations": _cite(
                            question=q,
                            operations=[{"op": op, "col": col}],
                            columns_used=[col],
                            rows_scanned=int(df.shape[0]),
                            rows_returned=1,
                        ),
                    },
                    citations={},
                )

    # 3) Trend over time (line chart)
    if ("over time" in ql) or ("trend" in ql) or ("by month" in ql) or ("by week" in ql) or ("by day" in ql):
        dt_col = _pick_datetime(types)
        if dt_col:
            metric = _pick_metric_from_text(df, ql) or _pick_default_metric(df, types, analysis)
            agg: Agg = "count" if metric is None else _metric_agg_guess(metric)
            grain: Grain = _pick_grain(ql, analysis, dt_col)
            if metric is None:
                chart = _time_series(df, dt_col=dt_col, metric="__count__", agg="count", grain=grain)
                return QueryResult(
                    answer={
                        "type": "chart",
                        "text": f"Trend of row count by {grain}.",
                        "chart": chart,
                        "citations": _cite(
                            question=q,
                            operations=[{"op": "time_bucket", "col": dt_col, "grain": grain}, {"op": "count"}],
                            columns_used=[dt_col],
                            rows_scanned=int(df.shape[0]),
                            rows_returned=len(chart.get("data") or []),
                        ),
                    },
                    citations={},
                )

            chart = _time_series(df, dt_col=dt_col, metric=metric, agg=agg, grain=grain)
            return QueryResult(
                answer={
                    "type": "chart",
                    "text": f"{agg.upper()}({metric}) over time by {grain}.",
                    "chart": chart,
                    "citations": _cite(
                        question=q,
                        operations=[{"op": "time_bucket", "col": dt_col, "grain": grain}, {"op": agg, "col": metric}],
                        columns_used=[dt_col, metric],
                        rows_scanned=int(df.shape[0]),
                        rows_returned=len(chart.get("data") or []),
                    ),
                },
                citations={},
            )

    # 4) Count / how many rows
    if "how many" in ql or re.fullmatch(r"\s*count\s*", ql):
        return QueryResult(
            answer={
                "type": "text",
                "text": f"Row count = {int(df.shape[0]):,}",
                "citations": _cite(question=q, operations=[{"op": "count_rows"}], columns_used=[], rows_scanned=int(df.shape[0]), rows_returned=1),
            },
            citations={},
        )

    return None


def _cite(question: str, operations: list[dict[str, Any]], columns_used: list[str], rows_scanned: int, rows_returned: int) -> dict[str, Any]:
    return {
        "computed": True,
        "question": question,
        "columns_used": columns_used,
        "operations": operations,
        "rows_scanned": rows_scanned,
        "rows_returned": rows_returned,
    }


def _best_matching_col(df: pd.DataFrame, raw: str) -> str | None:
    raw = raw.strip().lower()
    if not raw:
        return None
    for c in df.columns:
        if str(c).lower() == raw:
            return str(c)
    for c in df.columns:
        if raw in str(c).lower():
            return str(c)
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


def _pick_datetime(types: dict[str, str]) -> str | None:
    for c, t in types.items():
        if t == "datetime":
            return c
    return None


def _pick_metric_from_text(df: pd.DataFrame, ql: str) -> str | None:
    # Try to find any column name mentioned
    for c in df.columns:
        cl = str(c).lower()
        if cl and cl in ql:
            return str(c)
    # Patterns like "trend of revenue"
    m = re.search(r"(?:trend of|over time of)\s+(.+)$", ql)
    if m:
        return _best_matching_col(df, m.group(1))
    return None


def _pick_default_metric(df: pd.DataFrame, types: dict[str, str], analysis: dict[str, Any] | None) -> str | None:
    # Prefer “most business-like” numeric columns by name, else first numeric
    nums = [c for c, t in types.items() if t == "numeric"]
    if not nums:
        return None
    prefs = ["revenue", "sales", "amount", "total", "price", "profit", "cost", "spend", "qty", "quantity"]
    for p in prefs:
        for c in nums:
            if p in str(c).lower():
                return c
    return nums[0]


def _metric_agg_guess(metric: str) -> Agg:
    name = str(metric).lower()
    if re.search(r"(revenue|sales|amount|total|price|cost|spend|profit|qty|quantity)", name):
        return "sum"
    if re.search(r"(rate|ratio|percent|pct|avg|average|mean|age|score)", name):
        return "mean"
    return "mean"


def _pick_grain(ql: str, analysis: dict[str, Any] | None, dt_col: str) -> Grain:
    if "by month" in ql or "monthly" in ql:
        return "month"
    if "by week" in ql or "weekly" in ql:
        return "week"
    if "by day" in ql or "daily" in ql:
        return "day"
    # fallback from analysis profile range (already computed)
    prof = (analysis or {}).get("profile") if isinstance(analysis, dict) else None
    cols = (prof or {}).get("columns") if isinstance(prof, dict) else None
    info = (cols or {}).get(dt_col) if isinstance(cols, dict) else None
    minv, maxv = (info or {}).get("min"), (info or {}).get("max")
    try:
        if minv and maxv:
            d0 = pd.Timestamp(minv)
            d1 = pd.Timestamp(maxv)
            days = abs((d1 - d0).days)
            if days >= 365:
                return "month"
            if days >= 60:
                return "week"
    except Exception:
        pass
    return "day"


def _top_n(df: pd.DataFrame, dim: str, metric: str, n: int, agg: Agg) -> list[dict[str, Any]]:
    d = df[[dim, metric]].copy()
    d[metric] = pd.to_numeric(d[metric], errors="coerce")
    d = d.dropna(subset=[dim, metric])
    if agg == "mean":
        g = d.groupby(dim, dropna=True)[metric].mean()
    elif agg == "min":
        g = d.groupby(dim, dropna=True)[metric].min()
    elif agg == "max":
        g = d.groupby(dim, dropna=True)[metric].max()
    else:
        g = d.groupby(dim, dropna=True)[metric].sum()
    g = g.sort_values(ascending=False).head(max(1, n))
    return [{dim: str(k), metric: float(v)} for k, v in g.items()]


def _scalar_agg(df: pd.DataFrame, col: str, agg: Agg) -> float | None:
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return None
    if agg == "sum":
        return float(s.sum())
    if agg == "min":
        return float(s.min())
    if agg == "max":
        return float(s.max())
    return float(s.mean())


def _time_series(df: pd.DataFrame, dt_col: str, metric: str, agg: Agg, grain: Grain) -> dict[str, Any]:
    d = df[[dt_col]].copy() if metric == "__count__" else df[[dt_col, metric]].copy()
    d[dt_col] = pd.to_datetime(d[dt_col], errors="coerce", infer_datetime_format=True)
    d = d.dropna(subset=[dt_col])
    if metric != "__count__":
        d[metric] = pd.to_numeric(d[metric], errors="coerce")
        d = d.dropna(subset=[metric])

    if grain == "month":
        key = d[dt_col].dt.to_period("M").dt.to_timestamp()
    elif grain == "week":
        key = d[dt_col].dt.to_period("W").dt.start_time
    else:
        key = d[dt_col].dt.floor("D")
    d = d.assign(_k=key)

    if metric == "__count__" or agg == "count":
        g = d.groupby("_k").size()
        series = g.reset_index().rename(columns={"_k": dt_col, 0: "y"}).sort_values(dt_col)
    else:
        if agg == "mean":
            g = d.groupby("_k")[metric].mean()
        elif agg == "min":
            g = d.groupby("_k")[metric].min()
        elif agg == "max":
            g = d.groupby("_k")[metric].max()
        else:
            g = d.groupby("_k")[metric].sum()
        series = g.reset_index().rename(columns={"_k": dt_col, metric: "y"}).sort_values(dt_col)

    data = [{"x": pd.Timestamp(x).isoformat(), "y": float(y)} for x, y in zip(series[dt_col], series["y"], strict=False)]
    title_metric = "Rows" if metric == "__count__" else metric
    return {"type": "line", "title": f"{title_metric} over time", "x": dt_col, "y": metric, "data": data, "time_grain": grain, "agg": agg}

