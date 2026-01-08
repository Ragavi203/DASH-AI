from __future__ import annotations

from typing import Any


def generate_insights(profile: dict[str, Any], chart_specs: list[dict[str, Any]], anomalies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shape = profile.get("shape", {})
    rows, cols = shape.get("rows"), shape.get("cols")
    insights: list[dict[str, Any]] = []

    if rows is not None and cols is not None:
        insights.append({"type": "summary", "text": f"Loaded {rows:,} rows across {cols} columns."})

    missing = profile.get("missing_by_col", {}) or {}
    top_missing = sorted(missing.items(), key=lambda kv: kv[1], reverse=True)[:5]
    if top_missing and top_missing[0][1] > 0:
        insights.append(
            {
                "type": "data_quality",
                "text": "Missing values detected. Top columns: "
                + ", ".join([f"{c} ({n:,})" for c, n in top_missing if n > 0]),
            }
        )

    quality = profile.get("quality", {}) or {}
    dup = int(quality.get("duplicate_rows") or 0)
    if dup > 0:
        insights.append({"type": "data_quality", "text": f"Found {dup:,} duplicate rows. Consider de-duplicating before reporting."})
    const_cols = quality.get("constant_columns") or []
    if const_cols:
        insights.append(
            {
                "type": "data_quality",
                "text": "Constant columns (no variation): " + ", ".join([str(c) for c in const_cols[:8]]),
            }
        )
    high_missing = quality.get("high_missing_columns") or []
    if high_missing:
        insights.append(
            {
                "type": "data_quality",
                "text": "High-missing columns (≥30% empty): " + ", ".join([str(c) for c in high_missing[:8]]),
            }
        )

    corrs = profile.get("strong_correlations", []) or []
    if corrs:
        c0 = corrs[0]
        insights.append(
            {
                "type": "correlation",
                "text": f"Strong correlation detected: {c0['a']} vs {c0['b']} (corr={c0['corr']:.2f}).",
            }
        )

    if anomalies:
        spikes = [a for a in anomalies if a.get("type") == "spike"]
        outliers = [a for a in anomalies if a.get("type") == "outlier"]
        if spikes:
            s0 = spikes[0]
            tg = s0.get("time_grain")
            grain_txt = f" ({tg})" if tg else ""
            insights.append(
                {
                    "type": "anomaly",
                    "text": f"Anomaly spike in {s0['y_col']} around {s0['x']}{grain_txt}.",
                    "meta": s0,
                }
            )
        elif outliers:
            o0 = outliers[0]
            insights.append({"type": "anomaly", "text": f"Outliers detected in {o0['col']} (outside IQR bounds).", "meta": o0})

    if chart_specs:
        t_counts: dict[str, int] = {}
        for s in chart_specs:
            t = str(s.get("type") or "unknown")
            t_counts[t] = t_counts.get(t, 0) + 1
        parts = []
        if t_counts.get("line"):
            parts.append(f"{t_counts['line']} trend charts")
        if t_counts.get("bar"):
            parts.append(f"{t_counts['bar']} breakdown charts")
        if t_counts.get("hist"):
            parts.append(f"{t_counts['hist']} distributions")
        if t_counts.get("scatter"):
            parts.append(f"{t_counts['scatter']} relationships")
        summary = ", ".join(parts) if parts else f"{len(chart_specs)} charts"
        insights.append({"type": "charts", "text": f"Generated {summary} tailored to this dataset."})

    return insights[:12]



