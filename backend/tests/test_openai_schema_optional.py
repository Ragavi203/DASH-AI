from __future__ import annotations

import os

import pytest

from app.services.openai_chat import openai_answer


@pytest.mark.skipif(os.getenv("RUN_OPENAI_EVALS") != "1", reason="Set RUN_OPENAI_EVALS=1 to run OpenAI evals")
def test_openai_returns_json_with_citations():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    ctx = {
        "shape": {"rows": 5, "cols": 3},
        "columns": ["date", "customer", "revenue"],
        "types": {"date": "datetime", "customer": "categorical", "revenue": "numeric"},
        "column_summary": {},
        "strong_correlations": [],
        "anomalies": [],
        "sample_rows": [
            {"date": "2024-01-01", "customer": "A", "revenue": 10},
            {"date": "2024-01-02", "customer": "B", "revenue": 5},
        ],
        "retrieval": {"snippets": [], "selected_columns": [], "score_debug": []},
    }
    ans = openai_answer("What is the total revenue?", ctx)
    assert isinstance(ans, dict)
    assert "type" in ans and "text" in ans
    assert "citations" in ans
    assert ans["citations"].get("model")

