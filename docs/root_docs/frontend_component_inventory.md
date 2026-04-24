# frontend_component_inventory.md
## Frontend Component Inventory

Date: 2026-04-18

---

## Component classification

For each component: name, location, type, inputs, outputs, reuse status, and any migration notes.

---

## Layout components

| Component | Location | Type | Inputs | Outputs | Status | Migration notes |
|-----------|----------|------|--------|---------|--------|-----------------|
| `page_header(title, subtitle)` | app.py L433 | Layout | `title: str`, `subtitle: str` | Branded page title strip with logo + divider | **KEEP** | Used on every page; no change needed |
| `kpi(label, value, sub, style)` | app.py L454 | Layout | `label`, `value`, `sub`, CSS class string | KPI card HTML block | **KEEP** | Styles: `kpi-accent`, `kpi-warn`, `kpi-ok`, `kpi-slate` |
| `section(title, sub)` | app.py L465 | Layout | `title: str`, `sub: str` | Section header with red accent bar | **KEEP** | |
| CSS design tokens | app.py L59–263 | Style | CSS variables in `:root` | Dark theme for all elements | **KEEP** | Variables: `--accent`, `--ink`, `--slate-*`, `--bg*`, `--ok`, `--line`, `--muted` |
| `.pill` classes | app.py CSS | Style | HTML class | Status badges: `pill-ok`, `pill-warn`, `pill-crit`, `pill-slate`, `pill-info` | **KEEP** | Used inline in Bottlenecks, What-if, Actions pages |

---

## Chart components (`clarix/charts.py`)

### Existing — all KEEP

| Function | Signature | Chart type | Used on | Notes |
|----------|-----------|------------|---------|-------|
| `utilization_heatmap(util, top_n, title)` | `pd.DataFrame → go.Figure` | Heatmap | Capacity & Maintenance (Heatmap tab) | `UTIL_SCALE` colorscale; ranked by peak util |
| `utilization_lines(util, work_center, title)` | `pd.DataFrame, str → go.Figure` | Overlaid bar chart | Capacity & Maintenance (Heatmap tab, drilldown) | Available vs demand bars + threshold lines |
| `scenario_compare_bar(rows)` | `list[dict] → go.Figure` | Bar chart | Overview | Colors by util level |
| `pipeline_funnel(pipe)` | `pd.DataFrame → go.Figure` | Funnel | Overview, Scope & Pipeline | All-in → expected → high-confidence |
| `plant_demand_treemap(pipe)` | `pd.DataFrame → go.Figure` | Treemap | Overview | Hierarchical: plant → type → material |
| `sourcing_table_fig(sourcing)` | `pd.DataFrame → go.Figure` | Plotly Table | Sourcing & Delivery (MRP tab) | Falls back to annotation if empty |
| `kpi_donut(value, total, label, color)` | `float, float, str, str → go.Figure` | Donut | Available for reuse | Hole=0.75, centered pct + label |

### New — to ADD in Wave 1

| Function | Signature | Chart type | Used on | Description |
|----------|-----------|------------|---------|-------------|
| `pipeline_timeline_bar(pipe_qtrly)` | `pd.DataFrame → go.Figure` | Stacked bar | Scope & Pipeline | Quarterly pipeline expected vs all-in by plant; x=quarter, y=expected_qty, color=plant |
| `maintenance_impact_bar(maint_df)` | `pd.DataFrame → go.Figure` | Grouped bar | Capacity & Maintenance (Maintenance tab) | avg_maintenance_reduction_hours by plant × scenario; colored by impact_severity |
| `effective_capacity_timeline(eff_cap_df, plant, scenario)` | `pd.DataFrame, str, str → go.Figure` | Line + area | Capacity & Maintenance (Maintenance tab) | effective_available_capacity_hours vs total_load_hours over weeks; bottleneck_flag as red markers |
| `delivery_commitment_chart(commit_df)` | `pd.DataFrame → go.Figure` | Line chart | Sourcing & Delivery (Delivery tab) | committed vs required delivery by week; shortage flag as red dots |
| `risk_rollforward_waterfall(rollforward_df)` | `pd.DataFrame → go.Figure` | Waterfall | Logistics & Disruptions | Carry-over risk delta quarter over quarter |
| `action_score_bar(actions_df, top_n)` | `pd.DataFrame, int → go.Figure` | Horizontal bar | Actions & Recommendations | Top N actions by adjusted_action_score; bars colored by action_type; x-axis 0–1 |
| `action_type_donut(actions_df)` | `pd.DataFrame → go.Figure` | Donut | Actions & Recommendations | Distribution of action_type counts |

