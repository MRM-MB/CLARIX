"""
clarix.ui
=========
Shared UI primitives for the Clarix dashboard.
All functions render Streamlit components — they return None.
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Badge vocabulary
# ---------------------------------------------------------------------------
_BADGES: dict[str, tuple[str, str]] = {
    "real":      ("pill-ok",    "REAL"),
    "synthetic": ("pill-warn",  "SYNTHETIC"),
    "derived":   ("pill-info",  "DERIVED"),
    "enriched":  ("pill-slate", "ENRICHED"),
}


def data_source_strip(sources: list[tuple[str, str]]) -> None:
    """Render the data provenance strip at the top of a page body.

    Args:
        sources: list of (badge_type, label)
                 badge_type: "real" | "synthetic" | "derived" | "enriched"
                 label: e.g. "fact_planner_actions_v2"

    Example:
        ui.data_source_strip([
            ("real",      "fact_planner_actions_v2"),
            ("synthetic", "transit times"),
        ])
    """
    parts = []
    for badge_type, label in sources:
        pill_cls, pill_text = _BADGES.get(badge_type, ("pill-slate", badge_type.upper()))
        parts.append(f"<span class='pill {pill_cls}'>{pill_text}</span>&nbsp;{label}")
    st.markdown(
        "<div style='font-size:11px; color:var(--muted); padding:4px 0 12px 0;'>"
        + "&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts)
        + "</div>",
        unsafe_allow_html=True,
    )


def empty_state(title: str, message: str = "", hint: str = "") -> None:
    """Render a centered empty-state panel.

    Args:
        title:   Primary message (e.g. "No actions available")
        message: Secondary explanation (e.g. "Run the Wave 7 pipeline first")
        hint:    CLI hint or action (e.g. "python -m project.src.wave7.runner")
    """
    parts = [
        "<div style='text-align:center; padding:40px 20px; "
        "background:var(--bg-soft); border:1px solid var(--line); "
        "border-radius:12px; margin:16px 0;'>",
        f"<div style='font-size:16px; font-weight:700; color:var(--ink); "
        f"margin-bottom:8px;'>{title}</div>",
    ]
    if message:
        parts.append(
            f"<div style='font-size:13px; color:var(--ink-soft); margin-bottom:8px;'>{message}</div>"
        )
    if hint:
        parts.append(
            f"<div style='font-size:12px; color:var(--muted); "
            f"font-family:\"JetBrains Mono\",Consolas,monospace; "
            f"background:var(--bg); padding:6px 12px; border-radius:6px; "
            f"display:inline-block;'>{hint}</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def assumption_panel(text: str) -> None:
    """Render an assumption/warning note panel (slate-styled, non-intrusive)."""
    st.markdown(
        f"<div style='background:var(--slate-wash,#161B22); border-left:4px solid var(--slate,#475569); "
        f"padding:12px 16px; border-radius:8px; margin-bottom:18px; color:var(--ink); font-size:13px;'>"
        f"<b style='color:var(--ink-soft);'>Assumption</b>&nbsp;&nbsp;{text}"
        f"</div>",
        unsafe_allow_html=True,
    )


def why_panel(
    project_id: str,
    action_type: str,
    reason: str,
    expected_effect: str,
    caution_level: str = "—",
    caution_explanation: str = "",
    explanation_trace_json: str = "",
    service_memory_df: pd.DataFrame | None = None,
) -> None:
    """Render the 'Why this recommendation?' explanation panel.

    Includes the primary card, key metrics, and optional expandable trace/history.
    """
    caution_pill_cls = {
        "high": "pill-crit", "medium": "pill-warn", "low": "pill-ok"
    }.get(caution_level, "pill-slate")

    caution_note = caution_explanation or "No carry-over caution for this project."

    st.markdown(
        f"<div style='background:var(--bg-soft); border-left:4px solid var(--accent-brand); "
        f"padding:14px 18px; border-radius:8px; margin-bottom:16px; "
        f"font-size:13px; color:var(--ink-soft); line-height:1.7;'>"
        f"<b style='color:var(--ink); font-size:15px;'>{project_id}</b>&nbsp;"
        f"<span class='pill {caution_pill_cls}'>{caution_level.upper()} CAUTION</span>"
        f"<br><br>"
        f"<b style='color:var(--ink);'>Recommended action:</b>&nbsp;{action_type}<br>"
        f"<b style='color:var(--ink);'>Reason:</b>&nbsp;{reason}<br>"
        f"<b style='color:var(--ink);'>Expected effect:</b>&nbsp;{expected_effect}<br>"
        f"<b style='color:var(--ink);'>Quarter caution context:</b>&nbsp;{caution_note}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if explanation_trace_json:
        with st.expander("Full explanation trace"):
            try:
                parsed = json.loads(explanation_trace_json)
                _render_trace_dict(parsed)
            except (json.JSONDecodeError, TypeError):
                st.code(str(explanation_trace_json), language="json")

    if service_memory_df is not None and not service_memory_df.empty:
        with st.expander("Service memory history for this project"):
            st.dataframe(service_memory_df, use_container_width=True, hide_index=True)


def _render_trace_dict(trace: dict) -> None:
    """Pretty-render a parsed explanation_trace dict."""
    field_labels = {
        "top_driver":            "Top driver",
        "action_selected":       "Action selected",
        "maint_severity":        "Maintenance severity",
        "has_protect_opportunity": "Protect opportunity",
        "caution_carry_over":    "Caution carry-over",
        "reroute_target":        "Reroute target",
        "risk_score":            "Risk score",
        "action_score":          "Action score",
        "confidence":            "Confidence",
    }
    cols = st.columns(3)
    items = [(field_labels.get(k, k), v) for k, v in trace.items()]
    for i, (label, value) in enumerate(items):
        with cols[i % 3]:
            st.markdown(
                f"<div style='font-size:11px; color:var(--muted); text-transform:uppercase; "
                f"letter-spacing:1px; font-weight:700;'>{label}</div>"
                f"<div style='font-size:14px; color:var(--ink); font-weight:600; margin-top:2px;'>"
                f"{str(value)}</div>",
                unsafe_allow_html=True,
            )


def planner_mode_banner() -> None:
    """Render the 'no API key' info banner on Ask Clarix."""
    st.info(
        "**Planner mode** - set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` for the full conversational agent. "
        "The deterministic fallback still answers questions about *bottlenecks*, "
        "*sourcing*, and *scenario comparison*."
    )
