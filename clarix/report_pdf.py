"""Branded PDF report builder for the Clarix One-Click Plan.

Uses ReportLab's platypus flowables with the Clarix dark-on-white print palette.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak,
)

# --- Brand palette (print-tuned: white background, red accent) ---
BRAND_RED       = colors.HexColor("#bb2727")
BRAND_RED_DARK  = colors.HexColor("#7a1818")
BRAND_RED_SOFT  = colors.HexColor("#fde0e0")
INK             = colors.HexColor("#0E1117")
INK_SOFT        = colors.HexColor("#3a4250")
MUTED           = colors.HexColor("#6b7280")
LINE            = colors.HexColor("#e5e7eb")
SLATE_TINT      = colors.HexColor("#f3f4f6")
OK_GREEN        = colors.HexColor("#15803d")
WARN_AMBER      = colors.HexColor("#b45309")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title":   ParagraphStyle("title", parent=base["Title"],
                                  fontName="Helvetica-Bold", fontSize=22,
                                  textColor=INK, spaceAfter=4, leading=26),
        "tag":     ParagraphStyle("tag", parent=base["Normal"],
                                  fontName="Helvetica-Bold", fontSize=8,
                                  textColor=BRAND_RED, spaceAfter=10,
                                  letterSpace=2),
        "h2":      ParagraphStyle("h2", parent=base["Heading2"],
                                  fontName="Helvetica-Bold", fontSize=13,
                                  textColor=INK, spaceBefore=14, spaceAfter=6,
                                  leftIndent=0, leading=16),
        "body":    ParagraphStyle("body", parent=base["Normal"],
                                  fontName="Helvetica", fontSize=10,
                                  textColor=INK_SOFT, leading=14, alignment=TA_LEFT),
        "meta":    ParagraphStyle("meta", parent=base["Normal"],
                                  fontName="Helvetica", fontSize=9,
                                  textColor=MUTED, leading=13),
        "footer":  ParagraphStyle("footer", parent=base["Normal"],
                                  fontName="Helvetica-Oblique", fontSize=8,
                                  textColor=MUTED, leading=11),
    }


def _kpi_table(kpis: dict[str, str]) -> Table:
    rows = list(kpis.items())
    # 2 columns of pairs => grid of (label, value) cells
    pairs = []
    for i in range(0, len(rows), 2):
        left = rows[i]
        right = rows[i + 1] if i + 1 < len(rows) else ("", "")
        pairs.append([
            Paragraph(f"<font size=8 color='#6b7280'><b>{left[0].upper()}</b></font><br/>"
                      f"<font size=14 color='#0E1117'><b>{left[1]}</b></font>", _styles()["body"]),
            Paragraph(f"<font size=8 color='#6b7280'><b>{right[0].upper()}</b></font><br/>"
                      f"<font size=14 color='#0E1117'><b>{right[1]}</b></font>", _styles()["body"]),
        ])
    tbl = Table(pairs, colWidths=[85 * mm, 85 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), SLATE_TINT),
        ("BOX",          (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID",    (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LINEBEFORE",   (0, 0), (0, -1), 3, BRAND_RED),
    ]))
    return tbl


def _df_table(df: pd.DataFrame, header_map: dict[str, str] | None = None,
              col_widths: list[float] | None = None) -> Table:
    if df.empty:
        return Table([["No data."]], colWidths=[170 * mm], style=TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica-Oblique", 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), MUTED),
            ("BACKGROUND", (0, 0), (-1, -1), SLATE_TINT),
            ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
    cols = list(df.columns)
    headers = [header_map.get(c, c) if header_map else c for c in cols]
    body = [headers] + [[str(v) for v in row] for row in df.itertuples(index=False, name=None)]
    if col_widths is None:
        col_widths = [170 * mm / len(cols)] * len(cols)
    tbl = Table(body, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BRAND_RED),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONT",         (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN",        (0, 0), (-1, 0), "LEFT"),
        ("FONT",         (0, 1), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR",    (0, 1), (-1, -1), INK_SOFT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SLATE_TINT]),
        ("BOX",          (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID",    (0, 0), (-1, -1), 0.25, LINE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _header_footer(canvas, doc):
    canvas.saveState()
    # Top brand bar
    canvas.setFillColor(BRAND_RED)
    canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(15 * mm, A4[1] - 5.5 * mm, "CLARIX  /  Capacity & Sourcing Plan")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 15 * mm, A4[1] - 5.5 * mm,
                           datetime.now().strftime("%Y-%m-%d  %H:%M"))
    # Footer
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.drawString(15 * mm, 10 * mm,
                      "Generated by Clarix  /  Danfoss Climate Solutions hackathon case 3")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(15 * mm, 13 * mm, A4[0] - 15 * mm, 13 * mm)
    canvas.restoreState()


def build_plan_pdf(
    *,
    region: str,
    quarter: str | None,
    scenario_label: str,
    plant_filter: str,
    kpis: dict[str, str],
    bottlenecks: pd.DataFrame,
    sourcing: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> bytes:
    """Build a branded PDF and return it as bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Clarix Plan", author="Clarix",
    )
    s = _styles()
    flow: list[Any] = []

    flow.append(Paragraph("CAPACITY &amp; SOURCING PLAN", s["tag"]))
    flow.append(Paragraph("One-Click Plan Report", s["title"]))
    meta = (f"<b>Region:</b> {region}  &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Quarter:</b> {quarter or 'all'}  &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Scenario:</b> {scenario_label}  &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Plant:</b> {plant_filter}")
    flow.append(Paragraph(meta, s["meta"]))
    flow.append(Spacer(1, 14))

    flow.append(Paragraph("Headline KPIs", s["h2"]))
    flow.append(_kpi_table(kpis))
    flow.append(Spacer(1, 6))

    flow.append(Paragraph("Top 5 Bottlenecks", s["h2"]))
    bot = bottlenecks.copy()
    if not bot.empty:
        keep = [c for c in ["work_center", "plant", "peak_util", "weeks_crit"] if c in bot.columns]
        bot = bot[keep].copy()
        if "peak_util" in bot.columns:
            bot["peak_util"] = (pd.to_numeric(bot["peak_util"], errors="coerce") * 100).round(1).astype(str) + "%"
        bot = bot.rename(columns={"work_center": "Work center", "plant": "Plant",
                                  "peak_util": "Peak util", "weeks_crit": "Weeks >=100%"})
    flow.append(_df_table(bot))

    flow.append(Paragraph("Top 5 Sourcing Alerts", s["h2"]))
    src = sourcing.copy()
    if not src.empty:
        keep = [c for c in ["component_material", "plant", "shortfall", "order_by"] if c in src.columns]
        src = src[keep].copy()
        if "shortfall" in src.columns:
            src["shortfall"] = pd.to_numeric(src["shortfall"], errors="coerce").round(0).astype("Int64")
        src = src.rename(columns={"component_material": "Material", "plant": "Plant",
                                  "shortfall": "Shortfall", "order_by": "Order by"})
    flow.append(_df_table(src))

    flow.append(Paragraph("Scenario Comparison", s["h2"]))
    sce = scenarios.copy()
    if not sce.empty:
        if "label" in sce.columns and "scenario" in sce.columns:
            sce = sce[["label", "peak_util", "weeks_critical", "total_demand_hours"]]
        if "peak_util" in sce.columns:
            sce["peak_util"] = (pd.to_numeric(sce["peak_util"], errors="coerce") * 100).round(1).astype(str) + "%"
        if "total_demand_hours" in sce.columns:
            sce["total_demand_hours"] = pd.to_numeric(sce["total_demand_hours"], errors="coerce").round(0).astype("Int64")
        sce = sce.rename(columns={"label": "Scenario", "peak_util": "Peak util",
                                  "weeks_critical": "Weeks critical",
                                  "total_demand_hours": "Demand hrs"})
    flow.append(_df_table(sce))

    flow.append(Spacer(1, 18))
    flow.append(Paragraph(
        "This report was generated automatically from the Clarix capacity engine using the "
        "live filters in the Streamlit application. KPIs reflect the selected region, quarter, "
        "scenario, plant filter and (where applicable) maintenance scenario at the moment of export.",
        s["footer"],
    ))

    doc.build(flow, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()
