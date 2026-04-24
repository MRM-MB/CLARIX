# component_map_final.md
## Clarix — Final Component Map

Date: 2026-04-18  
Wave: 5 (Final)

---

## Clarix Package Components

### clarix/ui.py — UI Helpers

| Component | Function | Status | Used By |
|-----------|----------|--------|---------|
| KPI card | `st.markdown` + CSS `.kpi-*` classes (inline in app.py) | ACTIVE | All pages (Overview, classic pages) |
| Data source strip | `data_source_strip(sources)` | ACTIVE | All Wave 2–5 pages |
| Empty state | `empty_state(title, message, hint)` | ACTIVE | All fallback/missing-data paths |
| Assumption panel | `assumption_panel(text)` | ACTIVE | Scope & Region, Quarter History, Logistics |
| Why panel | `why_panel(project_id, action_type, confidence, reason, expected_effect, trace, context)` | ACTIVE | Final Actions |
| Trace dict renderer | `_render_trace_dict(trace)` | ACTIVE | Inside why_panel (internal) |
| Planner mode banner | `planner_mode_banner()` | ACTIVE | Ask Clarix (no API key path) |

### clarix/charts.py — Chart Factories

| Component | Function | Status | Used By |
|-----------|----------|--------|---------|
| Dark theme wrapper | `_theme(fig, height, title)` | ACTIVE | All chart factories (internal) |
| Utilization heatmap | `utilization_heatmap(util, top_n, title)` | ACTIVE | Capacity planner (classic) |
| Utilization lines | `utilization_lines(util, work_center, title)` | ACTIVE | Capacity planner (classic) |
| Scenario compare bar | `scenario_compare_bar(rows)` | ACTIVE | Overview, Capacity & Maintenance |
| Pipeline funnel | `pipeline_funnel(pipe)` | ACTIVE | Classic pages |
| Plant demand treemap | `plant_demand_treemap(pipe)` | ACTIVE | Classic pages |
| Sourcing table fig | `sourcing_table_fig(sourcing)` | ACTIVE | Sourcing & MRP (classic) |
| KPI donut | `kpi_donut(value, total, label, color)` | ACTIVE | Classic overview KPI |
| Pipeline timeline bar | `pipeline_timeline_bar(pq_df, title)` | ACTIVE | Scope & Region |
| Maintenance impact bar | `maintenance_impact_bar(maint_df, title)` | ACTIVE | Capacity & Maintenance |
| Effective capacity timeline | `effective_capacity_timeline(cap_df, plant, title)` | ACTIVE | Capacity & Maintenance |
| Delivery commitment chart | `delivery_commitment_chart(commit_df, title)` | ACTIVE | Sourcing & Delivery |
| Risk rollforward waterfall | `risk_rollforward_waterfall(rollforward_df, title)` | ACTIVE | Quarter History, Sourcing & Delivery |
| Action score bar | `action_score_bar(actions_df, scenario, title)` | ACTIVE | Final Actions |
| Action type donut | `action_type_donut(actions_df, title)` | ACTIVE | Final Actions |

### clarix/engine.py — Core Engine

| Component | Function | Status | Used By |
|-----------|----------|--------|---------|
| Scenario adjuster | `_apply_scenario(pipe, scenario)` | ACTIVE | Classic pages via build_demand_by_wc_week |
| Demand by WC/week builder | `build_demand_by_wc_week(data, scenario)` | ACTIVE | Capacity planner, Bottlenecks |
| Utilization builder | `build_utilization(demand, cap, limits)` | ACTIVE | Capacity planner, Bottlenecks |
| Bottleneck detector | `detect_bottlenecks(util, warn, crit)` | ACTIVE | Bottlenecks, What-if planner |
| Sourcing recommendations | `sourcing_recommendations(data, scenario, weeks_ahead)` | ACTIVE | Sourcing & MRP |
| Constraint explainer | `explain_constraint(data, wc_id, scenario)` | ACTIVE | Bottlenecks auto-explanation |
| Quarter label | `quarter_label(year, week)` | ACTIVE | Multiple pages |
| Quarter to month | `quarter_to_month(year, q)` | ACTIVE | Internal |
| Addable materials lister | `list_addable_materials(data, plant)` | ACTIVE | What-if planner |
| Basket to pipeline | `_basket_to_pipeline_rows(data, basket)` | ACTIVE | What-if planner (internal) |
| Utilization with basket | `build_utilization_with_basket(data, basket, scenario)` | ACTIVE | What-if planner |
| Project feasibility | `project_feasibility(data, project_id, scenario)` | ACTIVE | What-if planner |

