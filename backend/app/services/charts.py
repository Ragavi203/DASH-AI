from __future__ import annotations

import re
from typing import Any

import pandas as pd


def suggest_charts(
    df: pd.DataFrame,
    types: dict[str, str],
    profile: dict[str, Any] | None = None,
    max_suggestions: int = 14,
) -> list[dict[str, Any]]:
    dt_cols = [c for c, t in types.items() if t == "datetime"]
    num_cols = [c for c, t in types.items() if t == "numeric"]
    cat_cols = [c for c, t in types.items() if t == "categorical"]

    suggestions: list[dict[str, Any]] = []

    n_rows = int(profile.get("shape", {}).get("rows")) if profile else len(df)
    col_profile = (profile or {}).get("columns", {}) or {}

    best_dt = _pick_best_datetime(dt_cols, col_profile)

    cat_candidates = _pick_dim_candidates(cat_cols, col_profile, n_rows, limit=4)
    metrics = _pick_metric_candidates(num_cols, col_profile, n_rows, limit=4)

    primary_metric = metrics[0] if metrics else None
    secondary_metrics = metrics[1:3]

    grain = _infer_time_grain(best_dt, col_profile) if best_dt else None

    # Helper for prettier labels
    def pretty(s: str) -> str:
        return str(s).replace("_", " ").strip()

    # Recommended: row count over time (if time exists)
    if best_dt:
        x = best_dt
        suggestions.append(
            {
                "id": f"line:{x}:__count__",
                "type": "line",
                "x": x,
                "y": "__count__",
                "agg": "count",
                "time_grain": grain,
                "title": "Rows over time",
                "section": "Recommended",
                "reason": f"Shows activity over time using {pretty(x)}.",
            }
        )

    # Recommended: primary metric over time (if time+metric exist)
    if best_dt and primary_metric:
        x = best_dt
        for y in [primary_metric, *secondary_metrics]:
            agg = _metric_agg_for(y, col_profile)
            suggestions.append(
                {
                    "id": f"line:{x}:{y}",
                    "type": "line",
                    "x": x,
                    "y": y,
                    "agg": agg,
                    "time_grain": grain,
                    "title": f"{pretty(y)} over time ({agg})",
                    "section": "Trends",
                    "reason": f"{agg.upper()}({pretty(y)}) grouped by {pretty(x)} ({grain}).",
                }
            )

    # Breakdowns: counts by key dimensions
    for c in cat_candidates[:3]:
        suggestions.append(
            {
                "id": f"bar:{c}:__count__",
                "type": "bar",
                "x": c,
                "y": "__count__",
                "agg": "count",
                "limit": 12,
                "title": f"Count by {pretty(c)}",
                "section": "Breakdowns",
                "reason": f"Most common {pretty(c)} values (top 12).",
            }
        )

    # Breakdowns: metric by key dimensions
    if primary_metric and cat_candidates:
        for c in cat_candidates[:2]:
            agg = _metric_agg_for(primary_metric, col_profile)
            suggestions.append(
                {
                    "id": f"bar:{c}:{primary_metric}:{agg}",
                    "type": "bar",
                    "x": c,
                    "y": primary_metric,
                    "agg": agg,
                    "limit": 12,
                    "title": f"{agg.title()} {pretty(primary_metric)} by {pretty(c)}",
                    "section": "Breakdowns",
                    "reason": f"{agg.upper()}({pretty(primary_metric)}) grouped by {pretty(c)} (top 12).",
                }
            )

    # Tables: top combinations (if 2+ good categoricals)
    if len(cat_candidates) >= 2:
        a, b = cat_candidates[0], cat_candidates[1]
        suggestions.append(
            {
                "id": f"table:combo:{a}:{b}",
                "type": "table_combo",
                "a": a,
                "b": b,
                "limit": 20,
                "title": f"Top combinations: {pretty(a)} × {pretty(b)}",
                "section": "Recommended",
                "reason": "Quickly reveals the most frequent category pairs.",
            }
        )

    # Distributions: key numeric columns
    for y in metrics[:3]:
        suggestions.append(
            {
                "id": f"hist:{y}",
                "type": "hist",
                "x": y,
                "bins": 20,
                "title": f"Distribution of {pretty(y)}",
                "section": "Distributions",
                "reason": f"Shows spread and outliers in {pretty(y)}.",
            }
        )

    # Relationships: strongest correlations (up to 2)
    pairs = _pick_scatter_pairs(num_cols, profile, limit=2)
    for a, b in pairs:
        suggestions.append(
            {
                "id": f"scatter:{a}:{b}",
                "type": "scatter",
                "x": a,
                "y": b,
                "title": f"{pretty(b)} vs {pretty(a)}",
                "section": "Relationships",
                "reason": "Strongest correlation detected in numeric columns.",
            }
        )

    # If no datetime: still recommend a strong breakdown
    if not best_dt and primary_metric and cat_candidates:
        c = cat_candidates[0]
        agg = _metric_agg_for(primary_metric, col_profile)
        suggestions.append(
            {
                "id": f"bar:{c}:{primary_metric}:{agg}:top",
                "type": "bar",
                "x": c,
                "y": primary_metric,
                "agg": agg,
                "limit": 12,
                "title": f"Top {pretty(c)} by {agg} {pretty(primary_metric)}",
                "section": "Recommended",
                "reason": "Best single view when there is no time column.",
            }
        )

    # If nothing, at least show a row count table card
    if not suggestions:
        suggestions.append({"id": "table:preview", "type": "table", "title": "Data preview"})

    # de-dupe, cap
    seen = set()
    out: list[dict[str, Any]] = []
    for s in suggestions:
        if s["id"] in seen:
            continue
        seen.add(s["id"])
        out.append(s)
        if len(out) >= max_suggestions:
            break
    return out


