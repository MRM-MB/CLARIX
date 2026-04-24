# frontend_migration_plan.md
## Clarix → Product-Ready Dashboard: Migration Plan

Date: 2026-04-18

---

## Migration philosophy

1. **Adapt over replace.** The clarix backend (data_loader, engine, agent) and CSS system are high quality — keep them entirely.
2. **Consolidate.** Merge 13 flat pages into 7 workflow steps + 2 support pages (What-if, Ask Clarix).
3. **Enrich.** Wire Wave 6/7 processed CSVs into the existing page skeletons; they are already routed via `demo_layer.py`.
4. **Extend charts, don't rewrite.** Add new Plotly factories to `clarix/charts.py` using the existing `_theme()` and color constants.

---

## Global layout

### Current state
- Single `app.py` with inline CSS, 13 pages as `if/elif` blocks
- Sidebar: logo, flat 13-item radio, scenario selector, plant filter, scope summary, Wave 7 contextual filters (conditional), API key status, reset button

### Target state
- Keep single `app.py` (no multi-page restructure needed for hackathon scope)
- Sidebar radio grouped with markdown section headers:
  ```
  ### WORKFLOW
  ○ Overview
  ○ Scope & Pipeline
  ○ Capacity & Maintenance
  ○ Sourcing & Delivery
  ○ Logistics & Disruptions
  ○ Quarter History
  ○ Actions & Recommendations

  ### TOOLS
  ○ What-if planner
  ○ Ask Clarix
  ```
- Sidebar filters: always show Scenario + Plant; show Region always (not conditional); show Quarter + Maintenance scenario only on pages that use them
- Remove: "Bottlenecks" (absorbed into Capacity), "Actions" (merged into Final Actions), "Sourcing & MRP" (merged into Sourcing & Delivery)

---

## App navigation — old → new mapping

| Old page | New page | Migration type |
|----------|----------|----------------|
| Executive overview | **Overview** | ADAPT — add Wave 6/7 KPIs |
| Scope & Region (W7) | **Scope & Pipeline** | ADAPT — add pipeline breakdown |
| Capacity planner | **Capacity & Maintenance** tab: Heatmap | ADAPT — merge |
| Bottlenecks | **Capacity & Maintenance** tab: Bottlenecks | ADAPT — tab it |
| Capacity & Maintenance (W7) | **Capacity & Maintenance** tab: Maintenance | ADAPT — tab it |
| Sourcing & MRP | **Sourcing & Delivery** tab: MRP | ADAPT — merge |
| Sourcing & Delivery (W7) | **Sourcing & Delivery** tab: Delivery | ADAPT — tab it |
| Logistics & Disruptions (W7) | **Logistics & Disruptions** | ADAPT — enrich |
| Quarter History (W7) | **Quarter History** | ADAPT — add charts |
| Actions (W6) | *(removed)* | DEPRECATE |
| Final Actions (W7) | **Actions & Recommendations** | ADAPT — enrich |
| What-if planner | **What-if planner** | KEEP as-is |
| Ask Clarix | **Ask Clarix** | KEEP as-is |

---

## Page-level migration details

### 1. Overview (was: Executive overview)
**Changes:**
- Keep existing 4 KPIs (Pipeline EUR, Expected EUR, Peak Util, Bottleneck count)
- Add second KPI row from `demo_layer.get_demo_summary()`:
  - Avg risk score, High-priority actions count, Shortage rows, Bottleneck count (Wave 6)
- Add conditional `st.info` banner if `demo_layer` processed files are missing (graceful fallback)
- Keep: pipeline funnel, scenario compare bar, demand treemap
- Add: `_demo_layer_available` guard so page degrades gracefully without Wave 6/7 data

**New data needed:** `get_demo_summary()` from `demo_layer` (already in app.py, just not wired to overview)

---

### 2. Scope & Pipeline (was: Scope & Region)
**Changes:**
- Keep existing region scope table
- Add: project count by probability tier (donut or bar)
- Add: pipeline timeline (stacked bar by month, probability-weighted vs all-in)
- Add: plant-scope map (which plants are in active scope)
- Wire `dim_project_priority` to show revenue tier breakdown

**New chart needed:** `pipeline_timeline_bar()` in `charts.py`

---

### 3. Capacity & Maintenance (merge of 3 pages)
**Structure:** `st.tabs(["Heatmap", "Bottlenecks", "Maintenance Impact"])`

**Tab: Heatmap** — migrate from "Capacity planner" page unchanged

**Tab: Bottlenecks** — migrate from "Bottlenecks" page unchanged

**Tab: Maintenance Impact** — migrate from Wave 7 "Capacity & Maintenance" page; enrich with:
- Maintenance scenario selector (already in sidebar)
- `fact_maintenance_impact_summary` bar chart (avg reduction hours by plant/WC)
- `fact_effective_capacity_weekly_v2` bottleneck timeline
- KPIs: worst week, pct capacity lost, delta overload hours

**New chart needed:** `maintenance_impact_bar()` and `effective_capacity_timeline()` in `charts.py`

---

### 4. Sourcing & Delivery (merge of 2 pages)
**Structure:** `st.tabs(["MRP Recommendations", "Delivery Commitments"])`

**Tab: MRP Recommendations** — migrate from "Sourcing & MRP" page unchanged

**Tab: Delivery Commitments** — migrate from Wave 7 "Sourcing & Delivery" page; enrich with:
- `fact_delivery_commitment_weekly` line chart (committed vs required)
- `fact_scenario_sourcing_weekly` shortage flag summary
- Order-by urgency KPIs

**New chart needed:** `delivery_commitment_chart()` in `charts.py`

---

