# frontend_audit.md
## Clarix Frontend Audit — Wave 0

Audit date: 2026-04-18
Auditor: Wave 0 agent
Scope: `clarix/` (4 modules) + `app.py` (13 pages/sections)

---

## Methodology

Each row is:
`MODULE_NAME | purpose | current status | UX quality | technical quality | architectural fit | action | rationale`

Ratings: **High / Medium / Low**
Actions: **KEEP / ADAPT / DEPRECATE / REPLACE**

---

## Backend modules (`clarix/`)

| Module | Purpose | Status | UX quality | Technical quality | Architectural fit | Action | Rationale |
|--------|---------|--------|-----------|-------------------|-------------------|--------|-----------|
| `clarix/data_loader.py` | Reads hackathon_dataset.xlsx → 8 canonical DataFrames; LRU + parquet cache | Working | N/A | **High** — clean sheet builders, NaN handling, `@lru_cache`, parquet fallback | **High** — feeds engine and chart layer; adapts cleanly alongside `demo_layer.py` for Wave 6/7 CSVs | **KEEP** | Gold-standard data loading; parquet cache keeps startup fast; nothing to replace |
| `clarix/engine.py` | Capacity calc, scenario engine (4 scenarios + Monte Carlo), bottleneck detection, sourcing/MRP, what-if / project feasibility | Working | N/A | **High** — vectorised pandas, seeded RNG, clean abstractions | **High** — is the compute backbone for the five pipeline-facing pages | **KEEP** | Core differentiator; what-if + project feasibility are showpiece features for the demo |
| `clarix/charts.py` | Plotly chart factories with consistent dark theme (color palette, `_theme()` helper, 7 chart types) | Working | **High** — coherent dark palette, semantic colors, clean hover templates | **High** — reusable factory pattern, easy to extend | **Medium** — covers pipeline/capacity charts; Wave 6/7 pages need 4–5 new chart types | **ADAPT** | Extend with maintenance timeline, risk heatmap, action-score bar, and rollforward waterfall using the same `_theme()` and color system |
| `clarix/agent.py` | Claude tool-use loop (5 tools); graceful fallback to deterministic planner mode when no API key | Working | **High** — structured tool trace, clear fallback messages | **High** — clean agentic loop, `@dataclass` trace | **High** — "Ask Clarix" page is primary AI showcase for demo judges | **KEEP** | Best-in-class hackathon differentiator; keep and expose more prominently |

---

## Styling system (`app.py`, lines 59–263)

| Component | Purpose | Status | UX quality | Technical quality | Architectural fit | Action | Rationale |
|-----------|---------|--------|-----------|-------------------|-------------------|--------|-----------|
| CSS / design tokens | Dark theme (GitHub-inspired), Inter font, KPI cards, pills, section headers, sidebar styles, chat bubbles, scrollbar | Working | **High** — professional, consistent, demo-safe on projectors | **High** — CSS variables for all colors, well-organized blocks | **High** — applies globally; all pages benefit | **KEEP** | Best asset in the codebase; no reason to change |
| Color palette (`clarix/charts.py`) | Semantic color constants (ACCENT, OK_GREEN, SLATE family, INK family) | Working | **High** | **High** | **High** | **KEEP** | Used in both CSS and Plotly; consistency is a strength |

---

## Navigation & app structure

| Component | Purpose | Status | UX quality | Technical quality | Architectural fit | Action | Rationale |
|-----------|---------|--------|-----------|-------------------|-------------------|--------|-----------|
| Sidebar radio (13 items) | Page navigation | Working | **Medium** — 13 flat items is unwieldy; no grouping or workflow cues | **Medium** — works but no grouping | **Low** — doesn't reflect the 9-step workflow story | **ADAPT** | Group into 3 labelled sections: "Engine" (clarix-native pages), "Workflow" (steps 1–7), "Copilot" (Ask Clarix); reorder to match workflow causality |
| Sidebar scenario selector | Drives all clarix-engine pages | Working | **High** | **High** | **High** | **KEEP** | |
| Sidebar Wave 7 contextual filters (region / quarter / maintenance scenario) | Shown only on Wave 7 pages | Working | **Medium** — appears/disappears abruptly | **Medium** | **Medium** — correct concept, rough execution | **ADAPT** | Always show region selector; hide quarter/maintenance only when irrelevant to avoid jarring layout shifts |
| `page_header()` helper | Branded page title strip | Working | **High** | **High** | **High** | **KEEP** | |
| `kpi()` helper | Metric card | Working | **High** | **High** | **High** | **KEEP** | |
| `section()` helper | Section divider with red accent bar | Working | **High** | **High** | **High** | **KEEP** | |

---

## Pages