def materialize_chart(df: pd.DataFrame, spec: dict[str, Any], max_points: int = 5000) -> dict[str, Any]:
    """
    Returns a chart payload the frontend can render.
    This is intentionally simple JSON (Recharts-friendly).
    """
    ctype = spec.get("type")
    section = spec.get("section")
    reason = spec.get("reason")
    if ctype == "line":
        x, y = spec["x"], spec["y"]
        agg = spec.get("agg", "sum")
        grain = spec.get("time_grain")  # day|week|month|None
        cols = [x] if y == "__count__" else [x, y]
        d = df[cols].copy()
        d[x] = pd.to_datetime(d[x], errors="coerce", infer_datetime_format=True)
        if y != "__count__":
            d[y] = pd.to_numeric(d[y], errors="coerce")
            d = d.dropna(subset=[x, y]).sort_values(x)
        else:
            d = d.dropna(subset=[x]).sort_values(x)
        if grain:
            d = _aggregate_time(d, x, y, grain=grain, agg=agg)
        if len(d) > max_points:
            d = d.iloc[:: max(1, len(d) // max_points)]
        data = [{"x": _safe(vx), "y": float(vy)} for vx, vy in zip(d[x], d[y], strict=False)]
        return {
            "type": "line",
            "title": spec.get("title"),
            "x": x,
            "y": y,
            "data": data,
            "time_grain": grain,
            "agg": agg,
            "section": section,
            "reason": reason,
        }

    if ctype == "bar":
        x, y = spec["x"], spec["y"]
        agg = spec.get("agg", "sum")
        limit = int(spec.get("limit", 15))
        if y == "__count__" or agg == "count":
            d = df[[x]].copy().dropna(subset=[x])
            g = d.groupby(x, dropna=True).size()
        else:
            d = df[[x, y]].copy()
            d[y] = pd.to_numeric(d[y], errors="coerce")
            d = d.dropna(subset=[x, y])
            if agg == "mean":
                g = d.groupby(x, dropna=True)[y].mean()
            else:
                g = d.groupby(x, dropna=True)[y].sum()
        g = g.sort_values(ascending=False).head(limit)
        data = [{"x": str(ix), "y": float(v)} for ix, v in g.items()]
        return {"type": "bar", "title": spec.get("title"), "x": x, "y": y, "data": data, "section": section, "reason": reason}

    if ctype == "hist":
        x = spec["x"]
        bins = int(spec.get("bins", 20))
        s = pd.to_numeric(df[x], errors="coerce").dropna()
        if s.empty:
            return {"type": "hist", "title": spec.get("title"), "x": x, "bins": bins, "data": [], "section": section, "reason": reason}
        counts, edges = pd.cut(s, bins=bins, retbins=True, include_lowest=True).value_counts().sort_index(), None
        # derive edges from categories
        data = [{"bin": str(cat), "count": int(cnt)} for cat, cnt in counts.items()]
        return {"type": "hist", "title": spec.get("title"), "x": x, "bins": bins, "data": data, "section": section, "reason": reason}

    if ctype == "scatter":
        x, y = spec["x"], spec["y"]
        d = df[[x, y]].copy()
        d[x] = pd.to_numeric(d[x], errors="coerce")
        d[y] = pd.to_numeric(d[y], errors="coerce")
        d = d.dropna(subset=[x, y])
        if len(d) > max_points:
            d = d.sample(n=max_points, random_state=7)
        data = [{"x": float(vx), "y": float(vy)} for vx, vy in zip(d[x], d[y], strict=False)]
        return {"type": "scatter", "title": spec.get("title"), "x": x, "y": y, "data": data, "section": section, "reason": reason}

    if ctype == "table":
        return {"type": "table", "title": spec.get("title"), "data": df.head(50).to_dict(orient="records"), "section": section, "reason": reason}

    if ctype == "table_combo":
        a, b = spec["a"], spec["b"]
        limit = int(spec.get("limit", 20))
        d = df[[a, b]].copy().dropna(subset=[a, b])
        g = d.groupby([a, b]).size().sort_values(ascending=False).head(limit)
        rows = [{"a": str(ix[0]), "b": str(ix[1]), "count": int(v)} for ix, v in g.items()]
        return {
            "type": "table",
            "title": spec.get("title"),
            "data": rows,
            "section": section,
            "reason": reason,
        }

    return {"type": "unknown", "title": spec.get("title"), "raw": spec}


def _safe(v: Any) -> Any:
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


def _pick_best_datetime(dt_cols: list[str], col_profile: dict[str, Any]) -> str | None:
    if not dt_cols:
        return None
    ranked = []
    for c in dt_cols:
        info = col_profile.get(c, {}) or {}
        count = info.get("count") or 0
        ranked.append((int(count), c))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None


def _pick_best_numeric(num_cols: list[str], col_profile: dict[str, Any], n_rows: int) -> str | None:
    best = None
    best_score = -1.0
    for c in num_cols:
        info = col_profile.get(c, {}) or {}
        cnt = float(info.get("count") or 0)
        std = float(info.get("std") or 0) if info.get("std") is not None else 0.0
        coverage = cnt / max(float(n_rows), 1.0)
        score = std * (0.25 + coverage)
        if score > best_score:
            best_score = score
            best = c
    return best


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


def _pick_best_categorical(cat_cols: list[str], col_profile: dict[str, Any], n_rows: int) -> str | None:
    best = None
    best_score = -1.0
    for c in cat_cols:
        info = col_profile.get(c, {}) or {}
        uniq = float(info.get("unique") or 0)
        # prefer “bar chart-able”: not too low, not too high
        if uniq < 2 or uniq > 50:
            continue
        score = -abs(uniq - 12)  # best around 12 categories
        if score > best_score:
            best_score = score
            best = c
    return best or (cat_cols[0] if cat_cols else None)


def _pick_scatter_pair(num_cols: list[str], profile: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if profile:
        corrs = (profile.get("strong_correlations") or [])[:1]
        if corrs:
            return corrs[0].get("a"), corrs[0].get("b")
    if len(num_cols) >= 2:
        return num_cols[0], num_cols[1]
    return None, None


def _infer_time_grain(dt_col: str, col_profile: dict[str, Any]) -> str | None:
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


def _aggregate_time(d: pd.DataFrame, x: str, y: str, grain: str, agg: str) -> pd.DataFrame:
    dd = d.copy()
    if grain == "month":
        key = dd[x].dt.to_period("M").dt.to_timestamp()
    elif grain == "week":
        key = dd[x].dt.to_period("W").dt.start_time
    else:
        key = dd[x].dt.floor("D")
    dd = dd.assign(_k=key)
    if y == "__count__" or agg == "count":
        g = dd.groupby("_k").size()
        out = g.reset_index().rename(columns={"_k": x, 0: y}).sort_values(x)
    else:
        if agg == "mean":
            g = dd.groupby("_k")[y].mean()
        else:
            g = dd.groupby("_k")[y].sum()
        out = g.reset_index().rename(columns={"_k": x, y: y}).sort_values(x)
    return out


def _pick_top_categoricals(cat_cols: list[str], col_profile: dict[str, Any], n_rows: int, limit: int) -> list[str]:
    scored = []
    for c in cat_cols:
        info = col_profile.get(c, {}) or {}
        uniq = float(info.get("unique") or 0)
        if uniq < 2:
            continue
        # prefer low/medium cardinality for readable bars
        if uniq > 80:
            continue
        score = -abs(uniq - 10)
        scored.append((score, c))
    scored.sort(reverse=True)
    if scored:
        return [c for _, c in scored[:limit]]
    return cat_cols[:limit]


def _metric_agg_for(col: str, col_profile: dict[str, Any]) -> str:
    """
    Decide whether a numeric column should be summed or averaged when grouped.
    - sum: money/amount/revenue-like measures
    - mean: ratios, ages, scores, rates, already-averaged metrics
    """
    name = str(col).lower()
    if re.search(r"(revenue|sales|amount|total|price|cost|spend|profit|qty|quantity|count)", name):
        return "sum"
    if re.search(r"(rate|ratio|percent|pct|avg|average|mean|age|score)", name):
        return "mean"
    info = col_profile.get(col, {}) or {}
    skew = info.get("skew")
    # highly skewed distributions are often "amount-like" → sum
    if skew is not None:
        try:
            if abs(float(skew)) > 2.0:
                return "sum"
        except Exception:
            pass
    return "mean"


def _pick_scatter_pairs(num_cols: list[str], profile: dict[str, Any] | None, limit: int) -> list[tuple[str, str]]:
    if profile:
        corrs = profile.get("strong_correlations") or []
        pairs = []
        for c in corrs:
            a, b = c.get("a"), c.get("b")
            if a and b:
                pairs.append((a, b))
            if len(pairs) >= limit:
                break
        if pairs:
            return pairs
    if len(num_cols) >= 2:
        return [(num_cols[0], num_cols[1])]
    return []


def _pick_dim_candidates(cat_cols: list[str], col_profile: dict[str, Any], n_rows: int, limit: int) -> list[str]:
    """
    Pick categorical dimensions that are *human readable*:
    - exclude IDs/emails/phones/uuids
    - exclude extremely high-cardinality columns
    - prefer mid-cardinality columns
    """
    out: list[tuple[float, str]] = []
    for c in cat_cols:
        name = str(c).lower()
        if re.search(r"(id|uuid|guid|email|phone|mobile|address|lat|lon|zip|postal)", name):
            continue
        info = col_profile.get(c, {}) or {}
        uniq = float(info.get("unique") or 0)
        # unique_ratio exists for text/categorical in profiling; if missing, approximate
        ur = info.get("unique_ratio")
        if ur is None:
            try:
                ur = uniq / max(float(n_rows), 1.0)
            except Exception:
                ur = None
        if uniq < 2:
            continue
        if uniq > 60:
            continue
        if ur is not None and float(ur) > 0.35:
            # likely an identifier-like column
            continue
        score = -abs(uniq - 10)
        out.append((score, c))
    out.sort(reverse=True)
    return [c for _, c in out[:limit]]


def _pick_metric_candidates(num_cols: list[str], col_profile: dict[str, Any], n_rows: int, limit: int) -> list[str]:
    """
    Pick numeric measures that are informative:
    - high coverage
    - high variation
    - prefer business-like measures by name (revenue/amount/etc.)
    """
    scored: list[tuple[float, str]] = []
    for c in num_cols:
        info = col_profile.get(c, {}) or {}
        cnt = float(info.get("count") or 0)
        std = float(info.get("std") or 0) if info.get("std") is not None else 0.0
        coverage = cnt / max(float(n_rows), 1.0)
        if coverage < 0.4:
            continue
        base = std * (0.25 + coverage)
        name = str(c).lower()
        if re.search(r"(revenue|sales|amount|total|price|cost|spend|profit|gmv|qty|quantity)", name):
            base *= 1.35
        if re.search(r"(index|rank|score)", name):
            base *= 1.05
        scored.append((base, c))
    scored.sort(reverse=True)
    # fallback if everything filtered
    if not scored:
        return _pick_top_numeric(num_cols, col_profile, n_rows, limit=limit)
    return [c for _, c in scored[:limit]]



