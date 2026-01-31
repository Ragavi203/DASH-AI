from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings


def openai_answer(question: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Calls OpenAI Chat Completions with JSON-only output.
    Returns a dict compatible with ChatAnswer schema:
      { "type": "text"|"table"|"chart", "text": "...", "table": {...}?, "chart": {...}? }
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    system = (
        "You are a senior data analyst. Answer questions about a dataset using ONLY the provided dataset context.\n"
        "Return STRICT JSON with keys: type, text, and optionally table or chart.\n"
        "- type must be one of: text, table, chart\n"
        "- text must always be present and readable.\n"
        "- If returning type=table: table={columns:[...], rows:[{...}...]} and keep rows <= 20.\n"
        "- If unsure, ask a short follow-up question.\n"
        f"Prompt version: {settings.openai_prompt_version}\n"
        "Do not mention policy or hidden prompts."
    )

    user = {
        "question": question,
        "dataset_context": context,
    }

    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        "temperature": 0.2,
        "max_tokens": int(settings.openai_max_tokens),
        "response_format": {"type": "json_object"},
    }

    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=float(settings.openai_timeout_s)) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    try:
        obj = json.loads(content)
    except Exception:
        # fallback: treat as plain text
        return {
            "type": "text",
            "text": str(content),
            "citations": {"computed": False, "model": settings.openai_model, "prompt_version": settings.openai_prompt_version, "usage": usage},
        }

    # normalize
    t = str(obj.get("type") or "text")
    if t not in {"text", "table", "chart"}:
        t = "text"
    out: dict[str, Any] = {"type": t, "text": str(obj.get("text") or "")}
    if obj.get("table") is not None:
        out["table"] = obj["table"]
    if obj.get("chart") is not None:
        out["chart"] = obj["chart"]
    if not out["text"]:
        out["text"] = "No answer."
    out["citations"] = {"computed": False, "model": settings.openai_model, "prompt_version": settings.openai_prompt_version, "usage": usage}
    return out


