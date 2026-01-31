from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def render_pdf_report(report_dir: str, dataset_id: str, analysis: dict[str, Any]) -> str:
    Path(report_dir).mkdir(parents=True, exist_ok=True)
    path = Path(report_dir) / f"{dataset_id}.pdf"

    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter

    y = h - 0.75 * inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, y, "Instant Dashboard Report")

    y -= 0.4 * inch
    c.setFont("Helvetica", 10)
    shape = analysis.get("profile", {}).get("shape", {})
    c.drawString(0.75 * inch, y, f"Rows: {shape.get('rows', '?')}   Columns: {shape.get('cols', '?')}")

    y -= 0.35 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, y, "Executive brief")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    brief = (analysis.get("overview") or {}).get("executive_brief") if isinstance(analysis.get("overview"), dict) else None
    bullets = (brief or {}).get("bullets") if isinstance(brief, dict) else None
    if isinstance(bullets, list) and bullets:
        for b in bullets[:6]:
            y -= 0.18 * inch
            if y < 1.0 * inch:
                c.showPage()
                y = h - 0.75 * inch
                c.setFont("Helvetica", 10)
            c.drawString(0.9 * inch, y, f"- {str(b)[:160]}")
    else:
        y -= 0.18 * inch
        c.drawString(0.9 * inch, y, "- (No executive brief available for this dataset.)")

    y -= 0.35 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, y, "Key insights")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    for ins in (analysis.get("insights", []) or [])[:10]:
        txt = str(ins.get("text", "")).strip()
        if not txt:
            continue
        y -= 0.18 * inch
        if y < 1.0 * inch:
            c.showPage()
            y = h - 0.75 * inch
            c.setFont("Helvetica", 10)
        c.drawString(0.9 * inch, y, f"- {txt[:160]}")

    y -= 0.35 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, y, "Anomalies (top)")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    for a in (analysis.get("anomalies", []) or [])[:10]:
        y -= 0.18 * inch
        if y < 1.0 * inch:
            c.showPage()
            y = h - 0.75 * inch
            c.setFont("Helvetica", 10)
        c.drawString(0.9 * inch, y, f"- {json.dumps(a)[:160]}")

    c.showPage()
    c.save()
    return str(path)



