from __future__ import annotations

import pandas as pd

from app.services.query_engine import try_compute_answer
from app.services.profiling import infer_column_types


def _df():
    return pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-01", "2024-02-01", "2024-02-01", "2024-03-01"],
            "customer": ["A", "B", "A", "C", "A"],
            "revenue": [10, 5, 20, 2, 40],
            "age": [20, 30, 20, 40, 20],
        }
    )


def test_top_n_by_metric():
    df = _df()
    types = infer_column_types(df)
    res = try_compute_answer(df, "top 2 customer by revenue", types, analysis=None)
    assert res is not None
    ans = res.answer
    assert ans["type"] == "table"
    assert "citations" in ans
    rows = ans["table"]["rows"]
    assert len(rows) == 2
    assert rows[0]["customer"] == "A"
    assert rows[0]["revenue"] == 70.0


def test_scalar_mean():
    df = _df()
    types = infer_column_types(df)
    res = try_compute_answer(df, "mean age", types, analysis=None)
    assert res is not None
    ans = res.answer
    assert ans["type"] == "text"
    assert "citations" in ans
    assert "MEAN(age)" in ans["text"]


def test_trend_chart_month():
    df = _df()
    types = infer_column_types(df)
    analysis = {"profile": {"columns": {"date": {"min": "2024-01-01", "max": "2024-03-01"}}}}
    res = try_compute_answer(df, "trend of revenue by month", types, analysis=analysis)
    assert res is not None
    ans = res.answer
    assert ans["type"] == "chart"
    assert ans["chart"]["type"] == "line"
    assert ans["chart"]["time_grain"] == "month"
    assert len(ans["chart"]["data"]) >= 2
    assert "citations" in ans


def test_unknown_question_returns_none():
    df = _df()
    types = infer_column_types(df)
    res = try_compute_answer(df, "tell me something poetic", types, analysis=None)
    assert res is None