**Implementation note:** All new chart functions must:
- Import from existing `_theme()`, palette constants
- Return `go.Figure`
- Handle empty input with `_theme(go.Figure(), title="No data")`
- Follow existing hover template pattern

---

## Data loading components

| Component | Location | Type | Inputs | Outputs | Status | Notes |
|-----------|----------|------|--------|---------|--------|-------|
| `load_canonical(xlsx_path)` | `clarix/data_loader.py` | `@lru_cache` function | Excel path | `CanonicalData` (8 DataFrames) | **KEEP** | Parquet cache in `data/.clarix_cache/` |
| `get_data()` | app.py L270 | `@st.cache_resource` | — | `CanonicalData` | **KEEP** | |
| `get_utilization(scenario, plant)` | app.py L275 | `@st.cache_data` | scenario, plant | utilization DataFrame | **KEEP** | |
| `get_bottlenecks(scenario, plant)` | app.py L280 | `@st.cache_data` | scenario, plant | bottleneck DataFrame | **KEEP** | |
| `get_sourcing(scenario, plant, top_n)` | app.py L285 | `@st.cache_data` | scenario, plant, top_n | sourcing DataFrame | **KEEP** | |
| `load_all_processed()` | `project/src/app/demo_layer.py` | Function | optional dir paths | dict[str, DataFrame] (15 keys) | **ADAPT** | Needs `@st.cache_data` wrapper in app.py — currently re-reads CSVs on every page render |
| `get_demo_summary(data)` | `project/src/app/demo_layer.py` | Function | dict[str, DataFrame] | KPI dict | **ADAPT** | Wire to Overview page |

**New wrapper to add (app.py):**
```python
@st.cache_data(show_spinner=False)
def get_w7_data():
    if _DEMO_LAYER_AVAILABLE:
        return load_all_processed()
    return {}
```

---

## State management components

| Key | Type | Initialized | Used on | Notes |
|-----|------|-------------|---------|-------|
| `st.session_state.basket` | `list[dict]` | What-if planner (with demo seed) | What-if planner | Each item: plant, material, period_date, qty, probability_frac, spread_months |
| `st.session_state.chat` | `list[dict]` | Ask Clarix (`[]`) | Ask Clarix | Format: `{"role": "user"|"assistant"|"tool", "content": str}` |
| `st.session_state.feas_result` | `dict` | What-if planner (on run) | What-if planner | Keys: `per_project`, `per_quarter`, `summary` |

---

## Engine components (`clarix/engine.py`)

