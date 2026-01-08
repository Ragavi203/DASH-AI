from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _is_datetime_like(s: pd.Series) -> bool:
    if np.issubdtype(s.dtype, np.datetime64):
        return True
    # try parse a sample
    sample = s.dropna().head(50)
    if sample.empty:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True, utc=False)
    return parsed.notna().mean() > 0.8


def infer_column_types(df: pd.DataFrame) -> dict[str, str]:
    types: dict[str, str] = {}
    for col in df.columns:
        s = df[col]
        if _is_datetime_like(s):
            types[col] = "datetime"
            continue
        if pd.api.types.is_bool_dtype(s):
            types[col] = "boolean"
            continue
        if pd.api.types.is_numeric_dtype(s):
            types[col] = "numeric"
            continue
        # heuristics for low-cardinality strings
        nunique = s.dropna().nunique()
        if nunique <= max(25, int(0.05 * max(len(s), 1))):
            types[col] = "categorical"
        else:
            types[col] = "text"
    return types


def profile_dataframe(df: pd.DataFrame, types: dict[str, str]) -> dict[str, Any]:
    n_rows, n_cols = df.shape
    missing_by_col = {c: int(df[c].isna().sum()) for c in df.columns}
    cols: dict[str, Any] = {}

    for col in df.columns:
        s = df[col]
        t = types.get(col, "unknown")
        col_info: dict[str, Any] = {"type": t, "missing": int(s.isna().sum())}

        if t == "numeric":
            sn = pd.to_numeric(s, errors="coerce")
            non_null = int(sn.count())
            unique = int(sn.dropna().nunique())
            col_info.update(
                {
                    "count": non_null,
                    "mean": _finite(sn.mean()),
                    "std": _finite(sn.std()),
                    "min": _finite(sn.min()),
                    "p25": _finite(sn.quantile(0.25)),
                    "median": _finite(sn.median()),
                    "p75": _finite(sn.quantile(0.75)),
                    "max": _finite(sn.max()),
                    "unique": unique,
                    "zero_pct": _finite((sn == 0).mean()) if non_null else None,
                    "skew": _finite(sn.skew()) if non_null >= 10 else None,
                }
            )
        elif t == "datetime":
            sd = pd.to_datetime(s, errors="coerce", infer_datetime_format=True)
            non_null = int(s.notna().sum())
            parsed = int(sd.count())
            parse_rate = (parsed / non_null) if non_null else 0.0
            col_info.update(
                {
                    "count": parsed,
                    "parse_rate": _finite(parse_rate),
                    "min": _dt(sd.min()),
                    "max": _dt(sd.max()),
                }
            )
        else:
            vc = s.dropna().astype(str).value_counts().head(10)
            col_info["top_values"] = [{"value": k, "count": int(v)} for k, v in vc.items()]
            col_info["unique"] = int(s.dropna().nunique())
            col_info["unique_ratio"] = _finite(col_info["unique"] / max(int(s.notna().sum()), 1))

        cols[col] = col_info

    numeric_cols = [c for c, t in types.items() if t == "numeric"]
    corr: list[dict[str, Any]] = []
    if len(numeric_cols) >= 2:
        num = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        cm = num.corr(numeric_only=True)
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                a, b = numeric_cols[i], numeric_cols[j]
                val = cm.loc[a, b]
                if pd.isna(val):
                    continue
                if abs(float(val)) >= 0.6:
                    corr.append({"a": a, "b": b, "corr": float(val)})
        corr = sorted(corr, key=lambda x: abs(x["corr"]), reverse=True)[:10]

    # dataset-level quality flags
    duplicate_rows = int(df.duplicated().sum())
    constant_cols = []
    for c in df.columns:
        if df[c].dropna().nunique() <= 1:
            constant_cols.append(str(c))

    high_missing = []
    for c in df.columns:
        miss = int(missing_by_col.get(c, 0))
        if n_rows > 0 and (miss / n_rows) >= 0.3:
            high_missing.append(str(c))

    return {
        "shape": {"rows": int(n_rows), "cols": int(n_cols)},
        "missing_by_col": missing_by_col,
        "columns": cols,
        "strong_correlations": corr,
        "quality": {
            "duplicate_rows": duplicate_rows,
            "constant_columns": constant_cols[:25],
            "high_missing_columns": high_missing[:25],
        },
    }


def _finite(x: Any) -> float | None:
    try:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return None
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def _dt(x: Any) -> str | None:
    if x is None or pd.isna(x):
        return None
    try:
        return pd.Timestamp(x).isoformat()
    except Exception:
        return None



