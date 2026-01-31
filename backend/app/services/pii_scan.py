from __future__ import annotations

import re
from typing import Any

import pandas as pd


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{3}\)?[\s\-]?)\d{3}[\s\-]?\d{4}\b")


def pii_scan(df: pd.DataFrame, max_cols: int = 40, sample_size: int = 200) -> dict[str, Any]:
    """
    Lightweight PII risk scan (best-effort):
    - checks column names (email/phone/address/name)
    - checks sample values for email/phone patterns
    Returns: { risk: "low"|"medium"|"high", findings: [...] }
    """
    findings: list[dict[str, Any]] = []
    cols = [str(c) for c in df.columns.tolist()][:max_cols]
    sample_df = df[cols].head(sample_size)

    for c in cols:
        name = c.lower()
        name_hits = []
        if "email" in name:
            name_hits.append("email_keyword")
        if "phone" in name or "mobile" in name:
            name_hits.append("phone_keyword")
        if "address" in name:
            name_hits.append("address_keyword")
        if name in {"name", "first_name", "last_name"} or "name" in name:
            name_hits.append("name_keyword")

        s = sample_df[c].astype(str).fillna("")
        values = s.tolist()
        email_hits = sum(1 for v in values if EMAIL_RE.search(v or ""))
        phone_hits = sum(1 for v in values if PHONE_RE.search(v or ""))

        if name_hits or email_hits or phone_hits:
            score = 0
            score += 2 * len(name_hits)
            score += 3 if email_hits > 0 else 0
            score += 2 if phone_hits > 0 else 0
            findings.append(
                {
                    "column": c,
                    "signals": name_hits + (["email_pattern"] if email_hits else []) + (["phone_pattern"] if phone_hits else []),
                    "sample_matches": {"email": int(email_hits), "phone": int(phone_hits)},
                    "score": int(score),
                }
            )

    total_score = sum(int(f.get("score") or 0) for f in findings)
    if total_score >= 8:
        risk = "high"
    elif total_score >= 3:
        risk = "medium"
    else:
        risk = "low"

    return {"risk": risk, "findings": sorted(findings, key=lambda x: int(x.get("score") or 0), reverse=True)[:12]}

