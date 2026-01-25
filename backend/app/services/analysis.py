from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.anomalies import detect_anomalies
from app.services.charts import materialize_chart, suggest_charts
from app.services.insights import generate_insights
from app.services.overview import build_overview
from app.services.profiling import infer_column_types, profile_dataframe


def analyze_dataframe(df: pd.DataFrame, max_preview_rows: int = 50) -> dict[str, Any]:
    types = infer_column_types(df)
    profile = profile_dataframe(df, types)
    chart_specs = suggest_charts(df, types, profile=profile)
    anomalies = detect_anomalies(df, types, profile=profile)
    insights = generate_insights(profile, chart_specs, anomalies)

    preview = df.head(max_preview_rows).fillna("").to_dict(orient="records")
    charts = [materialize_chart(df, spec) for spec in chart_specs]

    analysis = {
        "types": types,
        "profile": profile,
        "chart_specs": chart_specs,
        "charts": charts,
        "anomalies": anomalies,
        "insights": insights,
        "preview": preview,
    }

    analysis["overview"] = build_overview(df, analysis)
    return analysis



