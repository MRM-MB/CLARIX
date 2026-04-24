"""
Clarix - Probabilistic Capacity-and-Sourcing Engine
Streamlit dashboard for the Danfoss Climate Solutions hackathon (case 3).

Run:
    streamlit run app.py
Optional:
    set ANTHROPIC_API_KEY=...     (Windows)
    export ANTHROPIC_API_KEY=...  (Mac/Linux)
"""
from __future__ import annotations

import os
from pathlib import Path

# Load .env (ANTHROPIC_API_KEY or GEMINI_API_KEY) before anything else
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pandas as pd
import streamlit as st

from clarix.agent import run_agent
from clarix.charts import (
    ACCENT, ACCENT_DARK, ACCENT_SOFT, ACCENT_WASH, BG_SOFT,
    INK, INK_SOFT, LINE, MUTED, SLATE, SLATE_DARK, SLATE_SOFT, SLATE_TINT, SLATE_WASH,
    OK_GREEN,
    pipeline_funnel, plant_demand_treemap, scenario_compare_bar,
    sourcing_table_fig, utilization_heatmap, utilization_lines,
    pipeline_timeline_bar, action_score_bar, action_type_donut,
    maintenance_impact_bar, effective_capacity_timeline,
    delivery_commitment_chart, risk_rollforward_waterfall,
    lead_time_breakdown_bar,
)
import clarix.ui as ui
from clarix.report_pdf import build_plan_pdf
_DASH = "—"  # em dash, safe outside f-string expressions
from clarix.data_loader import DEFAULT_XLSX, load_canonical
from clarix.engine import (
    SCENARIOS, build_utilization, detect_bottlenecks, sourcing_recommendations,
    list_addable_materials, project_feasibility, quarter_to_month,
)

try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from project.src.app.demo_layer import (
        load_all_processed,
        derive_planner_actions,
        get_demo_summary,
    )
    _DEMO_LAYER_AVAILABLE = True
except ImportError:
    _DEMO_LAYER_AVAILABLE = False


# =============================================================================
# Page config + theme
# =============================================================================
FAVICON = Path("assets/favicon.svg")
LOGO    = Path("logo.png")

st.set_page_config(
    page_title="Clarix | Capacity & Sourcing",
    page_icon=str(FAVICON) if FAVICON.exists() else "\U0001F517",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {{
    --accent:      {ACCENT};
    --accent-dark: {ACCENT_DARK};
    --accent-soft: {ACCENT_SOFT};
    --accent-wash: {ACCENT_WASH};
    --accent-brand: #bb2727;
    --slate:       {SLATE};
    --slate-dark:  {SLATE_DARK};
    --slate-soft:  {SLATE_SOFT};
    --slate-tint:  {SLATE_TINT};
    --slate-wash:  {SLATE_WASH};
    --ink:         {INK};
    --ink-soft:    {INK_SOFT};
    --muted:       {MUTED};
    --line:        {LINE};
    --bg:          {"#0E1117"};
    --bg-soft:     {BG_SOFT};
    --bg-elev:     {SLATE_TINT};
    --ok:          {OK_GREEN};
    --ok-green:    {OK_GREEN};
}}

/* ---------- Global dark surfaces ---------- */
html, body, [class*="css"], .stApp {{
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    color: var(--ink);
    background: var(--bg);
}}
.stApp {{ background: var(--bg) !important; }}
header[data-testid="stHeader"] {{ background: var(--bg) !important; border-bottom: 1px solid var(--line); }}
header[data-testid="stHeader"] * {{ color: var(--ink) !important; }}
[data-testid="stToolbar"] {{ background: var(--bg) !important; }}
[data-testid="stDecoration"] {{ background: linear-gradient(90deg, var(--accent-brand), var(--accent-dark)) !important; }}

.block-container {{ padding-top: 4.5rem; padding-bottom: 2rem; max-width: 1500px; }}
h1, h2, h3, h4, h5 {{ color: var(--ink) !important; font-weight: 700; letter-spacing: -0.01em; }}
p, li, label, span, div {{ color: var(--ink); }}
a {{ color: var(--accent-soft) !important; }}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {BG_SOFT} 0%, {SLATE_DARK} 100%);
    border-right: 1px solid var(--line);
}}
section[data-testid="stSidebar"] * {{ color: var(--ink) !important; }}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: var(--ink-soft) !important; }}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
    padding: 9px 14px; border-radius: 8px; margin-bottom: 4px;
    font-weight: 500; transition: all 0.15s; border-left: 3px solid transparent;
    cursor: pointer; background: transparent;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: rgba(187,39,39,0.08); border-left-color: var(--accent-soft);
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
    background: rgba(187,39,39,0.14); border-left-color: var(--accent-brand);
    color: #FFFFFF !important; font-weight: 700;
}}
section[data-testid="stSidebar"] h3 {{
    font-size: 11px !important; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--muted) !important; margin-top: 18px !important; margin-bottom: 6px !important;
    font-weight: 700 !important;
}}
.brand {{ padding: 4px 0 14px 0; border-bottom: 1px solid var(--line); margin-bottom: 14px; }}
.brand-tag {{
    font-size: 10.5px; color: var(--muted) !important; letter-spacing: 1.6px;
    text-transform: uppercase; margin-top: 6px; font-weight: 600;
}}