### 5. Logistics & Disruptions (was: Wave 7 draft page L941)
**Changes:**
- Enrich with `fact_delivery_risk_rollforward` — show carry-over risk trend
- Add disruption scenario selector (links to maintenance scenario sidebar filter)
- Keep existing logistics routing table if present

**New chart needed:** `risk_rollforward_waterfall()` in `charts.py`

---

### 6. Quarter History (was: Wave 7 draft page L1369)
**Changes:**
- Surface `fact_quarter_learning_signals` as trend table
- Surface `fact_quarter_service_memory` carry-over caution flags
- Add quarter-over-quarter comparison (selected quarter vs prior)
- Highlight `carry_over_service_caution_flag = True` rows in red

**New chart needed:** `learning_signals_table()` (styled dataframe, no new Plotly chart needed)

---

### 7. Actions & Recommendations (was: Final Actions + deprecating Actions)
**Changes:**
- Load `fact_planner_actions_v2.csv` directly (already done in demo_layer)
- Surface `explanation_trace` JSON: show `top_driver`, `action_selected`, `maint_severity` inline
- Add action_score bar chart sorted descending
- Add action type distribution donut
- Filter by scope_id, scenario, quarter_id (already in sidebar)
- KPIs: total actions, maintenance-specific actions count, avg confidence, avg score
- Remove old "Actions" page (Wave 6 version)

**New chart needed:** `action_score_bar()` and `action_type_donut()` in `charts.py`

---

## Data adapters

### Current
```python
# app.py top-level
data = get_data()  # clarix canonical tables — @st.cache_resource

# Wave 7 pages (uncached, inline)
w7 = load_all_processed()
```

### Target
```python
# Keep as-is
data = get_data()

# Add cached wrapper (currently missing)
@st.cache_data(show_spinner=False)
def get_w7_data():
    return load_all_processed()

w7 = get_w7_data()
```

This prevents re-reading 15 CSVs on every page navigation.

---

## Reusable component migrations

| Component | From | To | Change |
|-----------|------|----|--------|
| `page_header()` | app.py L433 | Keep verbatim | None |
| `kpi()` | app.py L454 | Keep verbatim | None |
| `section()` | app.py L465 | Keep verbatim | None |
| `utilization_heatmap()` | charts.py L75 | Keep verbatim | None |
| `utilization_lines()` | charts.py L95 | Keep verbatim | None |
| `scenario_compare_bar()` | charts.py L116 | Keep verbatim | None |
| `pipeline_funnel()` | charts.py L137 | Keep verbatim | None |
| `plant_demand_treemap()` | charts.py L154 | Keep verbatim | None |
| `sourcing_table_fig()` | charts.py L170 | Keep verbatim | None |
| `kpi_donut()` | charts.py L196 | Keep verbatim | None |

---

## New chart types to add to `clarix/charts.py`

| Function | Used on page | Data source |
|----------|-------------|-------------|
| `pipeline_timeline_bar(pipe_df)` | Scope & Pipeline | `fact_pipeline_quarterly` |
| `maintenance_impact_bar(maint_df)` | Capacity & Maintenance | `fact_maintenance_impact_summary` |
| `effective_capacity_timeline(eff_cap_df)` | Capacity & Maintenance | `fact_effective_capacity_weekly_v2` |
| `delivery_commitment_chart(commit_df)` | Sourcing & Delivery | `fact_delivery_commitment_weekly` |
| `risk_rollforward_waterfall(rollforward_df)` | Logistics & Disruptions | `fact_delivery_risk_rollforward` |
| `action_score_bar(actions_df)` | Actions & Recommendations | `fact_planner_actions_v2` |
| `action_type_donut(actions_df)` | Actions & Recommendations | `fact_planner_actions_v2` |

All new functions must use `_theme()` and the existing color constants. Estimated: 150–200 lines.

---

## Styling migration

No CSS changes needed. The existing CSS system is complete and well-organized. The only update is removing the conditional Wave 7 filter appearance/disappearance from the sidebar (always show region, conditionally show quarter/maintenance).

---

## Missing features to add

| Feature | Priority | Page | Effort |
|---------|----------|------|--------|
| `@st.cache_data` wrapper for `load_all_processed()` | HIGH | All Wave 7 pages | 5 min |
| Graceful degradation banners when CSVs missing | HIGH | All pages | 20 min |
| Wave 6/7 KPI row on Overview | HIGH | Overview | 30 min |
| Action score bar chart | HIGH | Actions | 45 min |
| `explanation_trace` JSON expansion | HIGH | Actions | 30 min |
| Pipeline timeline chart | MEDIUM | Scope & Pipeline | 45 min |
| Maintenance impact bar | MEDIUM | Capacity & Maintenance | 45 min |
| Delivery commitment chart | MEDIUM | Sourcing & Delivery | 45 min |
| `st.tabs()` consolidation (3 pages → 1) | MEDIUM | Capacity & Maintenance, Sourcing & Delivery | 60 min |
| Risk rollforward waterfall | LOW | Logistics & Disruptions | 60 min |
| Learning signals trend table | LOW | Quarter History | 30 min |
| Sidebar grouping with section headers | LOW | Global | 15 min |

**Total estimated effort:** ~7 hours of focused implementation work

---

## Execution order (recommended)

1. Add `@st.cache_data` for `load_all_processed()` — unblocks all Wave 7 pages
2. Add graceful degradation guards — makes demo safe even with missing CSVs
3. Wire Wave 6/7 KPIs to Overview — immediate visual impact
4. Add action score bar + explanation_trace to Actions page — showpiece for demo
5. Consolidate pages with `st.tabs()` — reduces nav clutter
6. Add new chart functions to `charts.py` — one per page
7. Update sidebar grouping — cosmetic but narrative-improving