| Function | Inputs | Outputs | Used on | Status |
|----------|--------|---------|---------|--------|
| `build_demand_by_wc_week(data, scenario, ...)` | CanonicalData, scenario | long DataFrame (WC, plant, year, week, demand_hours) | Internal | **KEEP** |
| `build_utilization(data, scenario, plant)` | CanonicalData, scenario, plant | utilization DataFrame | Capacity, Bottlenecks | **KEEP** |
| `detect_bottlenecks(util_df)` | utilization DataFrame | ranked bottleneck DataFrame | Bottlenecks | **KEEP** |
| `sourcing_recommendations(data, scenario, plant, top_n)` | CanonicalData | sourcing DataFrame | Sourcing & MRP | **KEEP** |
| `explain_constraint(data, work_center, scenario, year, week)` | CanonicalData, str | dict with top_projects | Bottlenecks | **KEEP** |
| `list_addable_materials(data, plant)` | CanonicalData, str | materials DataFrame | What-if planner | **KEEP** |
| `project_feasibility(data, scenario, basket, plant)` | CanonicalData, scenario, basket | dict with per_project, per_quarter, summary | What-if planner | **KEEP** |
| `build_utilization_with_basket(data, scenario, basket, plant)` | CanonicalData, basket | utilization DataFrame | What-if planner | **KEEP** |

---

## Agent components (`clarix/agent.py`)

| Component | Description | Status |
|-----------|-------------|--------|
| `TOOLS` list | 5 tool schemas for Claude API | **KEEP** |
| `SYSTEM_PROMPT` | CLARIX persona + rules | **KEEP** |
| `call_tool(name, args, data)` | Dispatches to engine functions | **KEEP** |
| `run_agent(user_msg, data, history, model, max_iter)` | Full tool-use loop | **KEEP** |
| `_fallback_planner(user_msg, data, trace)` | Deterministic fallback (no API key) | **KEEP** |
| `AgentTurn` dataclass | Trace record | **KEEP** |

---

## Wave 6/7 data components (via `demo_layer.py`)

| Key in `load_all_processed()` | CSV file | Used on page |
|-------------------------------|---------|--------------|
| `risk_base` | `fact_integrated_risk_base.csv` | Overview (KPIs), Actions |
| `sourcing` | `fact_scenario_sourcing_weekly.csv` | Sourcing & Delivery |
| `logistics` | `fact_scenario_logistics_weekly.csv` | Logistics & Disruptions |
| `bottlenecks` | `fact_capacity_bottleneck_summary.csv` | Overview (KPIs) |
| `action_policy` | `dim_action_policy.csv` | Actions |
| `quality_flags` | `fact_data_quality_flags.csv` | Actions (penalties) |
| `project_priority` | `dim_project_priority.csv` | Scope & Pipeline |
| `region_scope` | `dim_region_scope.csv` | Scope & Pipeline, sidebar |
| `pipeline_quarterly` | `fact_pipeline_quarterly.csv` | Scope & Pipeline |
| `effective_capacity_v2` | `fact_effective_capacity_weekly_v2.csv` | Capacity & Maintenance |
| `delivery_commitment` | `fact_delivery_commitment_weekly.csv` | Sourcing & Delivery |
| `service_memory` | `fact_quarter_service_memory.csv` | Quarter History |
| `delivery_rollforward` | `fact_delivery_risk_rollforward.csv` | Logistics & Disruptions |
| `maintenance_impact` | `fact_maintenance_impact_summary.csv` | Capacity & Maintenance |
| `learning_signals` | `fact_quarter_learning_signals.csv` | Quarter History |
| `rollforward_inputs` | `fact_quarter_rollforward_inputs.csv` | Quarter History |
| `planner_actions_v2` | `fact_planner_actions_v2.csv` | Actions & Recommendations |
| `service_level_policy` | `dim_service_level_policy_synth.csv` | Scope & Pipeline (synthetic badge) |

---

## Component count summary

| Category | Keep | Adapt | New | Deprecate |
|----------|------|-------|-----|-----------|
| Layout helpers | 5 | 0 | 0 | 0 |
| Chart functions | 7 | 0 | 7 | 0 |
| Data loading | 4 | 2 | 1 | 0 |
| State management | 3 | 0 | 1 | 0 |
| Engine functions | 8 | 0 | 0 | 0 |
| Agent components | 5 | 0 | 0 | 0 |
| **Total** | **32** | **2** | **9** | **0** |

All 9 new components are additive (new chart types + 1 cached data wrapper). Zero components require rewriting from scratch.
