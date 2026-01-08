from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def detect_anomalies(
    df: pd.DataFrame,
    types: dict[str, str],
    profile: dict[str, Any] | None = None,
    max_anomalies: int = 50,
) -> list[dict[str, Any]]:
    """
    Lightweight anomaly detection:
    - time series: z-score on numeric values aggregated by day/week/month (more stable than row-level)
    - numeric columns: IQR-based outliers
    """
    out: list[dict[str, Any]] = []
    dt_cols = [c for c, t in types.items() if t == "datetime"]
    num_cols = [c for c, t in types.items() if t == "numeric"]

    col_profile = (profile or {}).get("columns", {}) if profile else {}
    best_dt = _pick_best_datetime(dt_cols, col_profile)
    top_nums = _pick_top_numeric(num_cols, col_profile, int((profile or {}).get("shape", {}).get("rows") or len(df)), limit=3)
    grain = _infer_time_grain(best_dt, col_profile) if best_dt else None

    if best_dt and top_nums:
        x = best_dt
        dx = pd.to_datetime(df[x], errors="coerce", infer_datetime_format=True)
        for y in top_nums:
            dy = pd.to_numeric(df[y], errors="coerce")
            d = pd.DataFrame({"x": dx, "y": dy}).dropna()
            if d.empty:
                continue
            d = _aggregate_time(d, grain=grain)
            if len(d) < 10:
                continue
            mu = d["y"].mean()
            sig = d["y"].std(ddof=0) + 1e-9
            z = (d["y"] - mu) / sig
            mask = z.abs() >= 3.0
            for row, zz in zip(d[mask].itertuples(index=False), z[mask], strict=False):
                out.append(
                    {
                        "type": "spike",
                        "x_col": x,
                        "y_col": y,
                        "x": pd.Timestamp(row.x).isoformat(),
                        "y": float(row.y),
                        "score": float(abs(zz)),
                        "time_grain": grain,
                    }
                )

    # numeric IQR outliers (non-time)
    for y in num_cols[:6]:
        s = pd.to_numeric(df[y], errors="coerce").dropna()
        if len(s) < 50:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or np.isnan(iqr):
            continue
        lo, hi = q1 - 3.0 * iqr, q3 + 3.0 * iqr
        bad = s[(s < lo) | (s > hi)]
        if bad.empty:
            continue
        for val in bad.head(10).tolist():
            out.append({"type": "outlier", "col": y, "value": float(val), "lo": float(lo), "hi": float(hi)})

    # cap & sort
    out = sorted(out, key=lambda a: float(a.get("score", 0.0)), reverse=True)
    return out[:max_anomalies]


def _pick_best_datetime(dt_cols: list[str], col_profile: dict[str, Any]) -> str | None:
    if not dt_cols:
        return None
    ranked = []
    for c in dt_cols:
        info = col_profile.get(c, {}) or {}
        ranked.append((int(info.get("count") or 0), c))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None


def _pick_top_numeric(num_cols: list[str], col_profile: dict[str, Any], n_rows: int, limit: int) -> list[str]:
    scored = []
    for c in num_cols:
        info = col_profile.get(c, {}) or {}
        cnt = float(info.get("count") or 0)
        std = float(info.get("std") or 0) if info.get("std") is not None else 0.0
        coverage = cnt / max(float(n_rows), 1.0)
        score = std * (0.25 + coverage)
        scored.append((score, c))
    scored.sort(reverse=True)
    return [c for _, c in scored[:limit] if c]


def _infer_time_grain(dt_col: str | None, col_profile: dict[str, Any]) -> str | None:
    if not dt_col:
        return None
    info = col_profile.get(dt_col, {}) or {}
    minv = info.get("min")
    maxv = info.get("max")
    if not minv or not maxv:
        return None
    try:
        d0 = pd.Timestamp(minv)
        d1 = pd.Timestamp(maxv)
        days = abs((d1 - d0).days)
        if days >= 365:
            return "month"
        if days >= 60:
            return "week"
        return "day"
    except Exception:
        return None


def _aggregate_time(d: pd.DataFrame, grain: str | None) -> pd.DataFrame:
    dd = d.copy()
    if grain == "month":
        key = dd["x"].dt.to_period("M").dt.to_timestamp()
    elif grain == "week":
        key = dd["x"].dt.to_period("W").dt.start_time
    else:
        key = dd["x"].dt.floor("D")
    dd = dd.assign(_k=key)
    g = dd.groupby("_k")["y"].sum()
    return g.reset_index().rename(columns={"_k": "x"}).sort_values("x")