### clarix/data_loader.py — Data Layer

| Component | Function/Class | Status | Used By |
|-----------|----------------|--------|---------|
| CanonicalData dataclass | `CanonicalData` | ACTIVE | All classic pages via `_load_data()` |
| Main loader | `load_canonical(xlsx_path, use_cache)` | ACTIVE | app.py `_load_data()` |
| Pipeline builder | `_build_pipeline(plates, gaskets, projects)` | ACTIVE | Internal to load_canonical |
| WC capacity builder | `_build_wc_capacity(cap_df)` | ACTIVE | Internal |
| WC limits builder | `_build_wc_limits(limits)` | ACTIVE | Internal |
| Tool master builder | `_build_tool_master(tool)` | ACTIVE | Internal |
| Inventory builder | `_build_inventory(inv)` | ACTIVE | Internal |
| BOM builder | `_build_bom(bom)` | ACTIVE | Internal |
| Project dim builder | `_build_project_dim(projects)` | ACTIVE | Internal |
| Material master builder | `_build_material_master(sap)` | ACTIVE | Internal |

### clarix/agent.py — AI Agent

| Component | Function | Status | Used By |
|-----------|----------|--------|---------|
| Tool dispatcher | `call_tool(name, args, data)` | ACTIVE | run_agent |
| AgentTurn dataclass | `AgentTurn` | ACTIVE | Ask Clarix history |
| Live agent | `run_agent(user_msg, data, history, model)` | ACTIVE | Ask Clarix (with API key) |
| Fallback planner | `_fallback_planner(user_msg, data, trace)` | ACTIVE | Ask Clarix (no API key) |
| DF to records | `_df_to_records(df, limit)` | ACTIVE | Internal tool serialization |

### project/src/app/demo_layer.py — Wave 7 Adapter

| Component | Function | Status | Used By |
|-----------|----------|--------|---------|
| File registry | `_REAL_FILES` dict | ACTIVE | load_all_processed |
| Processed loader | `load_all_processed()` | ACTIVE | _load_w7() in app.py |
| Actions deriver | `derive_planner_actions()` | ACTIVE | app.py fallback |
| Demo summary | `get_demo_summary()` | ACTIVE | app.py Overview KPI derivation |

---

## Deprecated Components

| Component | Location | Reason | Action |
|-----------|----------|--------|--------|
| Old "Actions" page | `app.py` ~line 1434, `elif page == "Actions":` | Superseded by "Final Actions" (Wave 3); not in sidebar radio | Dead code — safe to delete after demo |
| `_ACTION_COLORS` / `_CAUTION_COLORS` (if only used by old page) | `clarix/charts.py` | Still used by `action_score_bar` and `action_type_donut` — NOT deprecated | Keep |

---

## Clarix Migration Status

| Original Clarix Component | Migrated To | Status |
|--------------------------|------------|--------|
| Clarix chat (`Ask Clarix`) | `clarix/agent.py` + `app.py ~line 1141` | COMPLETE |
| Clarix capacity planner | `clarix/engine.py` + `app.py ~line 790` | COMPLETE |
| Clarix bottlenecks | `clarix/engine.py` + `app.py ~line 828` | COMPLETE |
| Clarix sourcing | `clarix/engine.py` + `app.py ~line 888` | COMPLETE |
| Clarix what-if | `clarix/engine.py` + `app.py ~line 929` | COMPLETE |
| Clarix UI shell | `clarix/ui.py` + CSS in `app.py` | COMPLETE |

All original Clarix features are present in the final product. No functionality was lost. The Wave 2–5 pages are additive on top of the classic engine — they consume Wave 7 pre-generated outputs rather than running the engine live.