/* ---------- Sidebar nav (radio styled as menu) ---------- */
section[data-testid="stSidebar"] div[role="radiogroup"] {{
    gap: 2px !important;
}}
/* Page list (vertical) - rendered as full-width menu items */
section[data-testid="stSidebar"] div[data-testid="stRadio"]:not([aria-label="Section"]) > div > label,
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {{
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    margin: 1px 0 !important;
    width: 100% !important;
    transition: all 0.12s ease !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {{
    background: rgba(255,255,255,0.04) !important;
    border-color: var(--line) !important;
}}
/* Active item: red accent bar + soft red wash */
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{
    background: linear-gradient(90deg, rgba(187,39,39,0.18), rgba(187,39,39,0.04)) !important;
    border-color: rgba(187,39,39,0.35) !important;
    border-left: 3px solid var(--accent-brand) !important;
    padding-left: 11px !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] p {{
    font-size: 13px !important; font-weight: 600 !important;
    color: var(--ink-soft) !important; letter-spacing: 0.1px !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {{
    color: #FFFFFF !important; font-weight: 700 !important;
}}
/* Hide the radio dot - we use the bar instead */
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{
    display: none !important;
}}

/* ---------- Main page header ---------- */
.page-header {{
    display: flex; align-items: center; gap: 14px;
    padding: 6px 0 14px 0; margin-bottom: 8px;
    border-bottom: 1px solid var(--line);
}}

/* ---------- KPI cards ---------- */
.kpi-card {{
    background: var(--bg-soft); border: 1px solid var(--line); border-radius: 14px;
    padding: 18px 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.35);
    height: 100%; transition: all 0.15s;
}}
.kpi-card:hover {{ border-color: var(--slate-soft); box-shadow: 0 4px 18px rgba(0,0,0,0.5); }}
.kpi-card .kpi-label {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 1.3px;
    color: var(--muted); font-weight: 700;
}}
.kpi-card .kpi-value {{
    font-size: 30px; font-weight: 800; color: var(--ink);
    margin-top: 8px; line-height: 1.1; letter-spacing: -0.02em;
}}
.kpi-card .kpi-sub {{ font-size: 12px; color: var(--ink-soft); margin-top: 6px; }}
.kpi-accent {{ border-left: 4px solid var(--accent); }}
.kpi-accent .kpi-value {{ color: var(--accent-soft); }}
.kpi-warn   {{ border-left: 4px solid var(--accent-soft); }}
.kpi-warn .kpi-value {{ color: var(--accent-soft); }}
.kpi-ok     {{ border-left: 4px solid var(--ok); }}
.kpi-ok .kpi-value {{ color: var(--ok); }}
.kpi-slate  {{ border-left: 4px solid var(--slate-soft); }}
.kpi-slate .kpi-value {{ color: var(--ink); }}
.kpi-info   {{ border-left: 4px solid #38bdf8; }}
.kpi-info .kpi-value {{ color: #7DD3FC; }}

/* ---------- Demo mode banner ---------- */
.demo-banner {{
    background: linear-gradient(90deg, rgba(187,39,39,0.10) 0%, rgba(30,58,95,0.10) 100%);
    border: 1px solid rgba(187,39,39,0.25);
    border-left: 4px solid var(--accent-brand);
    border-radius: 10px; padding: 12px 18px; margin-bottom: 18px;
}}
.demo-step-num {{
    font-size: 10.5px; color: var(--accent-soft); text-transform: uppercase;
    letter-spacing: 1.5px; font-weight: 700; margin-bottom: 2px;
}}
.demo-step-title {{ font-size: 16px; font-weight: 800; color: var(--ink); letter-spacing: -0.01em; }}
.demo-step-desc  {{ font-size: 12px; color: var(--ink-soft); margin-top: 4px; line-height: 1.6; }}
.demo-nav-hint   {{ font-size: 11px; color: var(--muted); margin-top: 6px; font-style: italic; }}

/* ---------- Section headers ---------- */
.section-h {{
    font-size: 19px; font-weight: 700; color: var(--ink) !important;
    margin: 26px 0 4px 0; letter-spacing: -0.01em;
    display: flex; align-items: center; gap: 10px;
}}
.section-h::before {{
    content: ''; display: inline-block; width: 4px; height: 18px;
    background: var(--accent-brand); border-radius: 2px;
}}
.section-sub {{ font-size: 13px; color: var(--ink-soft); margin: 4px 0 14px 14px; }}

/* ---------- Pills ---------- */
.pill {{
    display: inline-block; padding: 4px 11px; border-radius: 999px; font-size: 11px;
    font-weight: 700; letter-spacing: 0.4px; text-transform: uppercase;
}}
.pill-ok    {{ background: rgba(34,197,94,0.18);  color: #4ADE80; }}
.pill-warn  {{ background: rgba(251,113,133,0.18); color: #FCA5A5; }}
.pill-crit  {{ background: rgba(239,68,68,0.22);  color: #FECACA; }}
.pill-slate {{ background: rgba(148,163,184,0.18); color: #CBD5E1; }}
.pill-info  {{ background: rgba(56,189,248,0.18); color: #7DD3FC; }}

/* ---------- Chat ---------- */
.chat-msg {{ padding: 14px 18px; border-radius: 12px; margin-bottom: 12px;
             line-height: 1.55; font-size: 14px; color: var(--ink); }}
.chat-user {{ background: var(--bg-soft); border: 1px solid var(--line); }}
.chat-assistant {{ background: var(--bg-soft); border: 1px solid var(--line);
                   border-left: 4px solid var(--accent-brand); }}
.chat-tool {{ background: var(--bg-elev); border: 1px dashed var(--slate-soft);
              font-size: 12px; color: var(--ink-soft);
              font-family: 'JetBrains Mono', Consolas, monospace; }}
.chat-msg b {{ color: var(--accent-soft); font-weight: 700; }}

/* ---------- Inputs (dark) ---------- */
hr {{ border: none; border-top: 1px solid var(--line); margin: 22px 0; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{
    background: transparent; border-radius: 10px 10px 0 0; padding: 10px 18px;
    font-weight: 600; color: var(--muted);
}}
.stTabs [aria-selected="true"] {{ background: var(--accent-brand) !important; color: #FFFFFF !important; }}
.stButton button {{
    background: var(--bg-soft); color: var(--ink); border: 1px solid var(--line);
    border-radius: 10px; padding: 8px 14px; font-weight: 500;
    transition: all 0.15s;
}}
.stButton button:hover {{
    border-color: var(--accent-brand); color: #FFFFFF;
    background: rgba(187,39,39,0.18);
}}
.stButton button[kind="primary"] {{
    background: var(--accent-brand); color: #FFFFFF; border-color: var(--accent-dark);
}}
.stButton button[kind="primary"]:hover {{
    background: var(--accent-dark); color: #FFFFFF;
}}
.stSelectbox label, .stSlider label, .stRadio label, .stNumberInput label, .stTextInput label {{
    font-size: 12px; color: var(--ink-soft) !important; font-weight: 600;
}}
[data-testid="stCaptionContainer"], small {{ color: var(--ink-soft) !important; }}
[data-baseweb="select"] > div {{
    background: var(--bg-soft) !important; border-color: var(--line) !important;
    color: var(--ink) !important;
}}
[data-baseweb="select"] * {{ color: var(--ink) !important; }}
[data-baseweb="popover"], [data-baseweb="menu"] {{
    background: var(--bg-soft) !important; color: var(--ink) !important;
}}
[data-baseweb="menu"] li {{ background: var(--bg-soft) !important; color: var(--ink) !important; }}
[data-baseweb="menu"] li:hover {{ background: var(--bg-elev) !important; }}
input, textarea {{ background: var(--bg-soft) !important; color: var(--ink) !important; border-color: var(--line) !important; }}
[data-testid="stChatInput"] textarea {{ background: var(--bg-soft) !important; color: var(--ink) !important; }}
.stSlider [data-baseweb="slider"] div[role="slider"] {{ background: var(--accent-brand) !important; }}
.stSlider [data-baseweb="slider"] > div > div {{ background: var(--accent-brand) !important; }}

/* ---------- Tables ---------- */
.stDataFrame {{ border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
.stDataFrame [data-testid="stTable"], .stDataFrame table {{ background: var(--bg-soft) !important; color: var(--ink) !important; }}
[data-testid="stDataFrameResizable"] {{ background: var(--bg-soft) !important; }}
[data-testid="stTable"] td, [data-testid="stTable"] th {{ color: var(--ink) !important; background: var(--bg-soft) !important; }}
[data-testid="stMetricValue"] {{ color: var(--accent-soft) !important; font-weight: 700; }}
[data-testid="stMetricLabel"] {{ color: var(--muted) !important; }}

/* ---------- Alerts ---------- */
.stAlert {{ background: var(--bg-soft) !important; border: 1px solid var(--line) !important; border-radius: 10px; }}
.stAlert, .stAlert p, .stAlert div, .stAlert li {{ color: var(--ink) !important; }}
.stAlert [data-baseweb="notification"] {{ background: var(--bg-soft) !important; }}

/* ---------- Expanders ---------- */
[data-testid="stExpander"] {{ background: var(--bg-soft); border: 1px solid var(--line); border-radius: 10px; }}
[data-testid="stExpander"] summary {{ color: var(--ink) !important; font-weight: 600; }}
[data-testid="stExpander"] summary:hover {{ color: var(--accent-soft) !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--slate-soft); border-radius: 5px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--accent-brand); }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =============================================================================
# Cached data layer
# =============================================================================
@st.cache_resource(show_spinner="Loading workbook + building canonical tables ...")
def get_data():
    return load_canonical(DEFAULT_XLSX)


@st.cache_data(show_spinner=False)
def get_utilization(scenario: str, plant: str | None):
    return build_utilization(get_data(), scenario, plant=plant)


@st.cache_data(show_spinner=False)
def get_bottlenecks(scenario: str, plant: str | None):
    return detect_bottlenecks(get_utilization(scenario, plant))


@st.cache_data(show_spinner=False)
def get_sourcing(scenario: str, plant: str | None, top_n: int = 25):
    return sourcing_recommendations(get_data(), scenario, plant=plant, top_n=top_n)


data = get_data()


# =============================================================================
# Wave 7 helper — cached loader for all processed Wave 6/7 outputs
# Defined here (above page conditionals) so every page can call it safely.
# =============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def _load_w7() -> dict[str, pd.DataFrame]:
    if _DEMO_LAYER_AVAILABLE:
        try:
            return load_all_processed()
        except Exception:
            pass
    base = Path("project/data/processed")
    _files = {
        "sourcing":     "fact_scenario_sourcing_weekly.csv",
        "logistics":    "fact_scenario_logistics_weekly.csv",
        "bottlenecks":  "fact_capacity_bottleneck_summary.csv",
        "region_scope": "dim_region_scope.csv",
        "pipeline_quarterly": "fact_pipeline_quarterly.csv",
        "effective_capacity_v2": "fact_effective_capacity_weekly_v2.csv",
        "delivery_commitment": "fact_delivery_commitment_weekly.csv",
        "service_memory": "fact_quarter_service_memory.csv",
        "delivery_rollforward": "fact_delivery_risk_rollforward.csv",
        "maintenance_impact": "fact_maintenance_impact_summary.csv",
        "learning_signals": "fact_quarter_learning_signals.csv",
        "rollforward_inputs": "fact_quarter_rollforward_inputs.csv",
        "planner_actions_v2": "fact_planner_actions_v2.csv",
        "integrated_risk_v2": "fact_integrated_risk_v2.csv",
        "project_priority": "dim_project_priority.csv",
    }
    return {k: pd.read_csv(base / v) if (base / v).exists() else pd.DataFrame()
            for k, v in _files.items()}


# Map engine scenario keys (used by sidebar) to the scenario labels used in the
# Wave 6/7 CSVs. Wave 7 v2 outputs use 'expected_value' / 'monte_carlo_light';
# the engine uses 'expected' / 'monte_carlo'. Without this map, filters return
# empty and panels show "No data — run Wave 7 pipeline first".
_W7_SCENARIO_MAP: dict[str, str] = {
    "all_in":           "all_in",
    "expected":         "expected_value",
    "high_confidence":  "high_confidence",
    "monte_carlo":      "monte_carlo_light",
    # Some legacy CSVs use these labels — pass them through unchanged.
    "pessimistic":      "pessimistic",
    "base":             "base",
    "optimistic":       "optimistic",
}


def _w7_scenario(engine_key: str) -> str:
    """Translate an engine scenario key to the label used in the Wave 7 CSVs."""
    return _W7_SCENARIO_MAP.get(engine_key, engine_key)


def _w7_filter(df: pd.DataFrame, engine_scenario: str) -> pd.DataFrame:
    """Filter a Wave 7 dataframe by scenario, mapping the engine key first.
    Falls back to all rows if the scenario column is absent or no match found."""
    if df is None or df.empty or "scenario" not in df.columns:
        return df if df is not None else pd.DataFrame()
    target = _w7_scenario(engine_scenario)
    out = df[df["scenario"] == target]
    if out.empty:
        # Try the raw key too (handles older v1 outputs)
        out = df[df["scenario"] == engine_scenario]
    return out.copy()


# ---- Scope (used in headers and KPIs) -----------------------------------
def _scope_strings():
    pipe = data.fact_pipeline_monthly
    cap = data.fact_wc_capacity_weekly
    n_plants_total = pipe["plant"].nunique()
    n_wcs_total = cap["work_center"].nunique() if not cap.empty else 0
    if "period_date" in pipe.columns:
        d = pd.to_datetime(pipe["period_date"], errors="coerce")
        d_min, d_max = d.min(), d.max()
        horizon = f"{d_min:%b %Y} - {d_max:%b %Y}"
        n_months = ((d_max.year - d_min.year) * 12 + (d_max.month - d_min.month)) + 1
    else:
        horizon, n_months = "n/a", 0
    return n_plants_total, n_wcs_total, horizon, n_months


N_PLANTS, N_WCS, HORIZON, N_MONTHS = _scope_strings()


# =============================================================================
# Sidebar
# =============================================================================
with st.sidebar:
    if LOGO.exists():
        st.image(str(LOGO), use_container_width=True)
        st.markdown(
            "<div class='brand'><div class='brand-tag'>Capacity &amp; Sourcing Engine</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='brand'>"
            "<div style='font-size:24px;font-weight:800;color:var(--accent-dark);letter-spacing:-0.02em;'>Clarix</div>"
            "<div class='brand-tag'>Capacity &amp; Sourcing Engine</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("### NAVIGATION")
    _main_tab = st.radio(
        "Tab",
        ["🏠  Homepage", "➕  Add Project", "📊  General Data", "⚙️  Machinery"],
        label_visibility="collapsed",
        key="main_tab",
    )

    if _main_tab == "📊  General Data":
        page = "General Data"
    elif _main_tab == "⚙️  Machinery":
        page = "Machinery"
    elif _main_tab == "➕  Add Project":
        page = "Add Project"
    else:
        page = "Homepage"

    _WAVE7_PAGES = {"Scope & Region", "Quarter History", "Capacity & Maintenance",
                    "Sourcing & Delivery", "Final Actions"}

    st.markdown("---")
    _has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    _has_gemini    = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if _has_anthropic:
        pill_class, pill_text, _agent_caption = "pill-ok", "CLAUDE", "Sonnet 4.5 / tool-use"
    elif _has_gemini:
        pill_class, pill_text, _agent_caption = "pill-ok", "GEMINI", "Gemini / function-calling"
    else:
        pill_class, pill_text, _agent_caption = "pill-warn", "PLANNER MODE", "Set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` for full chat."
    st.markdown(
        f"<div style='font-size:11px; color:var(--muted); font-weight:700; letter-spacing:1.2px;'>AGENT</div>"
        f"<div style='margin-top:4px;'><span class='pill {pill_class}'>{pill_text}</span></div>",
        unsafe_allow_html=True,
    )
    st.caption(_agent_caption)

    if st.button("\u21BB  Reset & reload data", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.cache_resource.clear()
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        import shutil
        shutil.rmtree("data/.clarix_cache", ignore_errors=True)
        st.rerun()

    st.markdown(
        "<div style='font-size:10px; color:var(--muted); margin-top:14px; text-align:center;'>"
        "v1.0 \u00b7 Danfoss Climate Solutions</div>",
        unsafe_allow_html=True,
    )

# =============================================================================
# Top filter bar (control plane in main area, not sidebar)
# =============================================================================
if page in {"Homepage", "Add Project", "General Data", "Machinery"}:
    # No global filter bar for these tabs — they manage their own state
    scenario = "expected"
    plant = None
    w7_region = "EMEA-West"
    w7_quarter = "2026-Q1"
    w7_maint = None
else:
    st.markdown(
        "<div style='display:flex; align-items:center; gap:10px; margin: 4px 0 6px 0;'>"
        "<span style='font-size:10.5px; color:var(--muted); font-weight:700; letter-spacing:1.6px;'>"
        "\u25B6 CONTROLS</span>"
        "<span style='flex:1; height:1px; background:var(--line);'></span>"
        "<span style='font-size:10.5px; color:var(--muted); font-style:italic;'>"
        "All KPIs and charts respond live to these filters</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    _show_maint_filter = page in _WAVE7_PAGES
    _filter_cols = st.columns([1.4, 1, 1.2, 1, 1.4] if _show_maint_filter else [1.4, 1, 1.2, 1])

    # ---- Region
    with _filter_cols[0]:
        _rscope_path = Path("project/data/processed/dim_region_scope.csv")
        if _rscope_path.exists():
            _rscope = pd.read_csv(_rscope_path)
            _active = _rscope[_rscope["active_flag"] == True] if "active_flag" in _rscope.columns else _rscope  # noqa: E712
            _region_opts = _active["region_name"].tolist() if not _active.empty else _rscope["region_name"].tolist()
        else:
            _region_opts = ["MVP 3-Plant"]
        w7_region = st.selectbox("\U0001F30D  Region / Country", _region_opts, index=0, key="flt_region")

    # ---- Quarter
    with _filter_cols[1]:
        _smem_path = Path("project/data/processed/fact_quarter_service_memory.csv")
        if _smem_path.exists():
            _smem = pd.read_csv(_smem_path)
            _qtrs = sorted(_smem["quarter_id"].dropna().unique().tolist()) if "quarter_id" in _smem.columns else ["2026-Q1"]
        else:
            _qtrs = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"]
        w7_quarter = st.selectbox("\U0001F4C5  Quarter", _qtrs + ["carry-over"], index=0, key="flt_quarter")

    # ---- Scenario
    with _filter_cols[2]:
        scenario = st.selectbox(
            "\u2699\ufe0f  Scenario", list(SCENARIOS.keys()),
            index=1, format_func=lambda k: SCENARIOS[k]["label"],
            help="All-in / expected / high-confidence / monte-carlo — drives demand probability weighting",
            key="flt_scenario",
        )

    # ---- Plant
    with _filter_cols[3]:
        plants = sorted([p for p in data.fact_pipeline_monthly["plant"].dropna().unique() if p])
        plant_opt = st.selectbox("\U0001F3ED  Plant", ["All plants"] + plants, key="flt_plant")
        plant = None if plant_opt == "All plants" else plant_opt

    # ---- Maintenance scenario (conditional)
    if _show_maint_filter:
        with _filter_cols[4]:
            _eff_path = Path("project/data/processed/fact_effective_capacity_weekly_v2.csv")
            if _eff_path.exists():
                _eff_hdr = pd.read_csv(_eff_path, nrows=1)
                _maint_scenarios = sorted(pd.read_csv(_eff_path)["scenario"].dropna().unique().tolist()) if "scenario" in _eff_hdr.columns else ["baseline_maintenance"]
            else:
                _maint_scenarios = ["baseline_maintenance", "maintenance_overrun", "preventive_maintenance_shift", "unexpected_breakdown"]
            w7_maint = st.selectbox("\U0001F527  Maintenance", _maint_scenarios, index=0,
                                    help="Switch to unexpected_breakdown to simulate machine failure",
                                    key="flt_maint")
    else:
        w7_maint = None

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


# =============================================================================
# Demo mode helpers
# =============================================================================
_demo_mode = st.session_state.get("demo_mode", False)

_DEMO_STEPS: dict[str, tuple[int, str, str, str]] = {
    # page_name: (step_num, step_title, story_desc, next_page)
    "Scope & Region": (
        1, "Scoped Pipeline",
        "We start with a focused regional scope \u2014 3 plants, real demand data. "
        "The MVP is intentionally narrow; the framework scales to all 15 plants.",
        "Next \u2192 Executive overview",
    ),
    "Executive overview": (
        2, "Prioritized Opportunities",
        "KPIs and W7 intelligence show the full business picture in under 30 seconds. "
        "Expected pipeline value, peak utilization, and top actions are all above the fold.",
        "Next \u2192 Quarter History",
    ),
    "Quarter History": (
        3, "Operational Exposure",
        "The system knows what happened last quarter and adjusts confidence scores accordingly. "
        "Repeated risks receive a penalty \u2014 planners are no longer surprised by the same problem twice.",
        "Next \u2192 Capacity & Maintenance",
    ),
    "Capacity & Maintenance": (
        4, "Maintenance-Aware Bottlenecks",
        "Nominal vs effective capacity reveals the real constraint after downtime. "
        "Bottleneck work centers are ranked with a suggested mitigation lever.",
        "Next \u2192 Sourcing & Delivery",
    ),
    "Sourcing & Delivery": (
        5, "Material Risk",
        "Shortages and order-by dates surface before they become expensive. "
        "The engine back-calculates from demand to raw material needs, offsetting live inventory.",
        "Next \u2192 Logistics & Disruptions",
    ),
    "Logistics & Disruptions": (
        6, "Disruption What-If",
        "Disruption scenarios quantify the cost of inaction vs rerouting. "
        "Planners can see landed cost tradeoffs and expedite eligibility at a glance.",
        "Next \u2192 Final Actions",
    ),
    "Final Actions": (
        7, "Final Action List",
        "Ranked planner actions \u2014 ready for sign-off. "
        "Every recommendation traces back to the risk score that generated it.",
        "End of demo \u2014 great job!",
    ),
}


def _render_demo_banner(page_name: str) -> None:
    """Render the demo step banner for the given page (only in demo mode)."""
    if not _demo_mode or page_name not in _DEMO_STEPS:
        return
    step_num, title, desc, nxt = _DEMO_STEPS[page_name]
    total = len(_DEMO_STEPS)
    progress_pips = "".join(
        f"<span style='display:inline-block;width:20px;height:4px;border-radius:2px;"
        f"background:{'var(--accent-brand)' if i <= step_num else 'var(--line)'};margin-right:3px;'></span>"
        for i in range(1, total + 1)
    )
    st.markdown(
        f"<div class='demo-banner'>"
        f"<div class='demo-step-num'>Demo \u00b7 Step {step_num} of {total}</div>"
        f"<div style='margin:4px 0 2px 0;'>{progress_pips}</div>"
        f"<div class='demo-step-title'>{title}</div>"
        f"<div class='demo-step-desc'>{desc}</div>"
        f"<div class='demo-nav-hint'>{nxt}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# Reusable helpers
# =============================================================================
def page_header(title: str, subtitle: str = ""):
    """Logo + title strip rendered at the top of every page."""
    cols = st.columns([1, 6])
    with cols[0]:
        if LOGO.exists():
            st.image(str(LOGO), width=110)
    with cols[1]:
        st.markdown(
            f"<div style='padding-top:10px;'>"
            f"  <div style='font-size:26px; font-weight:800; color:var(--ink); "
            f"             letter-spacing:-0.02em; line-height:1.1;'>{title}</div>"
            f"  <div style='font-size:12px; color:var(--muted); margin-top:4px; "
            f"             text-transform:uppercase; letter-spacing:1.3px; font-weight:600;'>"
            f"  {subtitle}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='border-bottom:1px solid var(--line); margin:10px 0 18px 0;'></div>",
                unsafe_allow_html=True)
    if page not in {"Homepage", "Add Project", "General Data", "Machinery"}:
        scope_strip()
    _render_demo_banner(page)


def kpi(label: str, value: str, sub: str = "", style: str = ""):
    st.markdown(
        f"""<div class="kpi-card {style}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def section(title: str, sub: str = ""):
    st.markdown(f"<div class='section-h'>{title}</div>", unsafe_allow_html=True)
    if sub:
        st.markdown(f"<div class='section-sub'>{sub}</div>", unsafe_allow_html=True)


def scope_strip():
    """Single context banner shown at the top of every page.
    Consolidates: Region, Quarter (with Q1-Q4 strip), Scenario, Scope (plants/WCs/horizon)."""
    # Build Q1-Q4 visual strip
    _current_q = w7_quarter if w7_quarter and w7_quarter != "carry-over" else "2026-Q1"
    _yr = _current_q.split("-")[0] if "-" in _current_q else "2026"
    _qstrip = ""
    for _q in ["Q1", "Q2", "Q3", "Q4"]:
        _qid = f"{_yr}-{_q}"
        _is_active = (_qid == _current_q)
        _bg = "var(--accent-brand)" if _is_active else "rgba(255,255,255,0.04)"
        _col = "#FFFFFF" if _is_active else "var(--muted)"
        _bd = "var(--accent-brand)" if _is_active else "var(--line)"
        _qstrip += (f"<div style='flex:1; background:{_bg}; color:{_col}; border:1px solid {_bd}; "
                    f"border-radius:5px; padding:3px 0; text-align:center; font-size:10px; "
                    f"font-weight:700; letter-spacing:0.4px;'>{_q}</div>")

    st.markdown(
        f"<div style='display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; "
        f"     margin:-6px 0 18px 0;'>"
        # Region card (red, prominent)
        f"  <div style='background:linear-gradient(135deg, rgba(187,39,39,0.20), rgba(187,39,39,0.06)); "
        f"       border:1px solid rgba(187,39,39,0.45); border-radius:10px; padding:10px 14px;'>"
        f"    <div style='font-size:10px; color:var(--accent-soft); letter-spacing:1.5px; "
        f"         text-transform:uppercase; font-weight:700;'>\U0001F30D Targeting Region</div>"
        f"    <div style='font-size:17px; color:#FFFFFF; font-weight:800; margin-top:3px; "
        f"         letter-spacing:-0.01em;'>{w7_region}</div>"
        f"  </div>"
        # Quarter card (with Q1-Q4 strip)
        f"  <div style='background:rgba(56,189,248,0.06); border:1px solid rgba(56,189,248,0.30); "
        f"       border-radius:10px; padding:8px 14px;'>"
        f"    <div style='font-size:10px; color:#7DD3FC; letter-spacing:1.5px; "
        f"         text-transform:uppercase; font-weight:700;'>\U0001F4C5 Active Quarter \u00b7 {_yr}</div>"
        f"    <div style='display:flex; gap:3px; margin-top:5px;'>{_qstrip}</div>"
        f"  </div>"
        # Scenario card
        f"  <div style='background:var(--bg-soft); border:1px solid var(--line); "
        f"       border-radius:10px; padding:10px 14px;'>"
        f"    <div style='font-size:10px; color:var(--muted); letter-spacing:1.5px; "
        f"         text-transform:uppercase; font-weight:700;'>\u2699\ufe0f Scenario</div>"
        f"    <div style='font-size:17px; color:var(--ink); font-weight:800; margin-top:3px; "
        f"         letter-spacing:-0.01em;'>{SCENARIOS[scenario]['label']}</div>"
        f"  </div>"
        # Scope card
        f"  <div style='background:var(--bg-soft); border:1px solid var(--line); "
        f"       border-radius:10px; padding:10px 14px;'>"
        f"    <div style='font-size:10px; color:var(--muted); letter-spacing:1.5px; "
        f"         text-transform:uppercase; font-weight:700;'>\U0001F4CA Scope</div>"
        f"    <div style='font-size:14px; color:var(--ink); font-weight:700; margin-top:3px; "
        f"         line-height:1.35;'>{N_PLANTS} plants \u00b7 {N_WCS} WCs<br>"
        f"      <span style='font-size:11px; color:var(--ink-soft); font-weight:500;'>{HORIZON}</span></div>"
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE: Homepage — Quotation Decision Cockpit
# =============================================================================
@st.dialog("Send to Production — No Simulation")
def _hp_no_sim_dialog() -> None:
    st.warning(
        "You haven't run a simulation yet. Sending to production without simulating "
        "means capacity and sourcing risks are **unknown**.\n\n"
        "Are you sure you want to proceed?"
    )
    _dc1, _dc2 = st.columns(2)
    with _dc1:
        if st.button("\u2705 Yes, send anyway", type="primary", use_container_width=True):
            st.session_state["hp_sent_to_prod"] = True
            st.rerun()
    with _dc2:
        if st.button("\u274C No, let me simulate", use_container_width=True):
            st.rerun()


if page == "Homepage":
    import numpy as np

    page_header("Homepage", "Quotation Decision Cockpit \u00b7 Select projects \u00b7 Simulate \u00b7 Decide")

    # Load project priority data
    _pp_path = Path("project/data/processed/dim_project_priority.csv")
    if _pp_path.exists():
        _pp = pd.read_csv(_pp_path)
    else:
        w7_hp = _load_w7()
        _pp = w7_hp.get("project_priority", pd.DataFrame())

    if _pp.empty:
        ui.empty_state("No project data", "Run Wave 7 pipeline first.", "python -m project.src.wave7.runner")
        st.stop()

    # Merge custom projects from Add Project tab
    _custom_projs = st.session_state.get("hp_custom_projects", [])
    if _custom_projs:
        _custom_pp = pd.DataFrame(_custom_projs)
        _pp = pd.concat([_pp, _custom_pp], ignore_index=True)

    # ---- Region filter (default EMEA-West) ----------------------------------
    _hp_regions = sorted(_pp["region"].dropna().unique().tolist())
    _hp_default = _hp_regions.index("EMEA-West") if "EMEA-West" in _hp_regions else 0
    _rc, _ = st.columns([1, 3])
    with _rc:
        _hp_region = st.selectbox("\U0001F30D Region", _hp_regions, index=_hp_default, key="hp_region")

    _hp_filtered = _pp[_pp["region"] == _hp_region].copy()

    # ---- Project multi-select -----------------------------------------------
    _hp_names = sorted(_hp_filtered["project_name"].dropna().tolist())
    _hp_selected = st.multiselect(
        "\U0001F4CB Select projects to evaluate",
        _hp_names,
        default=st.session_state.get("hp_selected_names", []),
        key="hp_project_select",
        help="Select one or more projects. Their capacity requirements compete for the same work centers and materials.",
    )
    st.session_state["hp_selected_names"] = _hp_selected

    if not _hp_selected:
        st.info("Select one or more projects above to start the evaluation.")
        st.stop()

    _hp_sel_df = _hp_filtered[_hp_filtered["project_name"].isin(_hp_selected)].copy()

    # ---- Project cards ------------------------------------------------------
    section("Selected Projects", f"{len(_hp_selected)} project(s) \u00b7 competing for shared capacity")

    def _hp_field(label: str, value: str) -> str:
        return (
            f"<div style='padding:6px 10px;background:var(--bg-soft);border:1px solid var(--line);"
            f"border-radius:8px;min-width:0;'>"
            f"<div style='font-size:9px;color:var(--muted);font-weight:700;letter-spacing:0.8px;"
            f"text-transform:uppercase;margin-bottom:3px;'>{label}</div>"
            f"<div style='font-size:12px;color:var(--ink);font-weight:600;white-space:nowrap;"
            f"overflow:hidden;text-overflow:ellipsis;'>{value}</div>"
            f"</div>"
        )

    for _, _hp_row in _hp_sel_df.iterrows():
        _hc = st.columns([2.2, 1, 1.2, 0.9, 1])
        with _hc[0]:
            st.markdown(f"**{_hp_row['project_name']}**")
            st.caption(f"Owner: {_hp_row.get('owner', 'n/a')} \u00b7 {_hp_row.get('segment', 'n/a')}")
        _dl = str(_hp_row.get("requested_delivery", "n/a"))[:10]
        _ev = _hp_row.get("expected_value", 0)
        _ev_str = f"\u20ac{float(_ev):,.0f}" if pd.notna(_ev) else "n/a"
        _pr = _hp_row.get("probability_score", 0)
        _pr_str = f"{float(_pr):.0%}" if pd.notna(_pr) else "n/a"
        _tier = str(_hp_row.get("revenue_tier", "n/a"))
        with _hc[1]:
            st.markdown(_hp_field("Deadline", _dl), unsafe_allow_html=True)
        with _hc[2]:
            st.markdown(_hp_field("Expected \u20ac", _ev_str), unsafe_allow_html=True)
        with _hc[3]:
            st.markdown(_hp_field("Probability", _pr_str), unsafe_allow_html=True)
        with _hc[4]:
            st.markdown(_hp_field("Revenue Tier", _tier), unsafe_allow_html=True)
        st.markdown("<hr style='margin:8px 0;border-color:var(--line);'>", unsafe_allow_html=True)

    if len(_hp_selected) > 1:
        _hp_total_ev = _hp_sel_df["expected_value"].sum()
        st.info(
            f"\u26a0\ufe0f **{len(_hp_selected)} projects selected** — combined expected value "
            f"**\u20ac{_hp_total_ev:,.0f}**. They share finite capacity and materials. "
            "The simulation accounts for their combined load."
        )

    # ---- Lead time breakdown chart -----------------------------------------
    section("Lead Time Breakdown", "Sourcing \u00b7 Production \u00b7 Transit \u00b7 per selected project")
    ui.data_source_strip([
        ("real", "sourcing lead time (dim_procurement_logic)"),
        ("synthetic", "production proxy (14 days)"),
        ("real", "transit time (fact_delivery_commitment)"),
    ])

    def _build_lead_time_df(_sel: pd.DataFrame, _w7: dict) -> pd.DataFrame:
        _dc_path = Path("project/data/processed/fact_delivery_commitment_weekly.csv")
        _pl_path = Path("project/data/processed/dim_procurement_logic.csv")

        _dc = pd.read_csv(_dc_path) if _dc_path.exists() else pd.DataFrame()
        _pl = pd.read_csv(_pl_path) if _pl_path.exists() else pd.DataFrame()

        _default_sourcing    = float(_pl["lead_time_days"].mean()) if not _pl.empty else 34.0
        _default_production  = 14.0
        _default_transit     = float(_dc["transit_time_days"].mean()) if not _dc.empty and "transit_time_days" in _dc.columns else 3.0

        _rows = []
        for _, _r in _sel.iterrows():
            _pid = _r.get("project_id") if "project_id" in _r.index else None
            _is_custom = str(_r.get("source", "")) == "manual"

            # Sourcing
            if not _is_custom and _pid and not _pl.empty and "lead_time_days" in _pl.columns:
                _plant = _r.get("plant") if "plant" in _r.index else None
                if _plant:
                    _sub = _pl[_pl["plant"] == _plant]
                    _src = float(_sub["lead_time_days"].mean()) if not _sub.empty else _default_sourcing
                else:
                    _src = _default_sourcing
            else:
                _src = _default_sourcing

            # Production + transit
            if not _is_custom and _pid and not _dc.empty:
                _dc_proj = _dc[_dc["project_id"] == _pid]
                _prod = float(_dc_proj["production_time_proxy_days"].mean()) if not _dc_proj.empty and "production_time_proxy_days" in _dc_proj.columns else _default_production
                _tra  = float(_dc_proj["transit_time_days"].mean())           if not _dc_proj.empty and "transit_time_days" in _dc_proj.columns else _default_transit
            else:
                _prod = _default_production
                _tra  = _default_transit

            # Deadline days from today
            _dl_raw = _r.get("requested_delivery")
            try:
                _dl_days = float((pd.to_datetime(_dl_raw) - pd.Timestamp.today()).days)
                if _dl_days < 0:
                    _dl_days = None
            except Exception:
                _dl_days = None

            _rows.append({
                "project_name":    _r["project_name"],
                "sourcing_days":   _src,
                "production_days": _prod,
                "transit_days":    _tra,
                "deadline_days":   _dl_days,
            })
        return pd.DataFrame(_rows)

    _lt_df = _build_lead_time_df(_hp_sel_df, _load_w7())
    if not _lt_df.empty:
        st.plotly_chart(lead_time_breakdown_bar(_lt_df), use_container_width=True)

    # ---- Feasibility data (computed here, rendered after simulate) ----------
    _risk_path = Path("project/data/processed/fact_integrated_risk_v2.csv")
    _risk_df   = pd.read_csv(_risk_path) if _risk_path.exists() else pd.DataFrame()
    if not _risk_df.empty and "scenario" in _risk_df.columns:
        _risk_df = _risk_df[_risk_df["scenario"] == "expected_value"]

    def _mean_risk(_col: str) -> float | None:
        """Average score for selected projects; falls back to population mean when no match."""
        if _risk_df.empty or _col not in _risk_df.columns:
            return None
        _pids = _hp_sel_df["project_id"].dropna().tolist() if "project_id" in _hp_sel_df.columns else []
        if not _pids:
            return float(_risk_df[_col].mean())
        _sub = _risk_df[_risk_df["project_id"].isin(_pids)]
        return float(_sub[_col].mean()) if not _sub.empty else float(_risk_df[_col].mean())

    # capacity_risk_score / sourcing_risk_score: clustered near 1.0 in real data (plants are loaded)
    # Thresholds tuned to their actual range: < 0.70 feasible, 0.70–0.90 at risk, > 0.90 not feasible
    # logistics_risk_score: genuine spread 0.005–0.712; 0.35/0.65 thresholds work directly
    _cap_score = _mean_risk("capacity_risk_score")
    _src_score = _mean_risk("sourcing_risk_score")
    _log_score = _mean_risk("logistics_risk_score")
    _has_custom = ("source" in _hp_sel_df.columns and (_hp_sel_df["source"] == "manual").any())
    _has_fallback = not _risk_df.empty and (
        "project_id" not in _hp_sel_df.columns
        or _risk_df[_risk_df["project_id"].isin(
            _hp_sel_df["project_id"].dropna() if "project_id" in _hp_sel_df.columns else pd.Series(dtype=str)
        )].empty
    )

    def _emoji_for(score: float | None, lo: float = 0.35, hi: float = 0.65) -> tuple[str, str, str]:
        if score is None:
            return "\u2753", "Unknown", "#888888"
        if score < lo:
            return "\U0001F60A", "Feasible", "#2A9D8F"
        if score <= hi:
            return "\U0001F610", "At Risk", "#E07B39"
        return "\U0001F61F", "Not Feasible", "#C0392B"

    def _feasibility_card(icon_label: str, dimension: str, score: float | None,
                          lo: float = 0.35, hi: float = 0.65) -> str:
        _emoji, _status, _color = _emoji_for(score, lo, hi)
        _score_txt = f"{score:.2f}" if score is not None else "n/a"
        return (
            f"<div style='padding:18px 14px;background:var(--bg-soft);border:1px solid var(--line);"
            f"border-radius:12px;text-align:center;'>"
            f"<div style='font-size:36px;margin-bottom:6px;'>{_emoji}</div>"
            f"<div style='font-size:13px;font-weight:700;color:var(--ink);margin-bottom:2px;'>{icon_label}</div>"
            f"<div style='font-size:11px;color:var(--muted);margin-bottom:8px;'>{dimension}</div>"
            f"<div style='font-size:14px;font-weight:700;color:{_color};'>{_status}</div>"
            f"<div style='font-size:10px;color:var(--muted);margin-top:3px;'>score: {_score_txt}</div>"
            f"</div>"
        )

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ---- Action buttons -----------------------------------------------------
    _btn1, _btn2, _btn_spacer = st.columns([1, 1, 2])

    with _btn1:
        if st.button("\U0001F3B2 Simulate", use_container_width=True, type="primary", key="hp_btn_sim"):
            with st.spinner("Running Monte Carlo simulation (200 trials) \u2026"):
                _hp_results = []
                _rng = np.random.default_rng(42)
                for _, _r in _hp_sel_df.iterrows():
                    _prob = float(_r.get("probability_score", 0.5))
                    _ev   = float(_r.get("expected_value", 0))
                    _wins = _rng.binomial(1, _prob, 200)
                    _revs = _wins * _ev
                    _hp_results.append({
                        "Project":        _r["project_name"],
                        "Probability":    _prob,
                        "Expected \u20ac": _ev,
                        "P10 \u20ac":     float(np.percentile(_revs, 10)),
                        "P50 \u20ac":     float(np.percentile(_revs, 50)),
                        "P90 \u20ac":     float(np.percentile(_revs, 90)),
                        "Win Rate":       float(_wins.mean()),
                    })
                st.session_state["hp_sim_results"] = pd.DataFrame(_hp_results)
                st.session_state["hp_sim_done"]    = True
            st.success("Simulation complete!")

    with _btn2:
        if st.button("\U0001F680 Send to Production", use_container_width=True, type="secondary", key="hp_btn_prod"):
            if not st.session_state.get("hp_sim_done", False):
                _hp_no_sim_dialog()
            else:
                st.session_state["hp_sent_to_prod"] = True

    # ---- Simulation results -------------------------------------------------
    if st.session_state.get("hp_sim_done", False) and "hp_sim_results" in st.session_state:
        _mc = st.session_state["hp_sim_results"]
        section("Monte Carlo Results", "200 Bernoulli trials per project \u00b7 P10 / P50 / P90 revenue distribution")

        _mc_p50 = _mc["P50 \u20ac"].sum()
        _mc_p10 = _mc["P10 \u20ac"].sum()
        _mc_p90 = _mc["P90 \u20ac"].sum()
        _mp1, _mp2, _mp3, _mp4 = st.columns(4)
        with _mp1:
            kpi("P50 Revenue", f"\u20ac{_mc_p50:,.0f}", "Median outcome", "kpi-accent")
        with _mp2:
            kpi("P10 Revenue", f"\u20ac{_mc_p10:,.0f}", "Pessimistic outcome", "kpi-warn")
        with _mp3:
            kpi("P90 Revenue", f"\u20ac{_mc_p90:,.0f}", "Optimistic outcome", "kpi-ok")
        with _mp4:
            # Normalise each score into [0,1] using its own thresholds then average
            def _norm(v, lo, hi):
                if v is None: return None
                return max(0.0, min(1.0, (v - lo) / (hi - lo + 1e-9)))
            _ov_vals = [x for x in [
                _norm(_cap_score, 0.70, 0.90),
                _norm(_src_score, 0.70, 0.90),
                _norm(_log_score, 0.35, 0.65),
            ] if x is not None]
            _ov_mean  = sum(_ov_vals) / len(_ov_vals) if _ov_vals else None
            _ov_emoji, _ov_label, _ = _emoji_for(_ov_mean)
            kpi("Overall Feasibility", f"{_ov_emoji} {_ov_label}", "Capacity + Materials + Delivery", "kpi-info")

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        _mc_disp = _mc.copy()
        for _col in ["Expected \u20ac", "P10 \u20ac", "P50 \u20ac", "P90 \u20ac"]:
            _mc_disp[_col] = _mc_disp[_col].apply(lambda x: f"\u20ac{x:,.0f}")
        _mc_disp["Probability"] = _mc_disp["Probability"].apply(lambda x: f"{x:.0%}")
        _mc_disp = _mc_disp.drop(columns=["Win Rate"], errors="ignore")
        st.dataframe(_mc_disp, use_container_width=True, hide_index=True)

        # ---- Feasibility Check (rendered after simulate) --------------------
        section("Feasibility Check", "Machine Capacity \u00b7 Materials & Stock \u00b7 Delivery \u00b7 per selected portfolio")
        ui.data_source_strip([("real", "integrated_risk_v2 (capacity / sourcing / logistics risk scores)")])
        _feas_c1, _feas_c2, _feas_c3 = st.columns(3)
        with _feas_c1:
            st.markdown(_feasibility_card("\U0001F3ED Machine Capacity", "Work center load risk (< 0.70 ok, > 0.90 critical)", _cap_score, 0.70, 0.90), unsafe_allow_html=True)
        with _feas_c2:
            st.markdown(_feasibility_card("\U0001F4E6 Materials & Stock", "Sourcing shortage risk (< 0.70 ok, > 0.90 critical)", _src_score, 0.70, 0.90), unsafe_allow_html=True)
        with _feas_c3:
            st.markdown(_feasibility_card("\U0001F69A Delivery", "Logistics & on-time feasibility", _log_score, 0.35, 0.65), unsafe_allow_html=True)
        if _has_custom or _has_fallback:
            st.caption("\u26a0\ufe0f Some projects have no individual risk record \u2014 scores shown are portfolio averages from the full dataset.")

    # ---- Production confirmation --------------------------------------------
    if st.session_state.get("hp_sent_to_prod", False):
        _proj_list = ", ".join(_hp_selected)
        st.success(
            f"\u2705 **Order sent to production!** "
            f"Project(s) **{_proj_list}** have been queued for production planning."
        )
        st.balloons()
        st.session_state["hp_sent_to_prod"] = False


# =============================================================================
# PAGE: Add Project
# =============================================================================
elif page == "Add Project":
    page_header("Add Project", "Create a new opportunity and include it in Homepage simulations")

    _MATERIAL_TYPES = ["Plates", "Gaskets", "Refrigeration", "District Heating",
                       "Industrial", "Marine", "Oil & Gas", "Pharma",
                       "Food & Beverage", "Data Center"]
    _TIERS = ["Small", "Medium", "Large", "Strategic"]
    _REGIONS = ["EMEA-West", "EMEA-East", "APAC-South", "APAC-East", "LATAM"]

    with st.form("add_project_form", clear_on_submit=True):
        section("New Project Details")
        _fc1, _fc2 = st.columns(2)
        with _fc1:
            _f_name     = st.text_input("Project Name *", placeholder="e.g. PRJ-ALPHA-0999")
            _f_material = st.selectbox("Material Type *", _MATERIAL_TYPES)
            _f_region   = st.selectbox("Region", _REGIONS, index=0)
        with _fc2:
            _f_amount   = st.number_input("Amount (\u20ac) *", min_value=0.0, step=10_000.0, format="%.0f")
            _f_date     = st.date_input("Delivery Date *")
            _f_tier     = st.selectbox("Tier *", _TIERS, index=1)

        _f_prob = st.slider(
            "Win Probability (%)",
            min_value=10, max_value=90, value=50, step=5,
            help="Estimated likelihood this opportunity converts to an order",
        )

        _submitted = st.form_submit_button("\u2795 Add Project", type="primary", use_container_width=True)

    if _submitted:
        if not _f_name.strip():
            st.error("Project name is required.")
        elif _f_amount <= 0:
            st.error("Amount must be greater than 0.")
        else:
            _prob_frac = _f_prob / 100
            _new_proj = {
                "project_name":       _f_name.strip(),
                "region":             _f_region,
                "segment":            _f_material,
                "requested_delivery": str(_f_date),
                "project_value":      _f_amount,
                "expected_value":     _f_amount * _prob_frac,
                "probability_score":  _prob_frac,
                "revenue_tier":       _f_tier,
                "owner":              "Manual entry",
                "priority_band":      "medium",
                "source":             "manual",
            }
            if "hp_custom_projects" not in st.session_state:
                st.session_state["hp_custom_projects"] = []
            st.session_state["hp_custom_projects"].append(_new_proj)
            st.success(
                f"\u2705 **{_f_name.strip()}** added to the pipeline. "
                "Go to **Homepage** to select it and run a simulation."
            )

    # ---- Show existing custom projects --------------------------------------
    _custom = st.session_state.get("hp_custom_projects", [])
    if _custom:
        section("Custom Projects Added This Session", f"{len(_custom)} project(s)")
        _custom_df = pd.DataFrame(_custom)[
            ["project_name", "region", "segment", "requested_delivery",
             "project_value", "probability_score", "revenue_tier"]
        ].copy()
        _custom_df.columns = ["Name", "Region", "Material", "Deadline", "Amount \u20ac", "Probability", "Tier"]
        _custom_df["Amount \u20ac"]  = _custom_df["Amount \u20ac"].apply(lambda x: f"\u20ac{x:,.0f}")
        _custom_df["Probability"] = _custom_df["Probability"].apply(lambda x: f"{x:.0%}")
        st.dataframe(_custom_df, use_container_width=True, hide_index=True)

        if st.button("\U0001F5D1\ufe0f  Clear all custom projects", type="secondary"):
            st.session_state["hp_custom_projects"] = []
            st.rerun()


# =============================================================================
# GENERAL DATA — Quarterly Business Summary
# =============================================================================
elif page == "General Data":
    page_header("General Data", "Quarterly business summary \u00b7 Projects \u00b7 Revenue \u00b7 Delivery Health")

    _gd_pa_path = Path("project/data/processed/fact_planner_actions_v2.csv")
    _gd_rv_path = Path("project/data/processed/fact_integrated_risk_v2.csv")
    _gd_pp_path = Path("project/data/processed/dim_project_priority.csv")

    _gd_pa = pd.read_csv(_gd_pa_path) if _gd_pa_path.exists() else pd.DataFrame()
    _gd_rv = pd.read_csv(_gd_rv_path) if _gd_rv_path.exists() else pd.DataFrame()
    _gd_pp = pd.read_csv(_gd_pp_path) if _gd_pp_path.exists() else pd.DataFrame()

    if not _gd_pa.empty and "scenario" in _gd_pa.columns:
        _gd_pa = _gd_pa[_gd_pa["scenario"] == "expected_value"]
    if not _gd_rv.empty and "scenario" in _gd_rv.columns:
        _gd_rv = _gd_rv[_gd_rv["scenario"] == "expected_value"]

    # Year selector
    _gd_years = sorted({q[:4] for q in _gd_pa["quarter_id"].unique()}) if not _gd_pa.empty else ["2026"]
    _gd_year  = st.radio("Year", _gd_years, horizontal=True, key="gd_year")
    _gd_qs    = [f"{_gd_year}-Q1", f"{_gd_year}-Q2", f"{_gd_year}-Q3", f"{_gd_year}-Q4"]

    # Build per-quarter summary
    _gd_rows = []
    for _q in _gd_qs:
        _pa_q  = _gd_pa[_gd_pa["quarter_id"] == _q] if not _gd_pa.empty else pd.DataFrame()
        _rv_q  = _gd_rv[_gd_rv["quarter_id"] == _q] if not _gd_rv.empty else pd.DataFrame()
        _pids  = _pa_q["project_id"].dropna().unique().tolist() if not _pa_q.empty else []
        _n_proj = len(_pids)
        _rev   = float(_gd_pp[_gd_pp["project_id"].isin(_pids)]["expected_value"].sum()) if not _gd_pp.empty and _pids else 0.0
        _log   = float(_rv_q["logistics_risk_score"].mean()) if not _rv_q.empty and "logistics_risk_score" in _rv_q.columns else None
        _cap   = float(_rv_q["capacity_risk_score"].mean())  if not _rv_q.empty and "capacity_risk_score"  in _rv_q.columns else None
        _delivery_health = round((1.0 - _log) * 100, 1) if _log is not None else None
        _gd_rows.append({"Quarter": _q, "Projects": _n_proj, "Revenue": _rev,
                         "Delivery Health %": _delivery_health, "Capacity Risk": _cap})
    _gd_df = pd.DataFrame(_gd_rows)

    # ---- KPI cards (one per quarter) ----------------------------------------
    section("Quarterly Snapshot", f"{_gd_year} \u00b7 Q1 through Q4")
    _kc = st.columns(4)
    for _i, (_q_label, (_, _row)) in enumerate(zip(["Q1", "Q2", "Q3", "Q4"], _gd_df.iterrows())):
        with _kc[_i]:
            _rev_str = f"\u20ac{_row['Revenue']/1e6:.1f}M" if _row['Revenue'] > 0 else "n/a"
            _dh_val  = _row["Delivery Health %"]
            _dh_str  = f"{_dh_val:.1f}%" if _dh_val is not None else "n/a"
            st.markdown(
                f"<div style='padding:16px 12px;background:var(--bg-soft);border:1px solid var(--line);"
                f"border-radius:12px;text-align:center;'>"
                f"<div style='font-size:11px;color:var(--muted);font-weight:700;letter-spacing:1px;"
                f"text-transform:uppercase;margin-bottom:8px;'>{_q_label}</div>"
                f"<div style='font-size:22px;font-weight:800;color:var(--accent);'>{_row['Projects']}</div>"
                f"<div style='font-size:10px;color:var(--muted);'>projects</div>"
                f"<div style='font-size:14px;font-weight:700;color:var(--ink);margin-top:8px;'>{_rev_str}</div>"
                f"<div style='font-size:10px;color:var(--muted);'>expected revenue</div>"
                f"<div style='font-size:13px;font-weight:600;color:#2A9D8F;margin-top:8px;'>{_dh_str}</div>"
                f"<div style='font-size:10px;color:var(--muted);'>delivery health</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ---- Charts -------------------------------------------------------------
    import plotly.graph_objects as _go_gd
    _ch1, _ch2 = st.columns(2)

    with _ch1:
        section("Active Projects per Quarter", "Unique projects with planner actions")
        _fig_proj = _go_gd.Figure(_go_gd.Bar(
            x=_gd_df["Quarter"], y=_gd_df["Projects"],
            marker_color=ACCENT, text=_gd_df["Projects"], textposition="outside",
        ))
        _fig_proj.update_layout(
            height=280, margin=dict(t=20, b=20, l=0, r=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor=LINE, zeroline=False),
            xaxis=dict(showgrid=False), font=dict(family="Inter", size=12),
            showlegend=False,
        )
        st.plotly_chart(_fig_proj, use_container_width=True)

    with _ch2:
        section("Delivery Health vs Capacity Risk", "Higher delivery health = better \u00b7 Lower capacity risk = better")
        _fig_risk = _go_gd.Figure()
        _fig_risk.add_trace(_go_gd.Scatter(
            x=_gd_df["Quarter"], y=_gd_df["Delivery Health %"],
            name="Delivery Health %", mode="lines+markers",
            line=dict(color="#2A9D8F", width=2), marker=dict(size=8),
        ))
        _fig_risk.add_trace(_go_gd.Scatter(
            x=_gd_df["Quarter"], y=(_gd_df["Capacity Risk"].fillna(0) * 100).round(1),
            name="Capacity Risk %", mode="lines+markers",
            line=dict(color="#C0392B", width=2, dash="dot"), marker=dict(size=8),
        ))
        _fig_risk.update_layout(
            height=280, margin=dict(t=20, b=20, l=0, r=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor=LINE, zeroline=False, range=[0, 110]),
            xaxis=dict(showgrid=False), font=dict(family="Inter", size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(_fig_risk, use_container_width=True)

    ui.data_source_strip([
        ("real", "fact_planner_actions_v2 (projects)"),
        ("real", "dim_project_priority (revenue)"),
        ("real", "fact_integrated_risk_v2 (delivery health / capacity risk)"),
    ])


# =============================================================================
# MACHINERY — Overview of machines, work centers, downtime
# =============================================================================
elif page == "Machinery":
    import plotly.graph_objects as _go_mach
    page_header("Machinery", "Work centers \u00b7 Tools \u00b7 Downtime \u00b7 Plant locations")

    _mwc_path   = Path("project/data/processed/bridge_material_tool_wc.csv")
    _mim_path   = Path("project/data/processed/fact_maintenance_impact_summary.csv")
    _mpol_path  = Path("project/data/processed/dim_maintenance_policy_synth.csv")
    _mbot_path  = Path("project/data/processed/fact_capacity_bottleneck_summary.csv")

    _mwc  = pd.read_csv(_mwc_path)  if _mwc_path.exists()  else pd.DataFrame()
    _mim  = pd.read_csv(_mim_path)  if _mim_path.exists()  else pd.DataFrame()
    _mpol = pd.read_csv(_mpol_path) if _mpol_path.exists() else pd.DataFrame()
    _mbot = pd.read_csv(_mbot_path) if _mbot_path.exists() else pd.DataFrame()

    # ---- KPI strip ----------------------------------------------------------
    _n_plants = int(_mwc["plant"].nunique())   if not _mwc.empty else 0
    _n_wcs    = int(_mwc["work_center"].nunique()) if not _mwc.empty else 0
    _n_tools  = int(_mwc["tool"].nunique())    if not _mwc.empty else 0
    _avg_dt   = float(_mim["pct_capacity_lost_to_maintenance"].mean() * 100) if not _mim.empty and "pct_capacity_lost_to_maintenance" in _mim.columns else 0.0
    _n_crit   = int((_mbot["bottleneck_severity"] == "critical").sum()) if not _mbot.empty and "bottleneck_severity" in _mbot.columns else 0

    _mk1, _mk2, _mk3, _mk4, _mk5 = st.columns(5)
    with _mk1: kpi("Plants", str(_n_plants), "Active manufacturing sites", "kpi-accent")
    with _mk2: kpi("Work Centers", str(_n_wcs), "Unique WC codes", "kpi-info")
    with _mk3: kpi("Tools", str(_n_tools), "Unique tool numbers", "kpi-info")
    with _mk4: kpi("Avg Downtime", f"{_avg_dt:.1f}%", "Capacity lost to maintenance", "kpi-warn")
    with _mk5: kpi("Critical WCs", str(_n_crit), "Bottleneck severity: critical", "kpi-danger" if _n_crit else "kpi-ok")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ---- Charts row ---------------------------------------------------------
    _mc1, _mc2 = st.columns(2)

    with _mc1:
        section("Work Centers per Plant", "Number of active WCs at each plant")
        if not _mwc.empty:
            _wc_cnt = _mwc.groupby("plant")["work_center"].nunique().sort_values(ascending=True).reset_index()
            _wc_cnt.columns = ["Plant", "WCs"]
            _fig_wc = _go_mach.Figure(_go_mach.Bar(
                y=_wc_cnt["Plant"], x=_wc_cnt["WCs"],
                orientation="h", marker_color=ACCENT,
                text=_wc_cnt["WCs"], textposition="outside",
            ))
            _fig_wc.update_layout(
                height=340, margin=dict(t=10, b=10, l=0, r=30),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=True, gridcolor=LINE),
                yaxis=dict(showgrid=False),
                font=dict(family="Inter", size=12), showlegend=False,
            )
            st.plotly_chart(_fig_wc, use_container_width=True)

    with _mc2:
        section("Capacity Lost to Maintenance", "% of nominal capacity consumed by scheduled downtime")
        if not _mim.empty and "pct_capacity_lost_to_maintenance" in _mim.columns:
            _mim_plant = (_mim.groupby("plant")["pct_capacity_lost_to_maintenance"]
                         .mean().mul(100).round(1).sort_values(ascending=True).reset_index())
            _mim_plant.columns = ["Plant", "Downtime %"]
            _colors = ["#C0392B" if v > 10 else "#E07B39" if v > 5 else "#2A9D8F"
                       for v in _mim_plant["Downtime %"]]
            _fig_dt = _go_mach.Figure(_go_mach.Bar(
                y=_mim_plant["Plant"], x=_mim_plant["Downtime %"],
                orientation="h", marker_color=_colors,
                text=_mim_plant["Downtime %"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside",
            ))
            _fig_dt.update_layout(
                height=340, margin=dict(t=10, b=10, l=0, r=50),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=True, gridcolor=LINE),
                yaxis=dict(showgrid=False),
                font=dict(family="Inter", size=12), showlegend=False,
            )
            st.plotly_chart(_fig_dt, use_container_width=True)

    # ---- Downtime policy table ----------------------------------------------
    section("Maintenance Schedule", "Policy per work center \u00b7 trigger type \u00b7 interval \u00b7 expected downtime")
    if not _mpol.empty:
        _pol_disp = _mpol[["plant", "work_center", "maintenance_trigger_type",
                            "estimated_interval_weeks_synth", "expected_downtime_hours_synth"]].copy()
        _pol_disp.columns = ["Plant", "Work Center", "Trigger Type", "Interval (weeks)", "Downtime (hrs)"]
        _pol_disp = _pol_disp.sort_values("Downtime (hrs)", ascending=False).reset_index(drop=True)
        st.dataframe(_pol_disp, use_container_width=True, hide_index=True)

    ui.data_source_strip([
        ("real", "bridge_material_tool_wc (WC / tool counts)"),
        ("synthetic", "dim_maintenance_policy (downtime schedule)"),
        ("real", "fact_maintenance_impact_summary (capacity lost)"),
    ])


# =============================================================================
# PAGE 0 - One-Click Plan (full automation pipeline in one view)
# =============================================================================
elif page == "One-Click Plan":
    page_header("One-Click Plan",
                "Every scenario \u00b7 every bottleneck \u00b7 every action \u2014 in one view")

    st.markdown(
        "<div style='background:linear-gradient(135deg, rgba(187,39,39,0.10), rgba(56,189,248,0.06)); "
        "border:1px solid rgba(187,39,39,0.30); border-left:4px solid var(--accent-brand); "
        "border-radius:10px; padding:14px 18px; margin-bottom:18px;'>"
        "<div style='font-size:11px; color:var(--accent-soft); letter-spacing:1.6px; "
        "text-transform:uppercase; font-weight:700;'>For business stakeholders</div>"
        "<div style='font-size:15px; color:var(--ink); margin-top:4px; line-height:1.5;'>"
        "Click <b>Run full plan</b> to compute the entire pipeline in one go: capacity utilization, "
        "bottleneck ranking, sourcing risk, planner actions, and quarter-over-quarter signals \u2014 "
        "all tailored to <b style='color:#FFFFFF;'>"
        f"{w7_region}</b> for <b style='color:#FFFFFF;'>{w7_quarter or 'all quarters'}</b>."
        "</div></div>",
        unsafe_allow_html=True,
    )

    rcol1, rcol2 = st.columns([3, 1])
    with rcol1:
        st.markdown(
            "<div style='font-size:13px; color:var(--ink-soft); padding:8px 0;'>"
            "<b style='color:var(--ink);'>What runs:</b> "
            "all 4 scenarios \u00b7 109 work centers \u00b7 9.5k BOM lines \u00b7 156-week horizon"
            "</div>",
            unsafe_allow_html=True,
        )
    with rcol2:
        run_clicked = st.button("\U0001F680  Run full plan", type="primary",
                                use_container_width=True, key="oneclick_run")

    if run_clicked or st.session_state.get("oneclick_done"):
        st.session_state["oneclick_done"] = True

        with st.spinner("Running full pipeline across all scenarios..."):
            util_b   = get_utilization(scenario, plant)
            bot_b    = get_bottlenecks(scenario, plant)
            src_b    = get_sourcing(scenario, plant, top_n=20)
            w7_data  = _load_w7()

        # ===== Headline KPIs =====
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Headline numbers", f"Snapshot for {w7_region} \u00b7 {w7_quarter or 'all quarters'}")

        pipe_df = data.fact_pipeline_monthly
        if plant:
            pipe_df = pipe_df[pipe_df["plant"] == plant]

        total_eur    = float(data.dim_project["total_eur"].fillna(0).sum())
        expected_eur = float((data.dim_project["total_eur"].fillna(0) *
                              data.dim_project["probability_frac"].fillna(0)).sum())
        peak_u       = float(util_b["utilization"].max()) if not util_b.empty else 0.0
        n_bot_view   = int(len(bot_b)) if not bot_b.empty else 0
        n_short      = int(len(src_b)) if src_b is not None and not src_b.empty else 0

        acts_v2 = w7_data.get("planner_actions_v2", pd.DataFrame())
        risk_v2 = w7_data.get("integrated_risk_v2", pd.DataFrame())
        n_actions = int(len(_w7_filter(acts_v2, scenario))) if not acts_v2.empty else int(len(acts_v2))
        avg_risk  = float(risk_v2["risk_score_v2"].mean()) if not risk_v2.empty and "risk_score_v2" in risk_v2.columns else 0.0

        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi("EXPECTED PIPELINE", f"\u20AC{expected_eur/1e6:.1f}M",
                     f"of \u20AC{total_eur/1e6:.1f}M total", "kpi-ok")
        with k2:
            style = "kpi-accent" if peak_u >= 1 else "kpi-warn" if peak_u >= 0.85 else "kpi-ok"
            kpi("PEAK UTILIZATION", f"{peak_u:.0%}", f"{SCENARIOS[scenario]['label']} scenario", style)
        with k3: kpi("BOTTLENECKS", f"{n_bot_view}", "WCs \u2265 85%",
                     "kpi-warn" if n_bot_view else "kpi-ok")
        with k4: kpi("SOURCING ALERTS", f"{n_short}", "components needing PO",
                     "kpi-accent" if n_short else "kpi-ok")

        k5, k6, k7, k8 = st.columns(4)
        with k5: kpi("PLANNER ACTIONS", f"{n_actions}", f"scenario: {scenario}", "kpi-slate")
        with k6: kpi("AVG RISK SCORE", f"{avg_risk:.2f}", "integrated risk v2",
                     "kpi-warn" if avg_risk >= 0.5 else "kpi-ok")
        with k7: kpi("PROJECTS", f"{int(data.dim_project.shape[0])}",
                     f"{int(pipe_df['plant'].nunique())} plants in view", "kpi-slate")
        with k8: kpi("HORIZON", f"{N_MONTHS}", "monthly buckets", "kpi-info")

        # ===== Quick export bar (always visible after Run) =====
        st.markdown(
            "<div style='background:linear-gradient(90deg, rgba(187,39,39,0.12), rgba(187,39,39,0.02)); "
            "border:1px solid rgba(187,39,39,0.30); border-left:3px solid var(--accent-brand); "
            "border-radius:10px; padding:10px 16px; margin-top:14px; "
            "display:flex; align-items:center; gap:10px;'>"
            "<span style='font-size:13px; color:var(--ink); font-weight:600;'>"
            "\U0001F4E5  Export this plan</span>"
            "<span style='flex:1;'></span>"
            "<span style='font-size:11px; color:var(--muted); font-style:italic;'>"
            "Branded PDF \u00b7 Excel workbook \u00b7 Markdown</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        _qe1, _qe2, _qe3 = st.columns(3)
        try:
            _scen_rows_quick = []
            for _sc in SCENARIOS:
                _u = get_utilization(_sc, plant)
                _scen_rows_quick.append({
                    "scenario": _sc, "label": SCENARIOS[_sc]["label"],
                    "peak_util": float(_u["utilization"].max()) if not _u.empty else 0,
                    "weeks_critical": int((_u["utilization"] >= 1.0).sum()) if not _u.empty else 0,
                    "total_demand_hours": float(_u["demand_hours"].sum()) if not _u.empty else 0,
                })
            _pdf_bytes = build_plan_pdf(
                region=w7_region, quarter=w7_quarter,
                scenario_label=SCENARIOS[scenario]['label'], plant_filter=plant or "All plants",
                kpis={
                    "Expected pipeline": f"EUR {expected_eur/1e6:.1f}M of {total_eur/1e6:.1f}M",
                    "Peak utilization":  f"{peak_u:.0%}",
                    "Bottlenecks (>=85%)": f"{n_bot_view}",
                    "Sourcing alerts":   f"{n_short}",
                    "Planner actions":   f"{n_actions}",
                    "Avg risk score":    f"{avg_risk:.3f}",
                },
                bottlenecks=bot_b.head(5) if not bot_b.empty else pd.DataFrame(),
                sourcing=src_b.head(5) if src_b is not None and not src_b.empty else pd.DataFrame(),
                scenarios=pd.DataFrame(_scen_rows_quick),
            )
            with _qe1:
                st.download_button(
                    "\U0001F4D1  PDF report", data=_pdf_bytes,
                    file_name=f"clarix_plan_{w7_region.replace(' ', '_')}_{w7_quarter or 'all'}_{scenario}.pdf",
                    mime="application/pdf", use_container_width=True, type="primary",
                    key="qexport_pdf",
                )
            import io as _io
            _xb = _io.BytesIO()
            with pd.ExcelWriter(_xb, engine="openpyxl") as _xw:
                (bot_b.head(50).to_excel(_xw, sheet_name="bottlenecks", index=False)
                    if not bot_b.empty else pd.DataFrame().to_excel(_xw, sheet_name="bottlenecks"))
                (src_b.head(50).to_excel(_xw, sheet_name="sourcing", index=False)
                    if src_b is not None and not src_b.empty
                    else pd.DataFrame().to_excel(_xw, sheet_name="sourcing"))
                pd.DataFrame(_scen_rows_quick).to_excel(_xw, sheet_name="scenario_summary", index=False)
            with _qe2:
                st.download_button(
                    "\U0001F4CA  Excel workbook", data=_xb.getvalue(),
                    file_name=f"clarix_plan_{w7_region.replace(' ', '_')}_{w7_quarter or 'all'}_{scenario}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, key="qexport_xlsx",
                )
            with _qe3:
                _md_quick = (
                    f"# Clarix Plan\n\n**Region:** {w7_region}  \n**Quarter:** {w7_quarter or 'all'}  \n"
                    f"**Scenario:** {SCENARIOS[scenario]['label']}  \n**Plant:** {plant or 'All plants'}\n\n"
                    f"## KPIs\n- Expected pipeline: EUR {expected_eur/1e6:.1f}M of {total_eur/1e6:.1f}M\n"
                    f"- Peak utilization: {peak_u:.0%}\n- Bottlenecks: {n_bot_view}\n"
                    f"- Sourcing alerts: {n_short}\n- Planner actions: {n_actions}\n"
                    f"- Avg risk: {avg_risk:.3f}\n"
                )
                st.download_button(
                    "\U0001F4C4  Markdown", data=_md_quick,
                    file_name=f"clarix_plan_{w7_region.replace(' ', '_')}_{w7_quarter or 'all'}_{scenario}.md",
                    mime="text/markdown", use_container_width=True, key="qexport_md",
                )
        except Exception as _qe_err:
            st.caption(f"Export unavailable: {_qe_err}")

        # ===== Scenario sweep =====
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Scenario sweep", "All scenarios at a glance \u2014 act on the worst-case row")
        sw_rows = []
        for sc in SCENARIOS:
            u_s = get_utilization(sc, plant)
            b_s = get_bottlenecks(sc, plant)
            sw_rows.append({
                "Scenario": SCENARIOS[sc]["label"],
                "Peak util %": f"{(float(u_s['utilization'].max()) if not u_s.empty else 0)*100:.0f}%",
                "Critical week-WCs": int((u_s["utilization"] >= 1).sum()) if not u_s.empty else 0,
                "Bottlenecks": int(len(b_s)) if not b_s.empty else 0,
                "Total demand h": f"{float(u_s['demand_hours'].sum()) if not u_s.empty else 0:,.0f}",
            })
        st.dataframe(pd.DataFrame(sw_rows), use_container_width=True, hide_index=True)

        # ===== Top bottlenecks + top sourcing =====
        st.markdown("<hr/>", unsafe_allow_html=True)
        cb1, cb2 = st.columns(2)
        with cb1:
            section("Top 5 bottlenecks", "Where capacity is tightest under base scenario")
            if not bot_b.empty:
                top_b = bot_b.head(5).copy()
                top_b["peak_util"] = (top_b["peak_util"] * 100).round(0)
                disp = top_b[["work_center", "plant", "peak_util", "weeks_crit", "total_overload_hours"]].rename(
                    columns={"work_center": "WC", "plant": "Plant",
                             "peak_util": "Peak %", "weeks_crit": "Crit wks",
                             "total_overload_hours": "Overload h"})
                disp["Overload h"] = disp["Overload h"].round(0)
                st.dataframe(disp, use_container_width=True, hide_index=True)
            else:
                st.success("No bottlenecks under base scenario.")

        with cb2:
            section("Top 5 sourcing actions", "Components needing PO soonest")
            if src_b is not None and not src_b.empty:
                top_s = src_b.head(5).copy()
                disp_s_cols = [c for c in ["component_material", "plant", "shortfall", "order_by"]
                               if c in top_s.columns]
                if disp_s_cols:
                    disp_s = top_s[disp_s_cols].rename(columns={
                        "component_material": "Material", "plant": "Plant",
                        "shortfall": "Shortfall", "order_by": "Order by"})
                    if "Shortfall" in disp_s.columns:
                        disp_s["Shortfall"] = disp_s["Shortfall"].round(0)
                    st.dataframe(disp_s, use_container_width=True, hide_index=True)
            else:
                st.success("No component shortfalls.")

        # ===== Top planner actions =====
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Top 5 planner actions",
                "AI-ranked recommendations (expedite / reschedule / source switch) for the active scenario")
        if not acts_v2.empty and "action_score" in acts_v2.columns:
            act_view = _w7_filter(acts_v2, scenario)
            top_acts = act_view.sort_values("action_score", ascending=False).head(5)
            for _, r in top_acts.iterrows():
                score = float(r.get("action_score", 0))
                conf  = float(r.get("confidence", 0))
                pill  = "pill-ok" if conf >= 0.7 else "pill-warn"
                st.markdown(
                    f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                    f"border-left:3px solid var(--accent-brand); "
                    f"padding:12px 16px; border-radius:8px; margin-bottom:8px; font-size:13px;'>"
                    f"<div style='display:flex; align-items:center; gap:10px; flex-wrap:wrap;'>"
                    f"<b style='color:var(--accent-brand); font-size:14px;'>{r.get('action_type', _DASH)}</b>"
                    f"<span style='color:var(--ink); font-weight:600;'>{r.get('project_id', _DASH)}</span>"
                    f"<span style='color:var(--muted);'>@ {r.get('plant', _DASH)}</span>"
                    f"<span class='pill {pill}'>conf {conf:.2f}</span>"
                    f"<span style='color:var(--muted); font-size:12px;'>score {score:.3f}</span>"
                    f"</div>"
                    f"<div style='font-size:12px; color:var(--ink-soft); margin-top:6px;'>"
                    f"{str(r.get('reason', ''))[:160]}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Planner actions not available \u2014 run the Wave 7 pipeline.")

        # ===== Pipeline + scenario charts =====
        st.markdown("<hr/>", unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            section("Pipeline funnel", "All-in vs expected-value")
            st.plotly_chart(pipeline_funnel(pipe_df), use_container_width=True)
        with cc2:
            section("Scenario comparison", "Peak utilization across scenarios")
            comp_rows = [{
                "scenario": sc, "label": SCENARIOS[sc]["label"],
                "peak_util": float(get_utilization(sc, plant)["utilization"].max()) if not get_utilization(sc, plant).empty else 0,
                "weeks_critical": int((get_utilization(sc, plant)["utilization"] >= 1.0).sum()) if not get_utilization(sc, plant).empty else 0,
                "total_demand_hours": float(get_utilization(sc, plant)["demand_hours"].sum()) if not get_utilization(sc, plant).empty else 0,
            } for sc in SCENARIOS]
            st.plotly_chart(scenario_compare_bar(comp_rows), use_container_width=True)

        section("Demand mix", "Where the expected pipeline is concentrated")
        st.plotly_chart(plant_demand_treemap(pipe_df), use_container_width=True)

        # ===== Quarter signals =====
        smem_df = w7_data.get("service_memory", pd.DataFrame())
        if not smem_df.empty and w7_quarter and w7_quarter != "carry-over":
            st.markdown("<hr/>", unsafe_allow_html=True)
            section(f"Quarter signals \u2014 {w7_quarter}",
                    "Carry-over caution + violation risk for this quarter")
            smem_q = smem_df[smem_df["quarter_id"] == w7_quarter] if "quarter_id" in smem_df.columns else smem_df
            if not smem_q.empty:
                qa, qb, qc = st.columns(3)
                caution_cnt = int(smem_q["carry_over_service_caution_flag"].sum()) if "carry_over_service_caution_flag" in smem_q.columns else 0
                avg_v_risk  = float(smem_q["prior_service_violation_risk"].mean()) if "prior_service_violation_risk" in smem_q.columns else 0.0
                n_proj_q    = int(smem_q["project_id"].nunique()) if "project_id" in smem_q.columns else 0
                with qa: kpi("PROJECTS TRACKED", f"{n_proj_q}", w7_quarter, "kpi-slate")
                with qb: kpi("CARRY-OVER CAUTION", f"{caution_cnt}", "flagged",
                             "kpi-warn" if caution_cnt else "kpi-ok")
                with qc: kpi("AVG VIOLATION RISK", f"{avg_v_risk:.2f}", "0=clean, 1=critical",
                             "kpi-accent" if avg_v_risk > 0.4 else "kpi-warn" if avg_v_risk > 0.2 else "kpi-ok")

        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown(
            "<div style='background:var(--bg-soft); border:1px solid var(--line); border-radius:10px; "
            "padding:18px 22px; font-size:13px; color:var(--ink-soft); line-height:1.7;'>"
            "<b style='color:var(--ink); font-size:14px;'>Next steps</b><br>"
            "Use the sidebar to drill into <b>Capacity &amp; Maintenance</b>, "
            "<b>Sourcing &amp; Delivery</b>, or <b>Final Actions</b> for full detail. "
            "Use <b>What-if planner</b> to test new projects against the live capacity model. "
            "Use <b>Ask Clarix</b> for natural-language questions."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Click \u2018Run full plan\u2019 above to compute the full snapshot in one shot.")


# =============================================================================
# PAGE 1 - Executive overview
# =============================================================================
elif page == "Executive overview":
    page_header("Executive overview",
                f"Scenario: {SCENARIOS[scenario]['label']} \u00b7 Plant: {plant or 'All'} \u00b7 {HORIZON} ({N_MONTHS} months)")

    ui.data_source_strip([
        ("real", "fact_pipeline_monthly"),
        ("real", "fact_pipeline_quarterly"),
        ("real", "fact_planner_actions_v2"),
        ("real", "fact_integrated_risk_v2"),
    ])

    pipe = data.fact_pipeline_monthly
    if plant:
        pipe = pipe[pipe["plant"] == plant]

    util = get_utilization(scenario, plant)
    bot = get_bottlenecks(scenario, plant)

    total_pipeline_eur = float(data.dim_project["total_eur"].fillna(0).sum())
    expected_pipeline_eur = float(
        (data.dim_project["total_eur"].fillna(0) * data.dim_project["probability_frac"].fillna(0)).sum()
    )
    n_projects = int(data.dim_project.shape[0])
    n_plants_view = int(pipe["plant"].nunique())
    peak_util = float(util["utilization"].max()) if not util.empty else 0.0
    n_critical_wks = int((util["utilization"] >= 1.0).sum()) if not util.empty else 0
    n_bot = int(bot.shape[0]) if not bot.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("PIPELINE VALUE (ALL-IN)", f"\u20AC{total_pipeline_eur/1e6:,.1f}M",
                 f"{n_projects} projects \u00b7 {n_plants_view} plants in view", "kpi-accent")
    with c2: kpi("EXPECTED VALUE", f"\u20AC{expected_pipeline_eur/1e6:,.1f}M",
                 "qty \u00d7 probability", "kpi-ok")
    with c3:
        style = "kpi-warn" if peak_util >= 0.85 else "kpi-ok"
        if peak_util >= 1.0: style = "kpi-accent"
        kpi("PEAK UTILIZATION", f"{peak_util:.0%}",
            f"{n_critical_wks:,} critical week-WC pairs", style)
    with c4: kpi("BOTTLENECK WORK CENTERS", f"{n_bot}",
                 "\u226585% util in any week", "kpi-warn" if n_bot else "kpi-ok")

    # --- Wave 7 intelligence layer ---
    if _DEMO_LAYER_AVAILABLE:
        w7 = _load_w7()
        acts_v2   = w7.get("planner_actions_v2", pd.DataFrame())
        risk_v2   = w7.get("integrated_risk_v2", pd.DataFrame())
        pq        = w7.get("pipeline_quarterly", pd.DataFrame())

        act_sc  = _w7_filter(acts_v2, scenario)
        risk_sc = _w7_filter(risk_v2, scenario)

        n_actions  = int(len(act_sc))
        high_conf  = int((act_sc["confidence"] >= 0.7).sum()) if "confidence" in act_sc.columns and n_actions > 0 else 0
        avg_risk   = float(risk_sc["risk_score_v2"].mean()) if not risk_sc.empty and "risk_score_v2" in risk_sc.columns else 0.0
        n_high_risk = int((risk_sc["risk_score_v2"] >= 0.7).sum()) if not risk_sc.empty and "risk_score_v2" in risk_sc.columns else 0

        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Wave 7 Intelligence Layer", "Planner actions \u00b7 integrated risk \u00b7 priority-weighted pipeline")

        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi("PLANNER ACTIONS", f"{n_actions:,}", f"scenario: {scenario}", "kpi-slate")
        with c2: kpi("HIGH-CONFIDENCE", f"{high_conf:,}", "confidence \u2265 0.7", "kpi-accent" if high_conf else "kpi-ok")
        with c3: kpi("AVG RISK SCORE", f"{avg_risk:.2f}", "integrated risk v2",
                     "kpi-warn" if avg_risk >= 0.5 else "kpi-ok")
        with c4: kpi("HIGH-RISK ROWS", f"{n_high_risk:,}", "risk score v2 \u2265 0.7",
                     "kpi-accent" if n_high_risk > 50 else "kpi-warn" if n_high_risk > 0 else "kpi-ok")

        # --- Top bottleneck + top recommendation side-by-side ---
        st.markdown("<hr/>", unsafe_allow_html=True)
        col_bot, col_act = st.columns(2)

        with col_bot:
            section("Top Bottleneck Projects", "Highest integrated risk score \u00b7 act before it becomes a shortage")
            if not risk_sc.empty and "risk_score_v2" in risk_sc.columns and "project_id" in risk_sc.columns:
                top_risk = (
                    risk_sc.groupby(["project_id", "plant"], as_index=False)
                    .agg(max_risk=("risk_score_v2", "max"), top_driver=("top_driver", "first"))
                    .sort_values("max_risk", ascending=False)
                    .head(5)
                )
                for _, r in top_risk.iterrows():
                    rv = float(r["max_risk"])
                    pill = "pill-crit" if rv >= 0.8 else "pill-warn" if rv >= 0.5 else "pill-ok"
                    st.markdown(
                        f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                        f"padding:10px 14px; border-radius:8px; margin-bottom:8px; font-size:13px;'>"
                        f"<b style='color:var(--ink);'>{r['project_id']}</b> "
                        f"<span style='color:var(--muted);'>@ {r['plant']}</span>&nbsp;"
                        f"<span class='pill {pill}'>{rv:.2f}</span><br>"
                        f"<span style='color:var(--ink-soft); font-size:12px;'>Driver: {r.get('top_driver', _DASH)}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                ui.empty_state("No risk data", "Run Wave 7 pipeline first.",
                               "python -m project.src.wave7.runner")

        with col_act:
            section("Top Recommended Actions", "Highest action score \u00b7 ready for planner sign-off")
            if not act_sc.empty and "action_score" in act_sc.columns:
                top_acts = act_sc.sort_values("action_score", ascending=False).head(5)
                for _, r in top_acts.iterrows():
                    score = float(r.get("action_score", 0))
                    conf  = float(r.get("confidence", 0))
                    pill  = "pill-ok" if conf >= 0.7 else "pill-warn"
                    st.markdown(
                        f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                        f"padding:10px 14px; border-radius:8px; margin-bottom:8px; font-size:13px;'>"
                        f"<b style='color:var(--ink);'>{r.get('project_id', _DASH)}</b> "
                        f"<span style='color:var(--muted);'>@ {r.get('plant', _DASH)}</span>&nbsp;"
                        f"<span class='pill {pill}'>conf {conf:.2f}</span><br>"
                        f"<span style='color:var(--accent-brand); font-weight:600;'>{r.get('action_type', _DASH)}</span>"
                        f"&nbsp;<span style='color:var(--muted); font-size:12px;'>score {score:.3f}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                ui.empty_state("No actions", "Run Wave 7 pipeline first.",
                               "python -m project.src.wave7.runner")

        # --- Scenario comparison table ---
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Scenario Summary", "Key metrics across all-in / expected / high-confidence / monte-carlo")
        scen_rows = []
        for sc in SCENARIOS:
            r_sc = _w7_filter(risk_v2, sc)
            a_sc = _w7_filter(acts_v2, sc)
            scen_rows.append({
                "Scenario":       SCENARIOS[sc]["label"],
                "Avg Risk":       f"{float(r_sc['risk_score_v2'].mean()):.3f}" if not r_sc.empty and "risk_score_v2" in r_sc.columns else "\u2014",
                "High-Risk Rows": int((r_sc["risk_score_v2"] >= 0.7).sum()) if not r_sc.empty and "risk_score_v2" in r_sc.columns else 0,
                "Actions":        int(len(a_sc)),
                "High-Confidence": int((a_sc["confidence"] >= 0.7).sum()) if not a_sc.empty and "confidence" in a_sc.columns else 0,
            })
        st.dataframe(pd.DataFrame(scen_rows), use_container_width=True, hide_index=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    cL, cR = st.columns([1, 1])
    with cL:
        st.plotly_chart(pipeline_funnel(pipe), use_container_width=True)
    with cR:
        rows = []
        for sc in SCENARIOS:
            u = get_utilization(sc, plant)
            rows.append({
                "scenario": sc, "label": SCENARIOS[sc]["label"],
                "peak_util": float(u["utilization"].max()) if not u.empty else 0,
                "weeks_critical": int((u["utilization"] >= 1.0).sum()) if not u.empty else 0,
                "total_demand_hours": float(u["demand_hours"].sum()) if not u.empty else 0,
            })
        st.plotly_chart(scenario_compare_bar(rows), use_container_width=True)

    section("Demand mix", "Where the expected pipeline is concentrated")
    st.plotly_chart(plant_demand_treemap(pipe), use_container_width=True)

    # --- Export plan as report ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Export Plan", "Download a stakeholder-ready report of this plan")

    if st.session_state.get("oneclick_done"):
        # Build markdown report from the live computed values
        from datetime import datetime as _dt
        _now = _dt.now().strftime("%Y-%m-%d %H:%M")
        
        # Calculate missing variables for the report
        total_eur = float(data.dim_project["total_eur"].fillna(0).sum())
        expected_eur = float((data.dim_project["total_eur"].fillna(0) * data.dim_project["probability_frac"].fillna(0)).sum())
        peak_u = float(util["utilization"].max()) if not util.empty else 0.0
        n_bot_view = int(bot.shape[0]) if not bot.empty else 0
        bot_b = bot if not bot.empty else pd.DataFrame()
        
        # Compute sourcing alerts and actions counts
        if not acts_v2.empty and "action_score" in acts_v2.columns:
            a_sc = _w7_filter(acts_v2, scenario)
            n_actions = int(len(a_sc))
        else:
            n_actions = 0
        
        if not risk_v2.empty and "risk_score_v2" in risk_v2.columns:
            r_sc = _w7_filter(risk_v2, scenario)
            avg_risk = float(r_sc["risk_score_v2"].mean()) if not r_sc.empty else 0.0
        else:
            avg_risk = 0.0
        
        # Sourcing bottlenecks
        src_b = get_sourcing(scenario, plant, top_n=20)
        n_short = int(src_b.shape[0]) if src_b is not None and not src_b.empty else 0
        _report_lines = [
            f"# Clarix Capacity & Sourcing Plan",
            f"",
            f"**Generated:** {_now}  ",
            f"**Region:** {w7_region}  ",
            f"**Quarter:** {w7_quarter or 'all quarters'}  ",
            f"**Scenario:** {SCENARIOS[scenario]['label']}  ",
            f"**Plant filter:** {plant or 'All plants'}  ",
            f"",
            f"---",
            f"",
            f"## Headline KPIs",
            f"",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Expected pipeline | EUR {expected_eur/1e6:.1f}M (of EUR {total_eur/1e6:.1f}M) |",
            f"| Peak utilization | {peak_u:.0%} |",
            f"| Bottlenecks (>=85%) | {n_bot_view} |",
            f"| Sourcing alerts | {n_short} |",
            f"| Planner actions | {n_actions} |",
            f"| Avg risk score | {avg_risk:.3f} |",
            f"",
            f"## Top 5 Bottlenecks",
            f"",
        ]
        if not bot_b.empty:
            _bb = bot_b.head(5)[["work_center", "plant", "peak_util", "weeks_crit"]].copy()
            _bb["peak_util"] = (_bb["peak_util"] * 100).round(1).astype(str) + "%"
            _report_lines.append("| Work Center | Plant | Peak Util | Weeks >=100% |")
            _report_lines.append("|---|---|---|---|")
            for _, r in _bb.iterrows():
                _report_lines.append(f"| {r['work_center']} | {r['plant']} | {r['peak_util']} | {r['weeks_crit']} |")
        else:
            _report_lines.append("_None detected._")

        _report_lines += ["", "## Top 5 Sourcing Alerts", ""]
        if src_b is not None and not src_b.empty:
            _cols = [c for c in ["component_material", "plant", "shortfall", "order_by"] if c in src_b.columns]
            _ss = src_b.head(5)[_cols]
            _report_lines.append("| " + " | ".join(_cols) + " |")
            _report_lines.append("|" + "|".join(["---"] * len(_cols)) + "|")
            for _, r in _ss.iterrows():
                _report_lines.append("| " + " | ".join(str(r[c]) for c in _cols) + " |")
        else:
            _report_lines.append("_None detected._")

        _report_lines += ["", "---", "",
                          "_Report generated by **Clarix** \u00b7 Danfoss Climate Solutions hackathon case 3_"]
        report_md = "\n".join(_report_lines)

        dcol1, dcol2, dcol3 = st.columns(3)
        with dcol1:
            st.download_button(
                label="\U0001F4C4  Markdown",
                data=report_md,
                file_name=f"clarix_plan_{w7_region.replace(' ', '_')}_{w7_quarter or 'all'}_{scenario}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with dcol2:
            # Pack live tables into a single Excel
            import io
            xbuf = io.BytesIO()
            with pd.ExcelWriter(xbuf, engine="openpyxl") as xw:
                bot_b.head(50).to_excel(xw, sheet_name="bottlenecks", index=False) if not bot_b.empty else pd.DataFrame().to_excel(xw, sheet_name="bottlenecks")
                (src_b.head(50).to_excel(xw, sheet_name="sourcing", index=False)
                    if src_b is not None and not src_b.empty
                    else pd.DataFrame().to_excel(xw, sheet_name="sourcing"))
                pd.DataFrame(scen_rows).to_excel(xw, sheet_name="scenario_summary", index=False) if scen_rows else None
            st.download_button(
                label="\U0001F4CA  Excel workbook",
                data=xbuf.getvalue(),
                file_name=f"clarix_plan_{w7_region.replace(' ', '_')}_{w7_quarter or 'all'}_{scenario}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with dcol3:
            # PDF report — branded, stakeholder-ready
            try:
                pdf_bytes = build_plan_pdf(
                    region=w7_region, quarter=w7_quarter, scenario_label=SCENARIOS[scenario]['label'],
                    plant_filter=plant or "All plants",
                    kpis={
                        "Expected pipeline": f"EUR {expected_eur/1e6:.1f}M of {total_eur/1e6:.1f}M",
                        "Peak utilization":  f"{peak_u:.0%}",
                        "Bottlenecks (>=85%)": f"{n_bot_view}",
                        "Sourcing alerts":   f"{n_short}",
                        "Planner actions":   f"{n_actions}",
                        "Avg risk score":    f"{avg_risk:.3f}",
                    },
                    bottlenecks=bot_b.head(5) if not bot_b.empty else pd.DataFrame(),
                    sourcing=src_b.head(5) if src_b is not None and not src_b.empty else pd.DataFrame(),
                    scenarios=pd.DataFrame(scen_rows) if scen_rows else pd.DataFrame(),
                )
                st.download_button(
                    label="\U0001F4D1  PDF report",
                    data=pdf_bytes,
                    file_name=f"clarix_plan_{w7_region.replace(' ', '_')}_{w7_quarter or 'all'}_{scenario}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            except Exception as _e:
                st.caption(f"PDF unavailable: {_e}")
    else:
        st.info("Click **Run full plan** above to generate a downloadable report.")

    # --- How the engine works ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("How the Engine Works", "A quick explainer for product owners")
    st.markdown(
        "<div style='background:var(--bg-soft); border:1px solid var(--line); "
        "border-radius:10px; padding:20px 24px; font-size:13px; color:var(--ink-soft); line-height:1.8;'>"
        "<b style='color:var(--ink); font-size:14px;'>1. Pipeline Ingestion</b><br>"
        "Sales opportunities (plates + gaskets) are loaded with probability weights. "
        "Expected demand = quantity \u00d7 probability, giving a realistic view of what will actually land.<br><br>"
        "<b style='color:var(--ink); font-size:14px;'>2. Capacity &amp; Bottleneck Analysis</b><br>"
        "Demand is routed through work centers using cycle times and shift schedules. "
        "Utilization is calculated per WC per week across pessimistic / base / optimistic scenarios.<br><br>"
        "<b style='color:var(--ink); font-size:14px;'>3. Integrated Risk Scoring (Wave 7)</b><br>"
        "Six risk dimensions (capacity, sourcing, logistics, delivery, disruption, maintenance) "
        "are combined into a single <b style='color:var(--ink);'>risk_score_v2</b>. "
        "Quarter-over-quarter learning and service-memory penalties are applied.<br><br>"
        "<b style='color:var(--ink); font-size:14px;'>4. Planner Action Generation</b><br>"
        "The engine recommends concrete actions (expedite, reroute, protect, reschedule) "
        "ranked by action score and confidence \u2014 ready for planner sign-off on the Actions page."
        "</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE 5 - What-if planner (project feasibility / quarter optimisation)
# =============================================================================
elif page == "What-if planner":
    page_header(
        "What-if planner",
        "Drop a hypothetical project into a quarter \u00b7 see if the factory can absorb it"
    )

    st.markdown(
        "<div style='background:var(--slate-wash); border-left:4px solid var(--slate); "
        "padding:12px 16px; border-radius:8px; margin-bottom:18px; color:var(--ink);'>"
        "<b>How it works.</b> Add one or more candidate projects to your basket "
        "(plant + material + quarter + qty + win-probability). Clarix replays the canonical "
        "pipeline plus your basket through the capacity engine and tells you which projects "
        "fit, which push a work center into overload, and which quarter could accept them instead."
        "</div>",
        unsafe_allow_html=True,
    )

    if "basket" not in st.session_state:
        # Pre-populate one demo project so the page is never empty
        plants_with_route = sorted(
            data.bridge_material_tool_wc["plant"].dropna().unique().tolist()
        )
        seed_plant = plants_with_route[0] if plants_with_route else None
        seed_basket = []
        if seed_plant:
            mats = list_addable_materials(data, seed_plant)
            if not mats.empty:
                seed_basket.append({
                    "project_name": "DEMO-Q3-FlexCool",
                    "plant": seed_plant,
                    "material": mats.iloc[0]["material"],
                    "material_description": mats.iloc[0]["material_description"],
                    "period_date": pd.Timestamp("2026-07-01"),
                    "qty": 8000,
                    "probability_frac": 0.6,
                    "spread_months": 3,
                })
        st.session_state.basket = seed_basket

    # ---- Add-project form -------------------------------------------------
    with st.expander("Add a candidate project", expanded=True):
        plants_with_route = sorted(
            data.bridge_material_tool_wc["plant"].dropna().unique().tolist()
        )
        f1, f2, f3 = st.columns([1.4, 1.6, 2])
        with f1:
            wp_plant = st.selectbox("Plant", plants_with_route, key="wp_plant")
            wp_year = st.selectbox("Year", [2026, 2027, 2028], key="wp_year")
            wp_q = st.selectbox("Quarter", ["Q1", "Q2", "Q3", "Q4"],
                                index=2, key="wp_q")
        with f2:
            mats = list_addable_materials(data, wp_plant)
            if mats.empty:
                st.warning("No materials with a tool/WC route at this plant.")
                wp_material = None
            else:
                mat_labels = [
                    f"{r.material} \u2014 {(r.material_description or '')[:60]}"
                    for r in mats.itertuples()
                ]
                idx = st.selectbox(
                    "Material", range(len(mat_labels)),
                    format_func=lambda i: mat_labels[i], key="wp_mat_idx"
                )
                wp_material = mats.iloc[idx]["material"]
                wp_mat_desc = mats.iloc[idx]["material_description"]
            wp_spread = st.slider(
                "Delivery spread (months)", 1, 6, 3, key="wp_spread",
                help="The qty is spread evenly across this many months starting from the chosen quarter."
            )
        with f3:
            wp_qty = st.number_input("Qty (pieces)", min_value=100, max_value=500_000,
                                     value=8000, step=500, key="wp_qty")
            wp_prob = st.slider(
                "Win probability", min_value=0.0, max_value=1.0, value=0.6, step=0.05,
                key="wp_prob",
                help="0.10 = early lead \u00b7 0.90 = signed/committed",
            )
            wp_name = st.text_input("Project name", value=f"WHATIF-{wp_year}-{wp_q}",
                                    key="wp_name")
            add_clicked = st.button("Add to basket", use_container_width=True, type="primary")

        if add_clicked and wp_material:
            q_int = int(wp_q[1])
            st.session_state.basket.append({
                "project_name": wp_name,
                "plant": wp_plant,
                "material": wp_material,
                "material_description": wp_mat_desc if 'wp_mat_desc' in dir() else "",
                "period_date": quarter_to_month(wp_year, q_int),
                "qty": float(wp_qty),
                "probability_frac": float(wp_prob),
                "spread_months": int(wp_spread),
            })
            st.rerun()

    # ---- Basket view ------------------------------------------------------
    section("Current basket",
            f"{len(st.session_state.basket)} candidate project(s) queued")

    if not st.session_state.basket:
        st.info("Basket is empty \u2014 add at least one project above.")
    else:
        bdf = pd.DataFrame(st.session_state.basket).copy()
        bdf["period_date"] = pd.to_datetime(bdf["period_date"]).dt.strftime("%Y-%m")
        bdf["qty"] = bdf["qty"].astype(int)
        bdf["probability_frac"] = (bdf["probability_frac"] * 100).round(0).astype(int).astype(str) + "%"
        bdf = bdf.rename(columns={
            "project_name": "Project", "plant": "Plant", "material": "Material",
            "material_description": "Description", "period_date": "Start month",
            "qty": "Qty", "probability_frac": "Prob",
            "spread_months": "Spread (mo)",
        })
        st.dataframe(bdf, use_container_width=True, hide_index=True)

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1:
            run_feas = st.button("Run feasibility check", type="primary",
                                 use_container_width=True)
        with cb2:
            if st.button("Clear basket", use_container_width=True):
                st.session_state.basket = []
                st.rerun()

        if run_feas:
            with st.spinner("Replaying pipeline + basket through the capacity engine..."):
                result = project_feasibility(data, scenario, st.session_state.basket)
            st.session_state.feas_result = result

    # ---- Feasibility output ----------------------------------------------
    if st.session_state.get("feas_result"):
        result = st.session_state.feas_result
        section("Feasibility verdict",
                "Per-project status \u00b7 worst work center driving the decision")

        per_proj = pd.DataFrame(result["per_project"])
        if per_proj.empty:
            st.info("No verdicts produced (basket may have unmappable materials).")
        else:
            summ = result["summary"]
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi("FEASIBLE", str(summ.get("feasible", 0)),
                         "fits without warning", "kpi-ok")
            with c2: kpi("AT RISK", str(summ.get("at_risk", 0)),
                         "85-100% peak after add", "kpi-warn")
            with c3: kpi("INFEASIBLE", str(summ.get("infeasible", 0)),
                         "pushes WC over 100%", "kpi-accent")
            with c4: kpi("OVERLOAD ADDED",
                         f"{summ.get('overload_hours_added', 0):,.0f} h",
                         "extra hours over capacity",
                         "kpi-accent" if summ.get("overload_hours_added", 0) > 0 else "kpi-ok")

            st.markdown("<hr/>", unsafe_allow_html=True)

            for v in result["per_project"]:
                status = v["status"]
                pill_cls = {
                    "feasible": "pill-ok", "at_risk": "pill-warn",
                    "infeasible": "pill-crit", "no_route": "pill-slate",
                    "no_capacity_data": "pill-slate",
                }.get(status, "pill-slate")
                pill_label = status.replace("_", " ").upper()
                st.markdown(
                    f"<div style='border:1px solid var(--line); border-radius:12px; "
                    f"padding:14px 18px; margin-bottom:10px; background:var(--bg-soft); "
                    f"box-shadow: 0 1px 0 rgba(0,0,0,0.4);'>"
                    f"<div style='display:flex; align-items:center; gap:12px; flex-wrap:wrap;'>"
                    f"  <span style='font-weight:700; font-size:15px; color:var(--ink);'>{v['project']}</span>"
                    f"  <span class='pill {pill_cls}'>{pill_label}</span>"
                    f"  <span style='color:var(--muted); font-size:12px;'>"
                    f"  &nbsp;\u00b7&nbsp; {v['plant']} \u00b7 {v['material']} \u00b7 {v['quarter']}</span>"
                    f"</div>"
                    f"<div style='margin-top:8px; font-size:13px; color:var(--ink-soft);'>"
                    f"Worst WC <b style='color:var(--ink);'>{v['worst_wc']}</b> \u00b7 "
                    f"peak util <b style='color:var(--ink);'>{v['peak_util_after']:.0%}</b> "
                    f"(was {v.get('peak_util_before', 0):.0%}) \u00b7 "
                    f"adds <b style='color:var(--ink);'>{v['marginal_h']:,.0f}h</b> demand \u00b7 "
                    f"quarter headroom <b style='color:var(--ink);'>{v['headroom_h']:,.0f}h</b>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            section("Quarter-by-quarter impact",
                    "Worst WC peak utilisation \u2014 baseline vs after-basket, by quarter")
            pq = result["per_quarter"]
            if pq.empty:
                st.info("No quarter-level impact to display.")
            else:
                disp = pq.copy()
                disp["peak_before"] = (disp["peak_before"] * 100).round(1)
                disp["peak_after"] = (disp["peak_after"] * 100).round(1)
                disp["delta_pp"] = disp["delta_pp"].round(1)
                disp = disp.rename(columns={
                    "work_center": "Work Center", "quarter": "Quarter",
                    "peak_before": "Peak before %", "peak_after": "Peak after %",
                    "delta_pp": "Delta (pp)",
                })
                st.dataframe(
                    disp, use_container_width=True, hide_index=True,
                    column_config={
                        "Peak before %": st.column_config.ProgressColumn(
                            "Peak before %", min_value=0, max_value=200, format="%.0f%%"),
                        "Peak after %": st.column_config.ProgressColumn(
                            "Peak after %", min_value=0, max_value=200, format="%.0f%%"),
                    },
                )


# =============================================================================
# PAGE 6 - Ask Clarix
# =============================================================================
elif page == "Ask Clarix":
    page_header("Ask Clarix",
                "Natural-language Q&A \u00b7 the agent calls one of five tools and synthesizes the answer")

    has_key = bool(os.environ.get("ANTHROPIC_API_KEY")
                    or os.environ.get("GEMINI_API_KEY")
                    or os.environ.get("GOOGLE_API_KEY"))
    if not has_key:
        st.info(
            "**Planner mode** \u2014 set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` for the full conversational agent. "
            "The deterministic fallback still answers questions about *bottlenecks*, *sourcing*, and *scenarios*."
        )

    if "chat" not in st.session_state:
        st.session_state.chat = []

    suggested = [
        "What are the top bottlenecks under the expected scenario?",
        "Compare all four scenarios.",
        "Why is the worst work center overloaded?",
        "Which components do we need to order in the next 8 weeks?",
    ]
    cols = st.columns(len(suggested))
    for c, q in zip(cols, suggested):
        if c.button(q, use_container_width=True):
            st.session_state.pending = q

    user_msg = st.chat_input("Ask about capacity, bottlenecks, sourcing, or a specific work center...")
    if "pending" in st.session_state and not user_msg:
        user_msg = st.session_state.pending
        del st.session_state.pending

    for turn in st.session_state.chat:
        role = turn["role"]
        if role == "user":
            st.markdown(f"<div class='chat-msg chat-user'><b>You</b><br>{turn['text']}</div>",
                        unsafe_allow_html=True)
        elif role == "assistant":
            st.markdown(f"<div class='chat-msg chat-assistant'><b>Clarix</b><br>{turn['text']}</div>",
                        unsafe_allow_html=True)
        elif role == "tool":
            st.markdown(
                f"<div class='chat-msg chat-tool'><b>tool: {turn.get('name','?')}</b><br>{turn['text']}</div>",
                unsafe_allow_html=True,
            )

    if user_msg:
        st.session_state.chat.append({"role": "user", "text": user_msg})
        with st.spinner("Clarix is thinking..."):
            try:
                answer, trace = run_agent(user_msg, data)
            except Exception as exc:
                answer = (
                    "Clarix hit an unexpected error while generating the answer.\n\n"
                    "The app should still work without Anthropic if `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set. "
                    "If no LLM key is configured, planner mode should still return a deterministic summary.\n\n"
                    f"Internal error: {exc}"
                )
                trace = []
        for t in trace:
            if t.role == "tool":
                st.session_state.chat.append({"role": "tool", "name": t.tool_name, "text": t.content})
        st.session_state.chat.append({"role": "assistant", "text": answer})
        st.rerun()


# =============================================================================
# PAGE 7 - Logistics & Disruptions
# =============================================================================
elif page == "Logistics & Disruptions":
    page_header("Logistics & Disruptions",
                "Shipping lanes \u00b7 landed cost tradeoffs \u00b7 disruption scenarios \u00b7 mitigation levers")

    w7 = _load_w7()
    logistics_df = w7.get("logistics", pd.DataFrame())

    ui.data_source_strip([
        ("real",      "fact_scenario_logistics_weekly"),
        ("synthetic", "dim_shipping_lane_synth"),
        ("synthetic", "dim_country_cost_index_synth"),
        ("synthetic", "dim_disruption_scenario_synth"),
    ])

    if logistics_df.empty:
        ui.empty_state("No logistics data",
                       "fact_scenario_logistics_weekly missing or empty.",
                       "python -m project.src.wave6.runner")
        st.stop()

    # Filter by current scenario
    filtered = _w7_filter(logistics_df, scenario)

    # --- KPI row ---
    total_routes = int(len(filtered))
    avg_transit  = float(filtered["transit_time_days"].mean()) if "transit_time_days" in filtered.columns and total_routes > 0 else 0.0
    pct_on_time  = float((filtered["on_time_feasible_flag"] == True).sum()) / max(total_routes, 1) * 100 if "on_time_feasible_flag" in filtered.columns and total_routes > 0 else 0.0  # noqa: E712
    avg_log_risk = float(filtered["logistics_risk_score"].mean()) if "logistics_risk_score" in filtered.columns and total_routes > 0 else 0.0
    avg_landed   = float(filtered["landed_cost_proxy"].mean()) if "landed_cost_proxy" in filtered.columns and total_routes > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("TOTAL ROUTES", f"{total_routes:,}", f"scenario: {scenario}", "kpi-slate")
    with c2: kpi("AVG TRANSIT DAYS", f"{avg_transit:.1f}", "mean transit time",
                 "kpi-ok" if avg_transit < 10 else "kpi-warn")
    with c3: kpi("% ON-TIME FEASIBLE", f"{pct_on_time:.1f}%", "routes meeting deadline",
                 "kpi-ok" if pct_on_time >= 80 else "kpi-warn" if pct_on_time >= 50 else "kpi-accent")
    with c4: kpi("AVG LOGISTICS RISK", f"{avg_log_risk:.3f}", "0 = low, 1 = critical",
                 "kpi-ok" if avg_log_risk < 0.3 else "kpi-warn" if avg_log_risk < 0.6 else "kpi-accent")

    # Synthetic enrichment explanation
    ui.assumption_panel(
        "Shipping lanes, country cost indices, and disruption scenarios are synthetic enrichments. "
        "Transit times and on-time feasibility flags are derived from real production schedule data. "
        "Landed cost proxies are directional only \u2014 not suitable for financial reporting."
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Shipping cost / transit time summary ---
    section("Shipping Cost & Transit Time Summary", "Per destination country \u00b7 avg values across all routes")
    if not filtered.empty and "destination_country" in filtered.columns:
        cty_sum = (
            filtered.groupby("destination_country", as_index=False)
            .agg(routes=("week", "count"),
                 avg_transit=("transit_time_days", "mean"),
                 avg_shipping=("shipping_cost", "mean"),
                 avg_landed=("landed_cost_proxy", "mean"),
                 avg_risk=("logistics_risk_score", "mean"))
            .sort_values("avg_risk", ascending=False)
        )
        for col_n in ["avg_transit", "avg_shipping", "avg_landed", "avg_risk"]:
            if col_n in cty_sum.columns:
                cty_sum[col_n] = cty_sum[col_n].round(2)
        st.dataframe(cty_sum, use_container_width=True, hide_index=True,
                     column_config={
                         "avg_risk": st.column_config.ProgressColumn(
                             "Avg Risk", min_value=0.0, max_value=1.0, format="%.3f"),
                         "avg_shipping": st.column_config.NumberColumn("Avg Shipping $", format="$%.0f"),
                         "avg_landed":   st.column_config.NumberColumn("Avg Landed $",   format="$%.0f"),
                     })

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Landed cost proxy comparison + disruption before/after ---
    col_cost, col_disruption = st.columns(2)

    with col_cost:
        section("Landed Cost Comparison", "Avg landed cost proxy by scenario")
        if "scenario" in logistics_df.columns and "landed_cost_proxy" in logistics_df.columns:
            lc_cmp = (
                logistics_df.groupby("scenario", as_index=False)
                .agg(avg_landed=("landed_cost_proxy", "mean"),
                     avg_shipping=("shipping_cost", "mean"),
                     avg_transit=("transit_time_days", "mean"))
                .round(2)
            )
            try:
                import plotly.express as _pxld
                fig_lc = _pxld.bar(lc_cmp, x="scenario", y="avg_landed",
                                   color="avg_landed",
                                   color_continuous_scale=["#22c55e", "#f97316", "#ef4444"],
                                   labels={"avg_landed": "Avg Landed Cost $", "scenario": "Scenario"},
                                   title="Avg Landed Cost by Scenario",
                                   template="plotly_dark")
                fig_lc.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
                                      font_color="#E2E8F0", coloraxis_showscale=False)
                st.plotly_chart(fig_lc, use_container_width=True)
            except Exception:
                st.dataframe(lc_cmp, use_container_width=True, hide_index=True)
        else:
            ui.empty_state("No landed cost data")

    with col_disruption:
        section("Disruption Before/After", "Logistics risk: base vs disrupted scenarios")
        if "scenario" in logistics_df.columns and "logistics_risk_score" in logistics_df.columns:
            sc_risk = (
                logistics_df.groupby("scenario", as_index=False)
                .agg(avg_risk=("logistics_risk_score", "mean"),
                     pct_on_time=("on_time_feasible_flag", "mean"),
                     routes=("week", "count"))
                .sort_values("avg_risk", ascending=False)
            )
            sc_risk["avg_risk"] = sc_risk["avg_risk"].round(3)
            sc_risk["pct_on_time"] = (sc_risk["pct_on_time"] * 100).round(1)
            try:
                import plotly.express as _pxdr
                fig_dr = _pxdr.bar(sc_risk, x="scenario", y="avg_risk",
                                   color="avg_risk",
                                   color_continuous_scale=["#22c55e", "#f97316", "#ef4444"],
                                   range_color=[0, 1],
                                   labels={"avg_risk": "Avg Logistics Risk", "scenario": "Scenario"},
                                   title="Avg Logistics Risk by Scenario",
                                   template="plotly_dark")
                fig_dr.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
                                      font_color="#E2E8F0", coloraxis_showscale=False)
                st.plotly_chart(fig_dr, use_container_width=True)
            except Exception:
                st.dataframe(sc_risk, use_container_width=True, hide_index=True)
        else:
            ui.empty_state("No scenario comparison data")

    # --- Route / lane risk panel ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Route / Lane Risk Panel", "Top 20 plant\u2192destination routes by logistics risk")
    if not filtered.empty and "destination_country" in filtered.columns and "logistics_risk_score" in filtered.columns:
        route_risk = (
            filtered.groupby(["plant", "destination_country"], as_index=False)
            .agg(avg_risk=("logistics_risk_score", "mean"),
                 avg_transit=("transit_time_days", "mean"),
                 avg_cost=("shipping_cost", "mean"),
                 route_weeks=("week", "nunique"))
            .sort_values("avg_risk", ascending=False)
            .head(20)
        )
        for _, r in route_risk.iterrows():
            risk = float(r["avg_risk"])
            pill = "pill-crit" if risk >= 0.8 else "pill-warn" if risk >= 0.5 else "pill-ok"
            st.markdown(
                f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                f"padding:10px 14px; border-radius:8px; margin-bottom:6px; font-size:13px; "
                f"display:flex; align-items:center; gap:12px;'>"
                f"<b style='color:var(--ink);'>{r['plant']}</b>"
                f"<span style='color:var(--muted);'>\u2192 {r['destination_country']}</span>&nbsp;"
                f"<span class='pill {pill}'>risk {risk:.2f}</span>"
                f"<span style='color:var(--muted); font-size:12px;'>"
                f"transit {r.get('avg_transit', 0):.1f}d &nbsp;\u00b7&nbsp; "
                f"cost ${r.get('avg_cost', 0):.0f} &nbsp;\u00b7&nbsp; "
                f"{int(r.get('route_weeks', 0))} weeks</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # --- Mitigation lever summary ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Mitigation Lever Summary", "Available mitigation options per scenario")
    if not filtered.empty and "expedite_option_flag" in filtered.columns:
        exp_cnt  = int((filtered["expedite_option_flag"] == True).sum())  # noqa: E712
        late_cnt = int((filtered["on_time_feasible_flag"] == False).sum()) if "on_time_feasible_flag" in filtered.columns else 0  # noqa: E712
        synth_cnt = int(filtered["synthetic_dependency_flag"].sum()) if "synthetic_dependency_flag" in filtered.columns else 0

        lev_cols = st.columns(3)
        with lev_cols[0]:
            st.markdown(
                f"<div style='background:var(--bg-soft); border:1px solid var(--line); padding:16px; border-radius:8px; text-align:center;'>"
                f"<div style='font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;'>Expedite Eligible</div>"
                f"<div style='font-size:28px; font-weight:800; color:var(--ok-green); margin-top:6px;'>{exp_cnt:,}</div>"
                f"<div style='font-size:11px; color:var(--muted);'>route-weeks where expedite is policy-allowed</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with lev_cols[1]:
            st.markdown(
                f"<div style='background:var(--bg-soft); border:1px solid var(--line); padding:16px; border-radius:8px; text-align:center;'>"
                f"<div style='font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;'>Late Route-Weeks</div>"
                f"<div style='font-size:28px; font-weight:800; color:#ef4444; margin-top:6px;'>{late_cnt:,}</div>"
                f"<div style='font-size:11px; color:var(--muted);'>require rerouting or schedule pull-in</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with lev_cols[2]:
            st.markdown(
                f"<div style='background:var(--bg-soft); border:1px solid var(--line); padding:16px; border-radius:8px; text-align:center;'>"
                f"<div style='font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;'>Synthetic Dependencies</div>"
                f"<div style='font-size:28px; font-weight:800; color:var(--muted); margin-top:6px;'>{synth_cnt:,}</div>"
                f"<div style='font-size:11px; color:var(--muted);'>route-weeks enriched with synthetic lane data</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # --- Full logistics table ---
    with st.expander("Full logistics feasibility table", expanded=False):
        if not filtered.empty:
            display_cols = [c for c in ["project_id", "plant", "destination_country", "week",
                                         "transit_time_days", "shipping_cost", "landed_cost_proxy",
                                         "on_time_feasible_flag", "expedite_option_flag",
                                         "logistics_risk_score", "synthetic_dependency_flag"]
                            if c in filtered.columns]
            st.dataframe(filtered[display_cols].head(500), use_container_width=True, hide_index=True,
                         column_config={
                             "logistics_risk_score": st.column_config.ProgressColumn(
                                 "Logistics Risk", min_value=0.0, max_value=1.0, format="%.3f"),
                             "shipping_cost":   st.column_config.NumberColumn("Shipping $",  format="$%.0f"),
                             "landed_cost_proxy": st.column_config.NumberColumn("Landed $", format="$%.0f"),
                         })

    # --- What this means ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:var(--bg-soft); border:1px solid var(--line); border-radius:10px; "
        "padding:18px 22px; font-size:13px; color:var(--ink-soft); line-height:1.8;'>"
        "<b style='color:var(--ink); font-size:14px;'>What this means for planners</b><br>"
        "Disruption scenarios simulate lane closures, port congestion, or tariff changes. "
        "Routes showing <b style='color:var(--ink);'>high logistics risk</b> should be reviewed for "
        "rerouting or schedule pull-in. <b style='color:var(--ink);'>Expedite-eligible</b> routes can "
        "absorb lateness through premium shipping \u2014 but at a cost captured in the landed cost proxy. "
        "The <b style='color:var(--ink);'>pessimistic scenario</b> represents worst-case disruption; "
        "compare it against the base to quantify the value of proactive mitigation."
        "</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE W7-1 — Scope & Region View
# =============================================================================
elif page == "Scope & Region":
    page_header("Scope & Region", "Single-region focus \u00b7 plants in scope \u00b7 demand distribution")

    w7 = _load_w7()
    rscope = w7.get("region_scope", pd.DataFrame())
    pq     = w7.get("pipeline_quarterly", pd.DataFrame())
    proj_pri = w7.get("project_priority", pd.DataFrame())

    ui.data_source_strip([
        ("real", "dim_region_scope"),
        ("real", "fact_pipeline_quarterly"),
        ("real", "dim_project_priority"),
    ])

    # --- Region selector + info card ---
    if not rscope.empty and "region_name" in rscope.columns:
        region_options = sorted(rscope["region_name"].dropna().unique().tolist())
        sel_region = w7_region if w7_region and w7_region in region_options else region_options[0]
        row = rscope[rscope["region_name"] == sel_region].iloc[0]
    else:
        row = pd.Series({"region_name": "MVP Region", "scope_id": "mvp_3plant",
                         "included_plants": "NW01, NW02, NW05",
                         "included_factories_note": "Three pilot factories",
                         "scope_rule": "Highest revenue concentration"})

    scope_id    = str(row.get("scope_id", "mvp_3plant"))
    plants_note = str(row.get("included_plants", "NW01, NW02, NW05"))
    factories_note = str(row.get("included_factories_note", ""))
    scope_rule  = str(row.get("scope_rule", "\u2014"))

    st.markdown(
        f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
        f"border-left:4px solid var(--accent-brand); padding:18px 22px; border-radius:10px; margin-bottom:18px;'>"
        f"<div style='display:flex; justify-content:space-between; align-items:flex-start;'>"
        f"<div>"
        f"<div style='font-size:20px; font-weight:700; color:var(--ink);'>{row.get('region_name','')}</div>"
        f"<div style='font-size:11px; color:var(--muted); margin-top:4px; text-transform:uppercase; letter-spacing:1px;'>scope_id: {scope_id}</div>"
        f"</div>"
        f"<span class='pill pill-ok'>ACTIVE SCOPE</span>"
        f"</div>"
        f"<div style='margin-top:12px; font-size:13px; color:var(--ink-soft); line-height:1.8;'>"
        f"<b style='color:var(--ink);'>Plants in scope:</b> {plants_note}<br>"
        f"{'<b style=color:var(--ink);>Factories note:</b> ' + factories_note + '<br>' if factories_note and factories_note != 'nan' else ''}"
        f"<b style='color:var(--ink);'>Scope rule:</b> {scope_rule}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # --- KPIs ---
    pq_scope = pq[pq["scope_id"] == scope_id] if not pq.empty and "scope_id" in pq.columns else pq
    n_projects  = int(pq_scope["project_id"].nunique()) if not pq_scope.empty and "project_id" in pq_scope.columns else 0
    n_plants_s  = int(pq_scope["plant"].nunique()) if not pq_scope.empty and "plant" in pq_scope.columns else 0
    n_materials = int(pq_scope["material"].nunique()) if not pq_scope.empty and "material" in pq_scope.columns else 0
    exp_val     = float(pq_scope["expected_value_quarter"].sum()) if not pq_scope.empty and "expected_value_quarter" in pq_scope.columns else 0.0
    n_quarters  = int(pq_scope["quarter_id"].nunique()) if not pq_scope.empty and "quarter_id" in pq_scope.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("PROJECTS IN SCOPE", f"{n_projects}", f"across {n_plants_s} plants", "kpi-accent")
    with c2: kpi("PLANTS / FACTORIES", f"{n_plants_s}", "in this region", "kpi-slate")
    with c3: kpi("MATERIALS", f"{n_materials}", f"over {n_quarters} quarters", "kpi-slate")
    with c4: kpi("EXPECTED VALUE", f"\u20AC{exp_val/1e6:.1f}M" if exp_val >= 1e6 else f"\u20AC{exp_val:,.0f}",
                 "prob-weighted pipeline", "kpi-ok")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Pipeline timeline (chart factory) ---
    section("Demand Distribution by Quarter", "Expected quantity per plant per quarter \u00b7 probability-weighted")
    if not pq_scope.empty:
        st.plotly_chart(pipeline_timeline_bar(pq_scope), use_container_width=True)
        st.caption("Each bar segment = one plant. Height = sum of expected quantity (all materials).")
    else:
        ui.empty_state("No pipeline data", "fact_pipeline_quarterly missing or empty.",
                       "python -m project.src.wave7.runner")

    # --- Plant-level overview ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Factory / Plant Overview", "Per-plant summary \u00b7 select a factory to inspect")

    if not pq_scope.empty and "plant" in pq_scope.columns:
        plant_sum = (
            pq_scope.groupby("plant", as_index=False)
            .agg(projects=("project_id", "nunique"),
                 materials=("material", "nunique"),
                 quarters=("quarter_id", "nunique"),
                 exp_qty=("expected_qty_quarter", "sum"),
                 exp_val=("expected_value_quarter", "sum"))
            .sort_values("exp_val", ascending=False)
        )
        plant_sum["exp_val"] = plant_sum["exp_val"].round(0)
        plant_sum["exp_qty"] = plant_sum["exp_qty"].round(1)
        st.dataframe(
            plant_sum,
            use_container_width=True, hide_index=True,
            column_config={
                "exp_val": st.column_config.NumberColumn("Expected Value \u20AC", format="\u20AC%.0f"),
                "exp_qty": st.column_config.NumberColumn("Expected Qty", format="%.1f"),
            },
        )

        # Selected-factory drilldown
        factory_list = sorted(plant_sum["plant"].dropna().tolist())
        sel_factory = st.selectbox("Drill down into a factory", factory_list, key="sr_factory_sel")
        pq_fact = pq_scope[pq_scope["plant"] == sel_factory]
        if not pq_fact.empty:
            f_projects = int(pq_fact["project_id"].nunique())
            f_materials = int(pq_fact["material"].nunique())
            f_val = float(pq_fact["expected_value_quarter"].sum()) if "expected_value_quarter" in pq_fact.columns else 0.0
            f_qty = float(pq_fact["expected_qty_quarter"].sum()) if "expected_qty_quarter" in pq_fact.columns else 0.0
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Projects", f_projects)
            m2.metric("Materials", f_materials)
            m3.metric("Expected Value", f"\u20AC{f_val:,.0f}")
            m4.metric("Expected Qty", f"{f_qty:,.1f}")
    else:
        ui.empty_state("No plant breakdown", "fact_pipeline_quarterly missing or has no plant column.")

    # --- Priority band breakdown (dim_project_priority) ---
    if not proj_pri.empty and "priority_band" in proj_pri.columns and "project_id" in proj_pri.columns:
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Project Priority Breakdown", "Distribution of projects by priority band in this scope")

        # filter to projects in scope
        scoped_project_ids = set(pq_scope["project_id"].dropna().unique()) if not pq_scope.empty and "project_id" in pq_scope.columns else set()
        pri_scope = proj_pri[proj_pri["project_id"].isin(scoped_project_ids)] if scoped_project_ids else proj_pri

        band_counts = pri_scope["priority_band"].value_counts().reset_index()
        band_counts.columns = ["Priority Band", "Projects"]

        col_pri, col_tbl = st.columns([1, 1])
        with col_pri:
            band_order = ["critical", "high", "medium", "low"]
            band_counts["sort_key"] = band_counts["Priority Band"].apply(
                lambda x: band_order.index(x) if x in band_order else 99
            )
            band_counts = band_counts.sort_values("sort_key").drop(columns="sort_key")
            for _, brow in band_counts.iterrows():
                band = str(brow["Priority Band"])
                cnt  = int(brow["Projects"])
                pill = {"critical": "pill-crit", "high": "pill-warn", "medium": "pill-info", "low": "pill-slate"}.get(band, "pill-slate")
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:12px; margin-bottom:8px;'>"
                    f"<span class='pill {pill}'>{band.upper()}</span>"
                    f"<span style='font-size:24px; font-weight:700; color:var(--ink);'>{cnt}</span>"
                    f"<span style='font-size:12px; color:var(--muted);'>projects</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        with col_tbl:
            if not pri_scope.empty:
                top_pri = pri_scope.sort_values("priority_score", ascending=False).head(10)[
                    [c for c in ["project_id", "priority_band", "priority_score", "revenue_tier", "region"]
                     if c in pri_scope.columns]
                ]
                st.dataframe(top_pri, use_container_width=True, hide_index=True)

    # --- Scope rationale panel ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    ui.assumption_panel(
        "This MVP intentionally focuses on one geographic region and a small number of factories. "
        "The framework extends to all 15 plants \u2014 the scope boundary is a deliberate demo constraint, "
        "not a product limitation."
    )

    # --- Data coverage panel ---
    section("Data Coverage", "Which Wave 7 outputs are available for this scope")
    cov_rows = [
        ("dim_region_scope",         not rscope.empty,   "Region / scope definitions"),
        ("fact_pipeline_quarterly",  not pq.empty,       "Quarterly demand pipeline"),
        ("dim_project_priority",     not proj_pri.empty, "Project priority scores"),
        ("fact_planner_actions_v2",  not w7.get("planner_actions_v2", pd.DataFrame()).empty, "Planner action recommendations"),
        ("fact_integrated_risk_v2",  not w7.get("integrated_risk_v2", pd.DataFrame()).empty, "Integrated risk scores"),
    ]
    cov_cols = st.columns(len(cov_rows))
    for col, (name, avail, desc) in zip(cov_cols, cov_rows):
        with col:
            pill = "pill-ok" if avail else "pill-crit"
            label = "AVAILABLE" if avail else "MISSING"
            st.markdown(
                f"<div style='text-align:center; padding:12px 8px; background:var(--bg-soft); "
                f"border:1px solid var(--line); border-radius:8px;'>"
                f"<span class='pill {pill}'>{label}</span>"
                f"<div style='font-size:11px; color:var(--ink); font-weight:600; margin-top:8px;'>{name}</div>"
                f"<div style='font-size:11px; color:var(--muted); margin-top:4px;'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# =============================================================================
# PAGE W7-2 — Quarter History / Learning View
# =============================================================================
elif page == "Quarter History":
    page_header("Quarter History", "Quarter-over-quarter learning \u00b7 service memory \u00b7 carry-over signals")

    w7 = _load_w7()
    smem       = w7.get("service_memory", pd.DataFrame())
    rollfw     = w7.get("rollforward_inputs", pd.DataFrame())
    learning   = w7.get("learning_signals", pd.DataFrame())
    delivery_rf = w7.get("delivery_rollforward", pd.DataFrame())

    ui.data_source_strip([
        ("real", "fact_quarter_service_memory"),
        ("real", "fact_quarter_rollforward_inputs"),
        ("real", "fact_quarter_learning_signals"),
        ("real", "fact_delivery_risk_rollforward"),
    ])

    # --- Quarter selector ---
    all_qtrs = sorted(smem["quarter_id"].dropna().unique().tolist()) if not smem.empty and "quarter_id" in smem.columns else ["2026-Q1"]
    default_qtr = w7_quarter if w7_quarter and w7_quarter in all_qtrs else (all_qtrs[0] if all_qtrs else "2026-Q1")
    qtr_options = all_qtrs + (["All quarters"] if len(all_qtrs) > 1 else [])
    sel_qtr_idx = qtr_options.index(default_qtr) if default_qtr in qtr_options else 0
    sel_qtr_raw = st.selectbox("Quarter", qtr_options, index=sel_qtr_idx, key="qh_quarter")
    show_all = (sel_qtr_raw == "All quarters")
    sel_qtr  = sel_qtr_raw if not show_all else (all_qtrs[0] if all_qtrs else "2026-Q1")

    # --- KPIs (current quarter) ---
    smem_q  = smem if show_all else (smem[smem["quarter_id"] == sel_qtr] if not smem.empty and "quarter_id" in smem.columns else smem)
    learn_q = learning if show_all else (learning[learning["quarter_id"] == sel_qtr] if not learning.empty and "quarter_id" in learning.columns else learning)

    n_proj_q    = int(smem_q["project_id"].nunique()) if not smem_q.empty and "project_id" in smem_q.columns else 0
    caution_cnt = int(smem_q["carry_over_service_caution_flag"].sum()) if not smem_q.empty and "carry_over_service_caution_flag" in smem_q.columns else 0
    avg_risk    = float(smem_q["prior_service_violation_risk"].mean()) if not smem_q.empty and "prior_service_violation_risk" in smem_q.columns else 0.0
    rep_risk    = int(learn_q["repeated_risk_flag"].sum()) if not learn_q.empty and "repeated_risk_flag" in learn_q.columns else 0

    # Q-over-Q comparison: get previous quarter's values
    qtr_idx_current = all_qtrs.index(sel_qtr) if sel_qtr in all_qtrs else 0
    prev_qtr  = all_qtrs[qtr_idx_current - 1] if qtr_idx_current > 0 else None
    if prev_qtr and not smem.empty and "quarter_id" in smem.columns:
        smem_prev   = smem[smem["quarter_id"] == prev_qtr]
        avg_risk_prev = float(smem_prev["prior_service_violation_risk"].mean()) if not smem_prev.empty and "prior_service_violation_risk" in smem_prev.columns else None
        caution_prev  = int(smem_prev["carry_over_service_caution_flag"].sum()) if not smem_prev.empty and "carry_over_service_caution_flag" in smem_prev.columns else None
    else:
        avg_risk_prev = caution_prev = None

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("PROJECTS TRACKED", f"{n_proj_q}", f"quarter: {sel_qtr if not show_all else 'all'}", "kpi-slate")
    with c2: kpi("CARRY-OVER CAUTION", f"{caution_cnt}",
                 f"prev: {caution_prev}" if caution_prev is not None else "flagged for next quarter",
                 "kpi-warn" if caution_cnt else "kpi-ok")
    with c3: kpi("AVG VIOLATION RISK", f"{avg_risk:.3f}",
                 f"prev: {avg_risk_prev:.3f}" if avg_risk_prev is not None else "0=clean, 1=critical",
                 "kpi-accent" if avg_risk > 0.4 else "kpi-warn" if avg_risk > 0.2 else "kpi-ok")
    with c4: kpi("REPEATED RISKS", f"{rep_risk}", "same risk flag reappearing", "kpi-warn" if rep_risk else "kpi-ok")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Q-over-Q comparison panel ---
    if prev_qtr and not show_all:
        section("Quarter-over-Quarter Comparison", f"{prev_qtr} \u2192 {sel_qtr}")
        learn_prev = learning[learning["quarter_id"] == prev_qtr] if not learning.empty and "quarter_id" in learning.columns else pd.DataFrame()
        rep_prev   = int(learn_prev["repeated_risk_flag"].sum()) if not learn_prev.empty and "repeated_risk_flag" in learn_prev.columns else 0

        delta_cols = st.columns(3)
        with delta_cols[0]:
            delta_risk = avg_risk - avg_risk_prev if avg_risk_prev is not None else 0.0
            st.metric("Avg Violation Risk", f"{avg_risk:.3f}", f"{delta_risk:+.3f} vs {prev_qtr}")
        with delta_cols[1]:
            delta_caution = caution_cnt - caution_prev if caution_prev is not None else 0
            st.metric("Carry-over Caution", caution_cnt, f"{delta_caution:+d} vs {prev_qtr}")
        with delta_cols[2]:
            delta_rep = rep_risk - rep_prev
            st.metric("Repeated Risks", rep_risk, f"{delta_rep:+d} vs {prev_qtr}")

        ui.assumption_panel(
            f"Quarter {sel_qtr} inherits carry-over penalties and caution flags from {prev_qtr}. "
            "Projects with repeated risks receive a confidence penalty on their recommended actions."
        )
        st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Carry-over project risk panel ---
    section("Carry-Over Project Risk", "Projects flagged for caution in the next quarter")
    if not smem_q.empty and "carry_over_service_caution_flag" in smem_q.columns:
        caution_projects = smem_q[smem_q["carry_over_service_caution_flag"] == True].copy()  # noqa: E712
        if not caution_projects.empty:
            caution_projects = caution_projects.sort_values("prior_service_violation_risk", ascending=False) if "prior_service_violation_risk" in caution_projects.columns else caution_projects
            for _, r in caution_projects.head(10).iterrows():
                risk_val = float(r.get("prior_service_violation_risk", 0))
                pill = "pill-crit" if risk_val > 0.6 else "pill-warn" if risk_val > 0.3 else "pill-slate"
                st.markdown(
                    f"<div style='background:var(--bg-soft); border-left:3px solid var(--accent-brand); "
                    f"padding:10px 14px; border-radius:8px; margin-bottom:8px; font-size:13px;'>"
                    f"<b style='color:var(--ink);'>{r.get('project_id', _DASH)}</b>&nbsp;"
                    f"<span class='pill {pill}'>risk {risk_val:.3f}</span><br>"
                    f"<span style='color:var(--ink-soft); font-size:12px;'>"
                    f"Carry-over caution: {r.get('caution_explanation', r.get('prior_reason_note', 'flagged'))}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("No carry-over caution projects in this quarter.")
    else:
        ui.empty_state("No service memory", "fact_quarter_service_memory missing.",
                       "python -m project.src.wave7.runner")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- What changed from last quarter? ---
    section("What Changed from Last Quarter?", "Roll-forward signals \u00b7 probability/priority adjustments \u00b7 deferred projects")
    if not rollfw.empty and "to_quarter" in rollfw.columns:
        rf_q = rollfw if show_all else rollfw[rollfw["to_quarter"] == sel_qtr]
        if rf_q.empty:
            st.info(f"No roll-forward entries arriving at quarter {sel_qtr}.")
        else:
            deferred_cnt  = int(rf_q["deferred_project_flag"].sum()) if "deferred_project_flag" in rf_q.columns else 0
            avg_prob_adj  = float(rf_q["carry_over_probability_adjustment"].mean()) if "carry_over_probability_adjustment" in rf_q.columns else 0.0
            avg_prio_adj  = float(rf_q["carry_over_priority_adjustment"].mean()) if "carry_over_priority_adjustment" in rf_q.columns else 0.0
            avg_penalty   = float(rf_q["unresolved_action_penalty"].mean()) if "unresolved_action_penalty" in rf_q.columns else 0.0

            ca1, ca2, ca3, ca4 = st.columns(4)
            with ca1: st.metric("Deferred Projects", deferred_cnt)
            with ca2: st.metric("Avg Prob Adjustment", f"{avg_prob_adj:+.3f}")
            with ca3: st.metric("Avg Priority Adjustment", f"{avg_prio_adj:+.3f}")
            with ca4: st.metric("Avg Unresolved Penalty", f"{avg_penalty:.3f}")

            with st.expander("Roll-forward detail table", expanded=False):
                show_cols = [c for c in ["project_id", "from_quarter", "to_quarter",
                                          "carry_over_probability_adjustment", "carry_over_priority_adjustment",
                                          "unresolved_action_penalty", "deferred_project_flag", "rollforward_note"]
                             if c in rf_q.columns]
                st.dataframe(rf_q[show_cols].head(200), use_container_width=True, hide_index=True)
    else:
        ui.empty_state("Roll-forward data not available", "fact_quarter_rollforward_inputs missing.")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Learning signals ---
    section("Learning Signals", "Repeated risks / actions / delays \u00b7 confidence adjustment per project")
    if not learn_q.empty:
        rep_flags = ["repeated_risk_flag", "repeated_action_flag", "repeated_delay_flag"]
        present   = [f for f in rep_flags if f in learn_q.columns]
        if present:
            flag_cols = st.columns(len(present))
            for col_f, flag in zip(flag_cols, present):
                cnt   = int(learn_q[flag].sum())
                label = flag.replace("_flag", "").replace("_", " ").title()
                with col_f:
                    pill_cls = "pill-warn" if cnt > 0 else "pill-ok"
                    st.markdown(
                        f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                        f"padding:12px 16px; border-radius:8px; text-align:center;'>"
                        f"<span class='pill {pill_cls}'>{label}</span>"
                        f"<div style='font-size:28px; font-weight:800; color:var(--ink); margin-top:6px;'>{cnt}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        with st.expander("Learning signals detail", expanded=False):
            show_learn = [c for c in ["project_id", "quarter_id", "repeated_risk_flag",
                                       "repeated_action_flag", "repeated_delay_flag",
                                       "confidence_adjustment_signal", "explanation_note"]
                          if c in learn_q.columns]
            st.dataframe(learn_q[show_learn].head(200), use_container_width=True, hide_index=True,
                         column_config={
                             "confidence_adjustment_signal": st.column_config.NumberColumn(
                                 "Confidence Adj.", format="%.4f"),
                         })
    else:
        ui.empty_state("No learning signals", "fact_quarter_learning_signals missing.")

    # --- Delivery rollforward caution + risk_rollforward_waterfall ---
    if not delivery_rf.empty:
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Delivery Caution Roll-Forward", "Caution levels carried from service memory into next quarter")
        col_wfall, col_detail = st.columns([1, 1])
        with col_wfall:
            st.plotly_chart(risk_rollforward_waterfall(delivery_rf), use_container_width=True)
        with col_detail:
            if "source_quarter_id" in delivery_rf.columns and not show_all:
                rf_disp = delivery_rf[delivery_rf["source_quarter_id"] == sel_qtr]
            else:
                rf_disp = delivery_rf
            for level in ["high", "medium", "low"]:
                rf_lv = rf_disp[rf_disp["recommended_caution_level"] == level] if "recommended_caution_level" in rf_disp.columns else pd.DataFrame()
                if rf_lv.empty:
                    continue
                pill = {"high": "pill-crit", "medium": "pill-warn", "low": "pill-ok"}[level]
                with st.expander(f"{level.upper()} caution ({len(rf_lv)} projects)", expanded=(level == "high")):
                    for _, r in rf_lv.head(8).iterrows():
                        st.markdown(
                            f"<div style='font-size:12px; color:var(--ink-soft); padding:4px 0;'>"
                            f"<b style='color:var(--ink);'>{r.get('project_id', _DASH)}</b> "
                            f"{r.get('source_quarter_id','?')} \u2192 {r.get('carry_forward_quarter_id','?')}<br>"
                            f"{r.get('caution_explanation','')}</div>",
                            unsafe_allow_html=True,
                        )

    # --- What this means ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:var(--bg-soft); border:1px solid var(--line); border-radius:10px; "
        "padding:18px 22px; font-size:13px; color:var(--ink-soft); line-height:1.8;'>"
        "<b style='color:var(--ink); font-size:14px;'>What this means for planners</b><br>"
        "Projects with <b style='color:var(--ink);'>repeated risks</b> across quarters receive a "
        "confidence penalty on their action scores \u2014 the engine knows they've been flagged before "
        "and have not been resolved. <b style='color:var(--ink);'>Carry-over caution</b> means the "
        "service memory saw a delivery violation risk in a previous quarter that hasn't been cleared. "
        "High-caution projects should be prioritized on the Actions &amp; Recommendations page."
        "</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE W7-3 — Capacity with Maintenance View
# =============================================================================
elif page == "Capacity & Maintenance":
    page_header("Capacity & Maintenance",
                "Maintenance-aware effective capacity \u00b7 downtime scenarios \u00b7 bottleneck drilldown")

    w7 = _load_w7()
    eff_cap      = w7.get("effective_capacity_v2", pd.DataFrame())
    maint_impact = w7.get("maintenance_impact", pd.DataFrame())
    bottlenecks  = w7.get("bottlenecks", pd.DataFrame())

    ui.data_source_strip([
        ("real",      "fact_effective_capacity_weekly_v2"),
        ("real",      "fact_maintenance_impact_summary"),
        ("real",      "fact_capacity_bottleneck_summary"),
        ("synthetic", "dim_maintenance_policy_synth"),
    ])

    # Filter to selected maintenance scenario
    eff_sel   = eff_cap[eff_cap["scenario"] == w7_maint].copy() if not eff_cap.empty and "scenario" in eff_cap.columns and w7_maint else eff_cap.copy()
    bot_sel   = bottlenecks[bottlenecks["scenario"] == w7_maint].copy() if not bottlenecks.empty and "scenario" in bottlenecks.columns and w7_maint else bottlenecks.copy()
    maint_sel = maint_impact[maint_impact["scenario"] == w7_maint].copy() if not maint_impact.empty and "scenario" in maint_impact.columns and w7_maint else maint_impact.copy()

    # --- KPIs ---
    avg_nom         = float(eff_sel["nominal_available_capacity_hours"].mean()) if not eff_sel.empty and "nominal_available_capacity_hours" in eff_sel.columns else 0.0
    avg_eff         = float(eff_sel["effective_available_capacity_hours"].mean()) if not eff_sel.empty and "effective_available_capacity_hours" in eff_sel.columns else 0.0
    n_bot_wks       = int(eff_sel["bottleneck_flag"].sum()) if not eff_sel.empty and "bottleneck_flag" in eff_sel.columns else 0
    n_bottlenecks   = int(len(bot_sel)) if not bot_sel.empty else 0
    pct_lost        = ((avg_nom - avg_eff) / max(avg_nom, 0.001) * 100) if avg_nom > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("MAINTENANCE SCENARIO", w7_maint or "\u2014", "selected in sidebar", "kpi-slate")
    with c2: kpi("AVG NOMINAL CAP", f"{avg_nom:.1f}h", "per WC-week", "kpi-slate")
    with c3: kpi("AVG EFFECTIVE CAP", f"{avg_eff:.1f}h", "after downtime deduction",
                 "kpi-warn" if pct_lost > 10 else "kpi-ok")
    with c4: kpi("CAPACITY LOST", f"{pct_lost:.1f}%", f"{n_bot_wks} bottleneck WC-weeks",
                 "kpi-accent" if pct_lost > 15 else "kpi-warn" if pct_lost > 5 else "kpi-ok")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Nominal vs effective capacity timeline ---
    section("Nominal vs Effective Capacity", "Select a plant to see capacity timeline with maintenance impact")
    if not eff_sel.empty and "plant" in eff_sel.columns:
        plant_opts_cm = sorted(eff_sel["plant"].dropna().unique().tolist())
        sel_plant_cm  = st.selectbox("Plant", plant_opts_cm, key="cm_plant")
        st.plotly_chart(effective_capacity_timeline(eff_sel, plant=sel_plant_cm, scenario=w7_maint or ""),
                        use_container_width=True)
        st.caption("Green line = nominal capacity. Red line = effective capacity after maintenance deductions. "
                   "Gaps indicate maintenance windows impacting this plant.")
    else:
        ui.empty_state("No capacity data", "fact_effective_capacity_weekly_v2 missing.",
                       "python -m project.src.wave7.runner")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Maintenance impact bar (chart factory) ---
    section("Before/After Maintenance Impact", "Average capacity reduction per work center \u00b7 sorted by impact")
    if not maint_sel.empty:
        st.plotly_chart(maintenance_impact_bar(maint_sel), use_container_width=True)
    else:
        ui.empty_state("No maintenance impact summary", "fact_maintenance_impact_summary missing.")

    # --- Scenario comparison ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Scenario Comparison", "Average capacity lost per maintenance scenario")
    if not eff_cap.empty and "scenario" in eff_cap.columns and "nominal_available_capacity_hours" in eff_cap.columns:
        sc_cmp = (
            eff_cap.groupby("scenario", as_index=False)
            .agg(avg_nominal=("nominal_available_capacity_hours", "mean"),
                 avg_effective=("effective_available_capacity_hours", "mean"),
                 bottleneck_weeks=("bottleneck_flag", "sum"))
        )
        sc_cmp["pct_lost"] = ((sc_cmp["avg_nominal"] - sc_cmp["avg_effective"]) / sc_cmp["avg_nominal"].clip(lower=0.001) * 100).round(2)
        try:
            import plotly.express as _pxcm
            fig_sc = _pxcm.bar(sc_cmp, x="scenario", y="pct_lost",
                               color="pct_lost",
                               color_continuous_scale=["#22c55e", "#f97316", "#ef4444"],
                               range_color=[0, 30],
                               labels={"pct_lost": "% Capacity Lost", "scenario": "Scenario"},
                               title="Capacity Lost to Maintenance by Scenario (%)",
                               template="plotly_dark")
            fig_sc.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22",
                                  font_color="#E2E8F0", coloraxis_showscale=False)
            st.plotly_chart(fig_sc, use_container_width=True)
        except Exception:
            st.dataframe(sc_cmp, use_container_width=True, hide_index=True)

    # --- Bottleneck drilldown ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Bottleneck Drilldown", "Work centers where maintenance creates or worsens capacity bottlenecks")
    if not bot_sel.empty:
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        if "bottleneck_severity" in bot_sel.columns:
            bot_sel = bot_sel.copy()
            bot_sel["_sev_sort"] = bot_sel["bottleneck_severity"].map(sev_order).fillna(9)
            bot_sel = bot_sel.sort_values("_sev_sort").drop(columns="_sev_sort")

        for _, r in bot_sel.head(10).iterrows():
            sev   = str(r.get("bottleneck_severity", "unknown"))
            pill  = {"critical": "pill-crit", "high": "pill-warn", "medium": "pill-info", "low": "pill-ok"}.get(sev, "pill-slate")
            lever = str(r.get("suggested_capacity_lever", ""))
            note  = str(r.get("explanation_note", ""))
            st.markdown(
                f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                f"padding:12px 16px; border-radius:8px; margin-bottom:8px; font-size:13px;'>"
                f"<div style='display:flex; align-items:center; gap:10px; margin-bottom:6px;'>"
                f"<b style='color:var(--ink);'>{r.get('work_center', _DASH)}</b>"
                f"<span style='color:var(--muted);'>@ {r.get('plant', _DASH)}</span>"
                f"<span class='pill {pill}'>{sev.upper()}</span>"
                f"</div>"
                f"<div style='color:var(--ink-soft); font-size:12px; line-height:1.6;'>"
                f"{'<b style=color:var(--ink);>Lever:</b> ' + lever + '<br>' if lever and lever != 'nan' else ''}"
                f"{note}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        with st.expander("Full bottleneck table"):
            disp_cols = [c for c in ["plant", "work_center", "bottleneck_severity",
                                      "top_driver_project_count", "suggested_capacity_lever", "explanation_note"]
                         if c in bot_sel.columns]
            st.dataframe(bot_sel[disp_cols], use_container_width=True, hide_index=True)
    else:
        ui.empty_state("No bottleneck data", "fact_capacity_bottleneck_summary missing.")

    # --- Maintenance impact summary table ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Maintenance Impact Detail", "Per work center \u00b7 before and after maintenance \u00b7 sorted by capacity lost")
    if not maint_sel.empty:
        delta_col = next((c for c in ["delta_avg_overload_hours", "delta_bottleneck_weeks"] if c in maint_sel.columns), None)
        display_cols = [c for c in ["plant", "work_center", "nominal_avg_available_hours",
                                     "effective_avg_available_hours", "avg_maintenance_reduction_hours",
                                     "pct_capacity_lost_to_maintenance", delta_col,
                                     "worst_week", "impact_severity"]
                        if c and c in maint_sel.columns]
        sort_col = "pct_capacity_lost_to_maintenance" if "pct_capacity_lost_to_maintenance" in maint_sel.columns else None
        tbl = maint_sel[display_cols].sort_values(sort_col, ascending=False) if sort_col else maint_sel[display_cols]
        st.dataframe(tbl, use_container_width=True, hide_index=True,
                     column_config={"pct_capacity_lost_to_maintenance": st.column_config.ProgressColumn(
                         "% Capacity Lost", min_value=0.0, max_value=1.0, format="%.1f%%")})
    else:
        ui.empty_state("No maintenance impact data", "fact_maintenance_impact_summary missing.")

    # --- What this means ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:var(--bg-soft); border:1px solid var(--line); border-radius:10px; "
        "padding:18px 22px; font-size:13px; color:var(--ink-soft); line-height:1.8;'>"
        "<b style='color:var(--ink); font-size:14px;'>What this means for planners</b><br>"
        "Maintenance windows reduce <b style='color:var(--ink);'>effective</b> capacity below the "
        "<b style='color:var(--ink);'>nominal</b> figure planners typically see in Anaplan. "
        "The gap between these two lines is the real constraint. Work centers ranked as "
        "<b style='color:var(--ink);'>critical</b> bottlenecks should be addressed before "
        "accepting new projects that route through them. Use the <b style='color:var(--ink);'>suggested lever</b> "
        "column to find the fastest mitigation path per WC."
        "</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE W7-4 — Sourcing & Delivery View
# =============================================================================
elif page == "Sourcing & Delivery":
    page_header("Sourcing & Delivery",
                "Material shortages \u00b7 order-by recommendations \u00b7 delivery feasibility \u00b7 service risk")

    w7 = _load_w7()
    sourcing    = w7.get("sourcing", pd.DataFrame())
    delivery    = w7.get("delivery_commitment", pd.DataFrame())
    rollforward = w7.get("delivery_rollforward", pd.DataFrame())

    ui.data_source_strip([
        ("real",      "fact_scenario_sourcing_weekly"),
        ("real",      "fact_delivery_commitment_weekly"),
        ("real",      "fact_delivery_risk_rollforward"),
        ("synthetic", "requested_delivery_date (week+28d)"),
    ])

    # Filter by scenario
    src_sel = _w7_filter(sourcing, scenario)
    del_sel = _w7_filter(delivery, scenario)

    # --- KPIs ---
    total_src      = int(len(src_sel))
    shortage_cnt   = int(src_sel["shortage_flag"].sum()) if "shortage_flag" in src_sel.columns and total_src > 0 else 0
    pct_shortage   = shortage_cnt / max(total_src, 1) * 100
    total_del      = int(len(del_sel))
    pct_on_time    = float((del_sel["on_time_feasible_flag"] == True).sum()) / max(total_del, 1) * 100 if "on_time_feasible_flag" in del_sel.columns and total_del > 0 else 0.0  # noqa: E712
    avg_svc_risk   = float(del_sel["service_violation_risk"].mean()) if "service_violation_risk" in del_sel.columns and total_del > 0 else 0.0
    high_caution   = int((rollforward["recommended_caution_level"] == "high").sum()) if not rollforward.empty and "recommended_caution_level" in rollforward.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("SHORTAGE ROWS", f"{shortage_cnt:,}", f"{pct_shortage:.1f}% of {total_src:,} sourcing rows",
                 "kpi-accent" if shortage_cnt > 0 else "kpi-ok")
    with c2: kpi("ON-TIME FEASIBLE", f"{pct_on_time:.1f}%", f"scenario: {scenario}",
                 "kpi-ok" if pct_on_time >= 80 else "kpi-warn" if pct_on_time >= 50 else "kpi-accent")
    with c3: kpi("AVG SERVICE RISK", f"{avg_svc_risk:.3f}", "0=clean, 1=critical",
                 "kpi-accent" if avg_svc_risk > 0.4 else "kpi-warn" if avg_svc_risk > 0.2 else "kpi-ok")
    with c4: kpi("HIGH CAUTION ROLLOVER", f"{high_caution}", "critical Q-history projects",
                 "kpi-accent" if high_caution > 0 else "kpi-ok")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Shortage table ---
    section("Shortage Table", "Materials with shortages in this scenario \u00b7 sorted by shortage qty")
    if not src_sel.empty and "shortage_flag" in src_sel.columns:
        short_df = src_sel[src_sel["shortage_flag"] == True].copy()  # noqa: E712
        if not short_df.empty:
            sort_col = "shortage_qty" if "shortage_qty" in short_df.columns else None
            if sort_col:
                short_df = short_df.sort_values(sort_col, ascending=False)
            disp_cols = [c for c in ["plant", "component_material", "week",
                                      "component_demand_qty", "available_qty", "shortage_qty",
                                      "coverage_days_or_weeks", "sourcing_risk_score"]
                         if c in short_df.columns]
            st.dataframe(short_df[disp_cols].head(200), use_container_width=True, hide_index=True,
                         column_config={
                             "shortage_qty": st.column_config.NumberColumn("Shortage Qty", format="%.1f"),
                             "sourcing_risk_score": st.column_config.ProgressColumn(
                                 "Sourcing Risk", min_value=0.0, max_value=1.0, format="%.3f"),
                         })
        else:
            st.success(f"No shortages in scenario: {scenario}")
    else:
        ui.empty_state("No sourcing data", "fact_scenario_sourcing_weekly missing.",
                       "python -m project.src.wave6.runner")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Order-by recommendations ---
    section("Order-By Recommendations", "Materials to order sorted by recommended order date \u00b7 act on these first")
    if not src_sel.empty and "recommended_order_date" in src_sel.columns:
        order_df = src_sel[src_sel["shortage_flag"] == True].copy() if "shortage_flag" in src_sel.columns else src_sel.copy()  # noqa: E712
        order_df = order_df.sort_values("recommended_order_date").dropna(subset=["recommended_order_date"])
        if not order_df.empty:
            ord_cols = [c for c in ["plant", "component_material", "recommended_order_date",
                                     "shortage_qty", "coverage_days_or_weeks", "sourcing_risk_score"]
                        if c in order_df.columns]
            st.dataframe(order_df[ord_cols].head(100), use_container_width=True, hide_index=True,
                         column_config={
                             "sourcing_risk_score": st.column_config.ProgressColumn(
                                 "Sourcing Risk", min_value=0.0, max_value=1.0, format="%.3f"),
                         })
        else:
            st.info("No order recommendations (no shortages).")
    else:
        ui.empty_state("Order-by data not available")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Material criticality view ---
    section("Material Criticality", "Top materials by sourcing risk score across all weeks")
    if not src_sel.empty and "sourcing_risk_score" in src_sel.columns and "component_material" in src_sel.columns:
        mat_crit = (
            src_sel.groupby(["component_material", "plant"], as_index=False)
            .agg(max_risk=("sourcing_risk_score", "max"),
                 shortage_weeks=("shortage_flag", "sum"),
                 total_shortage=("shortage_qty", "sum"))
            .sort_values("max_risk", ascending=False)
            .head(20)
        )
        for _, r in mat_crit.head(8).iterrows():
            risk = float(r["max_risk"])
            pill = "pill-crit" if risk >= 0.8 else "pill-warn" if risk >= 0.5 else "pill-ok"
            shortage_wks = int(r.get("shortage_weeks", 0))
            st.markdown(
                f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                f"padding:10px 14px; border-radius:8px; margin-bottom:6px; font-size:13px;'>"
                f"<b style='color:var(--ink);'>{r['component_material']}</b> "
                f"<span style='color:var(--muted);'>@ {r['plant']}</span>&nbsp;"
                f"<span class='pill {pill}'>risk {risk:.2f}</span>"
                f"<span style='color:var(--muted); font-size:12px;'>&nbsp;{shortage_wks} shortage weeks</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        ui.empty_state("No material criticality data")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # --- Delivery commitment chart + rollforward waterfall ---
    col_del, col_rf = st.columns(2)
    with col_del:
        section("Delivery Commitment", "On-time feasibility \u00b7 service violation risk over time")
        if not del_sel.empty:
            st.plotly_chart(delivery_commitment_chart(del_sel), use_container_width=True)
        else:
            ui.empty_state("No delivery commitment data")
    with col_rf:
        section("Caution Roll-Forward", "Caution levels carried into next quarter")
        if not rollforward.empty:
            st.plotly_chart(risk_rollforward_waterfall(rollforward), use_container_width=True)
        else:
            ui.empty_state("No rollforward data")

    # --- Expedite eligibility ---
    if not del_sel.empty and "expedite_option_flag" in del_sel.columns:
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Expedite Eligibility", "Projects and plants where expedite option is available")
        exp_df = del_sel[del_sel["expedite_option_flag"] == True].copy()  # noqa: E712
        if not exp_df.empty:
            exp_sum = (
                exp_df.groupby(["project_id", "plant"], as_index=False)
                .agg(expedite_weeks=("week", "nunique"),
                     avg_risk=("service_violation_risk", "mean"))
                .sort_values("avg_risk", ascending=False)
                .head(20)
            )
            st.dataframe(exp_sum, use_container_width=True, hide_index=True,
                         column_config={"avg_risk": st.column_config.ProgressColumn(
                             "Avg Risk", min_value=0.0, max_value=1.0, format="%.3f")})
        else:
            st.info("No expedite-eligible rows in this scenario.")

    # --- What this means ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:var(--bg-soft); border:1px solid var(--line); border-radius:10px; "
        "padding:18px 22px; font-size:13px; color:var(--ink-soft); line-height:1.8;'>"
        "<b style='color:var(--ink); font-size:14px;'>What this means for planners</b><br>"
        "A <b style='color:var(--ink);'>shortage row</b> means that projected demand exceeds available stock "
        "plus in-transit for a specific material in a specific week. "
        "The <b style='color:var(--ink);'>order-by date</b> is the latest safe date to place a purchase order "
        "given supplier lead times. Materials shown in red on the criticality view should be escalated immediately. "
        "Delivery feasibility below 80% means more than 1 in 5 delivery commitments are at risk "
        "under the current production and logistics plan."
        "</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE W7-5 — Actions & Recommendations
# =============================================================================
elif page == "Final Actions":
    page_header("Actions & Recommendations",
                "Ranked planner actions \u00b7 confidence \u00b7 risk context \u00b7 why this recommendation?")

    w7 = _load_w7()
    actions_v2  = w7.get("planner_actions_v2", pd.DataFrame())
    risk_v2     = w7.get("integrated_risk_v2", pd.DataFrame())
    smem        = w7.get("service_memory", pd.DataFrame())
    delivery_rf = w7.get("delivery_rollforward", pd.DataFrame())

    ui.data_source_strip([
        ("real", "fact_planner_actions_v2"),
        ("real", "fact_integrated_risk_v2"),
        ("real", "fact_quarter_service_memory"),
        ("real", "fact_delivery_risk_rollforward"),
    ])

    # --- Scenario filter ---
    if actions_v2.empty:
        ui.empty_state("No planner actions found",
                       "fact_planner_actions_v2.csv is missing or empty.",
                       "python -m project.src.wave7.runner")
        st.stop()

    # Enrich with caution level early so filters can use it
    if not delivery_rf.empty and "project_id" in delivery_rf.columns and "recommended_caution_level" in delivery_rf.columns:
        caution_map = delivery_rf.drop_duplicates("project_id").set_index("project_id")["recommended_caution_level"].to_dict()
        actions_v2["caution_level"] = actions_v2["project_id"].map(caution_map).fillna("\u2014")
    else:
        actions_v2["caution_level"] = "\u2014"

    if not risk_v2.empty and "project_id" in risk_v2.columns and "risk_score_v2" in risk_v2.columns:
        risk_map = risk_v2.groupby("project_id")["risk_score_v2"].max().to_dict()
        actions_v2["max_risk"] = actions_v2["project_id"].map(risk_map).fillna(0.0)
    else:
        actions_v2["max_risk"] = 0.0

    # --- Filters ---
    with st.expander("\u25bc Filters", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            scen_opts = sorted(actions_v2["scenario"].dropna().unique().tolist()) if "scenario" in actions_v2.columns else [scenario]
            sel_scen = st.selectbox("Scenario", scen_opts,
                                    index=scen_opts.index(scenario) if scenario in scen_opts else 0,
                                    key="fa_scen")
        with fc2:
            type_opts = ["All"] + sorted(actions_v2["action_type"].dropna().unique().tolist()) if "action_type" in actions_v2.columns else ["All"]
            sel_type = st.selectbox("Action type", type_opts, key="fa_type")
        with fc3:
            plant_opts = ["All"] + sorted(actions_v2["plant"].dropna().unique().tolist()) if "plant" in actions_v2.columns else ["All"]
            sel_plant_fa = st.selectbox("Plant", plant_opts, key="fa_plant")
        with fc4:
            min_conf = st.slider("Min confidence", 0.0, 1.0, 0.0, 0.05, key="fa_conf")

    act_sel = actions_v2[actions_v2["scenario"] == sel_scen].copy() if "scenario" in actions_v2.columns else actions_v2.copy()
    if sel_type != "All" and "action_type" in act_sel.columns:
        act_sel = act_sel[act_sel["action_type"] == sel_type]
    if sel_plant_fa != "All" and "plant" in act_sel.columns:
        act_sel = act_sel[act_sel["plant"] == sel_plant_fa]
    if "confidence" in act_sel.columns:
        act_sel = act_sel[act_sel["confidence"] >= min_conf]

    # --- KPIs ---
    total_acts      = int(len(act_sel))
    high_conf       = int((act_sel["confidence"] >= 0.7).sum()) if "confidence" in act_sel.columns and total_acts > 0 else 0
    act_type_count  = act_sel["action_type"].nunique() if "action_type" in act_sel.columns and total_acts > 0 else 0
    avg_score       = float(act_sel["action_score"].mean()) if "action_score" in act_sel.columns and total_acts > 0 else 0.0
    caution_projects = int(delivery_rf[delivery_rf["recommended_caution_level"].isin(["high", "medium"])]["project_id"].nunique()) if not delivery_rf.empty and "recommended_caution_level" in delivery_rf.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("FILTERED ACTIONS", f"{total_acts:,}", f"scenario: {sel_scen}", "kpi-slate")
    with c2: kpi("HIGH-CONFIDENCE", f"{high_conf:,}", "confidence \u2265 0.7", "kpi-accent" if high_conf else "kpi-ok")
    with c3: kpi("AVG ACTION SCORE", f"{avg_score:.3f}", f"{act_type_count} action types", "kpi-slate")
    with c4: kpi("CAUTION PROJECTS", f"{caution_projects}", "high/medium rollover caution",
                 "kpi-warn" if caution_projects else "kpi-ok")

    # --- Top action cards ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Top Recommended Actions", "Highest action score after filters \u00b7 act on these first")

    if not act_sel.empty and "action_score" in act_sel.columns:
        top3 = act_sel.sort_values("action_score", ascending=False).head(3)
        cols_top = st.columns(3)
        for col, (_, r) in zip(cols_top, top3.iterrows()):
            score = float(r.get("action_score", 0))
            conf  = float(r.get("confidence", 0))
            risk  = float(r.get("max_risk", 0))
            pill  = "pill-ok" if conf >= 0.7 else "pill-warn"
            risk_pill = "pill-crit" if risk >= 0.8 else "pill-warn" if risk >= 0.5 else "pill-ok"
            with col:
                st.markdown(
                    f"<div style='background:var(--bg-soft); border:1px solid var(--line); "
                    f"border-top:3px solid var(--accent-brand); padding:16px; border-radius:10px; height:100%;'>"
                    f"<div style='font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;'>Top action</div>"
                    f"<div style='font-size:18px; font-weight:700; color:var(--accent-brand); margin:6px 0;'>"
                    f"{r.get('action_type', _DASH)}</div>"
                    f"<div style='font-size:13px; color:var(--ink); font-weight:600;'>{r.get('project_id', _DASH)}</div>"
                    f"<div style='font-size:12px; color:var(--muted);'>@ {r.get('plant', _DASH)}</div>"
                    f"<div style='margin-top:10px; display:flex; gap:6px; flex-wrap:wrap;'>"
                    f"<span class='pill {pill}'>conf {conf:.2f}</span>"
                    f"<span class='pill {risk_pill}'>risk {risk:.2f}</span>"
                    f"</div>"
                    f"<div style='margin-top:8px; font-size:12px; color:var(--ink-soft);'>score {score:.3f}</div>"
                    f"<div style='margin-top:6px; font-size:11px; color:var(--muted);'>{str(r.get('reason', ''))[:80]}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    else:
        ui.empty_state("No actions after filters", "Try widening your filter criteria.")

    # --- Charts ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    if not act_sel.empty:
        col_donut, col_bar = st.columns([1, 2])
        with col_donut:
            section("By Action Type", "Distribution of recommended action types")
            st.plotly_chart(action_type_donut(act_sel), use_container_width=True)
        with col_bar:
            section("Top Actions by Score", "Highest-scoring individual recommendations")
            st.plotly_chart(action_score_bar(act_sel, top_n=20), use_container_width=True)

    # --- Confidence / Risk breakdown ---
    if not act_sel.empty and not risk_v2.empty and "risk_score_v2" in risk_v2.columns:
        st.markdown("<hr/>", unsafe_allow_html=True)
        section("Confidence & Risk Breakdown", "How action confidence distributes against risk score")
        risk_sc = _w7_filter(risk_v2, sel_scen) if "scenario" in risk_v2.columns else risk_v2
        if not risk_sc.empty and "project_id" in risk_sc.columns and "action_score" in act_sel.columns and "project_id" in act_sel.columns:
            merged = act_sel[["project_id", "action_score", "confidence", "action_type"]].merge(
                risk_sc.groupby("project_id", as_index=False).agg(
                    risk_score_v2=("risk_score_v2", "max"),
                    top_driver=("top_driver", "first")
                ),
                on="project_id", how="left"
            ).dropna(subset=["risk_score_v2"])
            if not merged.empty:
                import plotly.express as _px
                fig_cr = _px.scatter(
                    merged, x="risk_score_v2", y="confidence",
                    color="action_type", size="action_score",
                    hover_data=["project_id", "top_driver"],
                    labels={"risk_score_v2": "Max Risk Score v2", "confidence": "Action Confidence"},
                    title=f"Confidence vs Risk \u2014 {sel_scen}",
                    template="plotly_dark",
                )
                fig_cr.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#161B22", font_color="#E2E8F0")
                st.plotly_chart(fig_cr, use_container_width=True)
                st.caption("Ideal actions: bottom-right (high risk, high confidence). Bubble size = action score.")

    # --- Ranked table ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Ranked Action Table",
            "All filtered actions \u00b7 sorted by action score \u00b7 top 100")

    if act_sel.empty:
        ui.empty_state("No actions match the current filters")
    else:
        table_cols = [c for c in ["project_id", "plant", "action_type", "action_score",
                                   "confidence", "caution_level", "max_risk",
                                   "material_or_wc", "recommended_target_plant",
                                   "expected_effect", "reason"]
                      if c in act_sel.columns]
        top100 = act_sel.sort_values("action_score", ascending=False).head(100) if "action_score" in act_sel.columns else act_sel.head(100)
        st.dataframe(
            top100[table_cols],
            use_container_width=True, hide_index=True,
            column_config={
                "action_score": st.column_config.ProgressColumn("Action Score", min_value=0.0, max_value=1.0, format="%.3f"),
                "confidence":   st.column_config.ProgressColumn("Confidence",   min_value=0.0, max_value=1.0, format="%.3f"),
                "max_risk":     st.column_config.ProgressColumn("Max Risk",     min_value=0.0, max_value=1.0, format="%.3f"),
            },
        )

    # --- Why this recommendation? drilldown ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    section("Why This Recommendation?",
            "Select a project to see the full reasoning chain + quarter caution context")

    if act_sel.empty:
        ui.empty_state("No actions to explain", "Widen filters above to see projects.")
    else:
        proj_ids = sorted(act_sel["project_id"].dropna().unique().tolist()) if "project_id" in act_sel.columns else []
        if not proj_ids:
            st.info("No project IDs in filtered actions.")
        else:
            sel_proj = st.selectbox("Select project", proj_ids, key="fa_project_sel")
            proj_acts = (
                act_sel[act_sel["project_id"] == sel_proj]
                .sort_values("action_score", ascending=False)
                if "action_score" in act_sel.columns
                else act_sel[act_sel["project_id"] == sel_proj]
            )

            if not proj_acts.empty:
                top_act = proj_acts.iloc[0]
                caution_lvl  = str(top_act.get("caution_level", "\u2014"))
                caution_expl = ""
                if not delivery_rf.empty and "project_id" in delivery_rf.columns:
                    rf_row = delivery_rf[delivery_rf["project_id"] == sel_proj]
                    if not rf_row.empty:
                        caution_expl = str(rf_row.iloc[0].get("caution_explanation", ""))

                # Use ui.why_panel for consistent rendering
                proj_smem = smem[smem["project_id"] == sel_proj] if not smem.empty and "project_id" in smem.columns else pd.DataFrame()
                ui.why_panel(
                    project_id=sel_proj,
                    action_type=str(top_act.get("action_type", "\u2014")),
                    reason=str(top_act.get("reason", "\u2014")),
                    expected_effect=str(top_act.get("expected_effect", "\u2014")),
                    caution_level=caution_lvl,
                    caution_explanation=caution_expl,
                    explanation_trace_json=str(top_act.get("explanation_trace", "")),
                    service_memory_df=proj_smem if not proj_smem.empty else None,
                )

                m1, m2, m3, m4 = st.columns(4)
                with m1: st.metric("Action Score",  f"{float(top_act.get('action_score', 0)):.3f}")
                with m2: st.metric("Confidence",    f"{float(top_act.get('confidence', 0)):.3f}")
                with m3: st.metric("Max Risk v2",   f"{float(top_act.get('max_risk', 0)):.3f}")
                with m4: st.metric("Target Plant",  str(top_act.get("recommended_target_plant", "\u2014")))

                # All actions for this project
                if len(proj_acts) > 1:
                    with st.expander(f"All {len(proj_acts)} actions for this project"):
                        disp_cols = [c for c in table_cols if c in proj_acts.columns]
                        st.dataframe(proj_acts[disp_cols], use_container_width=True, hide_index=True)

    # --- Baseline vs mitigated compare ---
    if not actions_v2.empty and "scenario" in actions_v2.columns:
        pess = actions_v2[actions_v2["scenario"] == "pessimistic"]
        base = actions_v2[actions_v2["scenario"] == "base"]
        if not pess.empty and not base.empty and "action_score" in actions_v2.columns:
            st.markdown("<hr/>", unsafe_allow_html=True)
            section("Baseline vs Mitigated Outcome",
                    "Pessimistic scenario (baseline) vs base scenario (after partial mitigation)")
            cmp_rows = []
            for sc_label, sc_df in [("Pessimistic (baseline)", pess), ("Base (mitigated)", base)]:
                cmp_rows.append({
                    "Scenario": sc_label,
                    "Total Actions": int(len(sc_df)),
                    "Avg Action Score": round(float(sc_df["action_score"].mean()), 3),
                    "High-Conf Actions": int((sc_df["confidence"] >= 0.7).sum()) if "confidence" in sc_df.columns else 0,
                    "Avg Risk": round(float(sc_df["max_risk"].mean()), 3) if "max_risk" in sc_df.columns else "\u2014",
                })
            st.dataframe(pd.DataFrame(cmp_rows), use_container_width=True, hide_index=True)
            st.caption("A lower avg risk score and higher high-confidence action count in the base scenario "
                       "indicates that standard mitigation measures (buffer sourcing, schedule adjustments) "
                       "meaningfully reduce exposure.")

# =============================================================================
# FLOATING CHAT — Clarix assistant bubble (rendered on every page)
# =============================================================================
import base64 as _b64

_logo_b64 = ""
if LOGO.exists():
    with open(LOGO, "rb") as _lf:
        _logo_b64 = _b64.b64encode(_lf.read()).decode()

_CLARIX_DEMOS = {
    "capacity": "Based on the current pipeline, <b>NW01 and NW02</b> are approaching critical load in Q2-Q3 2026. I recommend reviewing expedite options for projects in those plants.",
    "order":    "The top 3 orders to prioritise today are <b>SF-100045, SF-100087, SF-100120</b> — all have high expected value, manageable logistics risk, and available capacity in alternative plants.",
    "material": "The next 6 weeks require sourcing action on <b>rubber gasket compounds</b> (3 plants below safety stock) and <b>cold-rolled coil</b> (lead time risk flagged in NW03). Order-by date: <b>Apr 28</b>.",
    "delivery": "Delivery health across the portfolio is <b>83%</b> on the expected-value scenario. Two projects show service-violation risk — I recommend expediting or rerouting to NW05.",
    "default":  "I'm Clarix, your AI planning assistant. Ask me about capacity, sourcing, deliveries, or which orders to accept. I can also explain any recommendation in one sentence.",
}

import streamlit.components.v1 as _stc

_chat_js = f"""
<script>
(function() {{
  const D = window.parent.document;

  // Remove stale instance from previous reruns
  ['clx-fab','clx-popup','clx-style'].forEach(id => {{ const el = D.getElementById(id); if (el) el.remove(); }});

  // Inject CSS into parent
  const style = D.createElement('style');
  style.id = 'clx-style';
  style.textContent = `
    #clx-fab {{
      position:fixed;bottom:28px;right:28px;width:60px;height:60px;
      border-radius:50%;background:#BB2727;box-shadow:0 4px 20px rgba(187,39,39,.45);
      cursor:pointer;z-index:99999;display:flex;align-items:center;justify-content:center;
      transition:transform .2s,box-shadow .2s;border:2px solid rgba(255,255,255,.15);
    }}
    #clx-fab:hover{{transform:scale(1.08);box-shadow:0 6px 28px rgba(187,39,39,.6);}}
    #clx-fab img{{width:36px;height:36px;object-fit:contain;border-radius:4px;}}
    #clx-popup{{
      position:fixed;bottom:100px;right:28px;width:340px;
      background:#18181B;border:1px solid #2D2D32;border-radius:16px;
      box-shadow:0 8px 40px rgba(0,0,0,.55);z-index:99998;
      display:none;flex-direction:column;overflow:hidden;font-family:Inter,sans-serif;
    }}
    #clx-header{{background:#BB2727;padding:12px 16px;display:flex;align-items:center;gap:10px;}}
    #clx-header img{{width:28px;height:28px;object-fit:contain;border-radius:3px;}}
    #clx-header span{{color:#fff;font-weight:700;font-size:15px;}}
    #clx-header small{{color:rgba(255,255,255,.65);font-size:11px;margin-left:auto;}}
    #clx-msgs{{height:260px;overflow-y:auto;padding:14px 14px 6px;display:flex;flex-direction:column;gap:10px;}}
    .clx-msg{{max-width:88%;font-size:13px;line-height:1.5;padding:9px 12px;border-radius:10px;}}
    .clx-bot{{background:#27272A;color:#E4E4E7;align-self:flex-start;border-bottom-left-radius:3px;}}
    .clx-user{{background:#BB2727;color:#fff;align-self:flex-end;border-bottom-right-radius:3px;}}
    #clx-footer{{padding:10px 12px;border-top:1px solid #2D2D32;display:flex;gap:8px;}}
    #clx-input{{flex:1;background:#27272A;border:1px solid #3D3D42;border-radius:8px;
      color:#E4E4E7;padding:8px 12px;font-size:13px;outline:none;font-family:Inter,sans-serif;}}
    #clx-input::placeholder{{color:#71717A;}}
    #clx-send{{background:#BB2727;border:none;border-radius:8px;color:#fff;
      padding:8px 14px;cursor:pointer;font-size:13px;font-weight:600;transition:background .15s;}}
    #clx-send:hover{{background:#991B1B;}}
    .clx-dot{{width:7px;height:7px;background:#52525B;border-radius:50%;display:inline-block;
      animation:clxb 1.2s infinite;margin:0 2px;}}
    .clx-dot:nth-child(2){{animation-delay:.2s;}}
    .clx-dot:nth-child(3){{animation-delay:.4s;}}
    @keyframes clxb{{0%,80%,100%{{transform:scale(.8);opacity:.5;}}40%{{transform:scale(1.2);opacity:1;}}}}
  `;
  D.head.appendChild(style);

  const LOGO = 'data:image/png;base64,{_logo_b64}';
  const DEMOS = {{
    capacity: `{_CLARIX_DEMOS['capacity']}`,
    order:    `{_CLARIX_DEMOS['order']}`,
    material: `{_CLARIX_DEMOS['material']}`,
    delivery: `{_CLARIX_DEMOS['delivery']}`,
    default:  `{_CLARIX_DEMOS['default']}`,
  }};

  // FAB button
  const fab = D.createElement('div');
  fab.id = 'clx-fab'; fab.title = 'Ask Clarix';
  fab.innerHTML = `<img src="${{LOGO}}" alt="Clarix"/>`;
  D.body.appendChild(fab);

  // Popup
  const popup = D.createElement('div');
  popup.id = 'clx-popup';
  popup.innerHTML = `
    <div id="clx-header">
      <img src="${{LOGO}}" alt="Clarix"/>
      <span>Clarix</span>
      <small>AI Planning Assistant</small>
    </div>
    <div id="clx-msgs">
      <div class="clx-msg clx-bot">Hi! I'm <b>Clarix</b>. Ask me about capacity, orders, sourcing, or delivery health.</div>
    </div>
    <div id="clx-footer">
      <input id="clx-input" type="text" placeholder="Ask Clarix anything…"/>
      <button id="clx-send">&#10148;</button>
    </div>`;
  D.body.appendChild(popup);

  function clxToggle() {{
    const p = D.getElementById('clx-popup');
    const open = p.style.display === 'flex';
    p.style.display = open ? 'none' : 'flex';
    if (!open) D.getElementById('clx-input').focus();
  }}
  function clxSend() {{
    const inp = D.getElementById('clx-input');
    const q = inp.value.trim(); if (!q) return;
    inp.value = '';
    const msgs = D.getElementById('clx-msgs');
    const um = D.createElement('div'); um.className='clx-msg clx-user'; um.textContent=q;
    msgs.appendChild(um);
    const typ = D.createElement('div'); typ.className='clx-msg clx-bot';
    typ.innerHTML='<span class="clx-dot"></span><span class="clx-dot"></span><span class="clx-dot"></span>';
    msgs.appendChild(typ); msgs.scrollTop=msgs.scrollHeight;
    const ql=q.toLowerCase();
    let resp=DEMOS.default;
    if(ql.includes('capac')||ql.includes('plant')||ql.includes('work')) resp=DEMOS.capacity;
    else if(ql.includes('order')||ql.includes('accept')||ql.includes('quote')) resp=DEMOS.order;
    else if(ql.includes('material')||ql.includes('sourc')||ql.includes('stock')||ql.includes('buy')) resp=DEMOS.material;
    else if(ql.includes('deliver')||ql.includes('on-time')||ql.includes('transit')||ql.includes('ship')) resp=DEMOS.delivery;
    setTimeout(()=>{{
      typ.remove();
      const bm=D.createElement('div'); bm.className='clx-msg clx-bot'; bm.innerHTML=resp;
      msgs.appendChild(bm); msgs.scrollTop=msgs.scrollHeight;
    }}, 900);
  }}
  fab.addEventListener('click', clxToggle);
  D.getElementById('clx-send').addEventListener('click', clxSend);
  D.getElementById('clx-input').addEventListener('keydown', e=>{{ if(e.key==='Enter') clxSend(); }});
}})();
</script>
"""

_stc.html(_chat_js, height=0)