| Page | Purpose | Status | UX quality | Technical quality | Architectural fit | Action | Rationale |
|------|---------|--------|-----------|-------------------|-------------------|--------|-----------|
| **Executive overview** (L474) | 4 KPIs, pipeline funnel, scenario compare bar, demand treemap | Working | **High** | **High** | **High** — maps to "Overview" family | **ADAPT** | Add Wave 6/7 KPIs (avg risk score, open actions, planner action count) via `demo_layer.get_demo_summary()` |
| **Capacity planner** (L532) | Utilization heatmap, top-N slider, WC drilldown line chart | Working | **High** | **High** | **High** — maps to "Capacity & Maintenance" | **ADAPT** | Merge with or tab alongside the Wave 7 "Capacity & Maintenance" page so capacity data is not split across two pages |
| **Bottlenecks** (L570) | Ranked bottleneck list (ProgressColumn), explain-constraint auto-analysis | Working | **High** | **High** | **Medium** — overlaps with "Capacity & Maintenance" | **ADAPT** | Move to a tab inside "Capacity & Maintenance"; too much value to deprecate |
| **Sourcing & MRP** (L630) | BOM-backed component order recommendations, urgent counter | Working | **High** | **High** | **High** — maps to "Sourcing & Delivery" | **ADAPT** | Merge into Wave 7 "Sourcing & Delivery" page as the "Live MRP" tab |
| **What-if planner** (L671) | Basket-based project feasibility; quarter-by-quarter impact table | Working | **High** — richest interactive feature | **High** | **Medium** — no clear position in workflow | **KEEP** | Best interactive feature; position it between "Pipeline" and "Capacity" in the workflow nav |
| **Ask Clarix** (L883) | Chat agent with 5 tools + suggested questions + trace display | Working | **High** | **High** | **High** | **KEEP** | Primary AI/demo showpiece |
| **Logistics & Disruptions** (L941) | Wave 6 logistics/disruption page (delivery risk, reroute scenarios) | Draft — partial Wave 6 implementation | **Medium** | **Medium** | **High** — maps to "Logistics & Disruptions" family | **ADAPT** | Enrich with `fact_delivery_commitment_weekly` and `fact_delivery_risk_rollforward` data |
| **Actions** (L1078) | Wave 6 planner actions page | Draft | **Medium** | **Medium** | **Medium** — superseded by Wave 7 Final Actions | **DEPRECATE** | Replaced by "Final Actions" (Wave 7); merge any unique content there |
| **Scope & Region** (L1270) | Region scoping, active scope display, plant list | Draft | **Medium** | **Medium** | **High** — workflow step 1 | **ADAPT** | Add pipeline breakdown by region; show scope → project → factory hierarchy clearly |
| **Quarter History** (L1369) | Learning signals, service memory carry-over caution | Draft | **Medium** | **Medium** | **High** — workflow step 2 | **ADAPT** | Surface `fact_quarter_learning_signals` and `fact_quarter_service_memory` with trend charts |
| **Capacity & Maintenance** (L1492) | Effective capacity v2, maintenance impact summary | Draft | **Medium** | **Medium** | **High** — workflow step 3 | **ADAPT** | Consolidate with clarix Capacity planner + Bottlenecks into tabbed layout |
| **Sourcing & Delivery** (L1623) | Delivery commitments, sourcing scenario comparison | Draft | **Medium** | **Medium** | **High** — workflow step 4 | **ADAPT** | Consolidate with clarix Sourcing & MRP; split into "Sourcing" and "Delivery" tabs |
| **Final Actions** (L1741) | `fact_planner_actions_v2` — scored, ranked planner recommendations | Draft | **Medium** | **Medium** | **High** — workflow endpoint | **ADAPT** | Surface `explanation_trace` JSON, action_score bar, scope/quarter filters prominently |

---

## State management

| Component | Purpose | Status | UX quality | Technical quality | Architectural fit | Action | Rationale |
|-----------|---------|--------|-----------|-------------------|-------------------|--------|-----------|
| `st.session_state.basket` | What-if project basket | Working | Good | Good | Good | **KEEP** | |
| `st.session_state.chat` | Chat history | Working | Good | Good | Good | **KEEP** | |
| `st.session_state.feas_result` | Feasibility result cache | Working | Good | Good | Good | **KEEP** | |
| `st.cache_resource` / `st.cache_data` | Data and computation caching | Working | N/A | **High** | **High** | **KEEP** | Extend patterns to Wave 6/7 data |

---

## Data integration

| Component | Purpose | Status | UX quality | Technical quality | Architectural fit | Action | Rationale |
|-----------|---------|--------|-----------|-------------------|-------------------|--------|-----------|
| `clarix/data_loader.load_canonical()` | Loads Excel → canonical tables | Working | N/A | **High** | **High** | **KEEP** | |
| `project/src/app/demo_layer.load_all_processed()` | Loads Wave 6/7 CSVs | Working (post-fix) | N/A | **Medium** | **High** | **ADAPT** | Add `@st.cache_data` wrapper in app.py; currently loaded without caching on Wave 7 pages |
| `project/src/app/demo_layer.get_demo_summary()` | KPI summary dict from processed data | Working | N/A | **Medium** | **High** | **ADAPT** | Expose on Executive overview |
| `project/src/app/demo_layer.derive_planner_actions()` | Derives planner actions from risk_base + policy | Working | N/A | **Medium** | **Medium** — Wave 7 uses `fact_planner_actions_v2.csv` directly | **DEPRECATE** | Superseded by `build_fact_planner_actions_v2`; app.py should load the CSV, not re-derive |

---

## Summary counts

| Action | Count |
|--------|-------|
| KEEP | 11 |
| ADAPT | 12 |
| DEPRECATE | 2 |
| REPLACE | 0 |

**Key finding:** Nothing needs to be replaced from scratch. The clarix backend (data_loader, engine, agent) is production-quality and should be fully preserved. The styling system is excellent. The main work is consolidating 13 flat pages into a coherent 7-step workflow, enriching existing pages with Wave 6/7 data, and extending `charts.py` with 4–5 new chart types.
