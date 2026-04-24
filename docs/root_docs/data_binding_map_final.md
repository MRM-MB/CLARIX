# data_binding_map_final.md
## Clarix — Final Data Binding Map

Date: 2026-04-18  
Wave: 5 (Final)

---

## Data Source Overview

Two data sources feed the frontend:

| Source | Loader | Cache | Availability |
|--------|--------|-------|-------------|
| `data/hackathon_dataset.xlsx` (13 sheets) | `clarix/data_loader.load_canonical()` → `CanonicalData` | `@st.cache_resource` (persistent until restart) | Required — app crashes if missing |
| `project/data/processed/*.csv` (40+ files) | `demo_layer.load_all_processed()` → dict | `@st.cache_data(ttl=300)` | Optional — pages degrade gracefully if missing |

---

## Page-by-Page Binding

### Executive Overview
| Widget / Section | Data Source | Key / Column | Fallback |
|-----------------|-------------|--------------|---------|
| 4 KPI cards (pipeline, plants, peak util, actions) | `_load_w7()["actions_v2"]`, `["integrated_risk"]` | `action_score`, `risk_score_v2` | Zeroes shown |
| W7 intelligence row (actions count, high-conf, risk projects) | `_load_w7()["actions_v2"]` | `confidence`, `action_type` | Empty counts |
| Top-5 bottleneck cards | `_load_w7()["bottlenecks"]` | `bottleneck_severity`, `plant`, `work_center` | `ui.empty_state()` |
| Top-5 action cards | `_load_w7()["actions_v2"]` | `action_score`, `action_type`, `reason` | `ui.empty_state()` |
| Scenario summary table | `_load_w7()["integrated_risk"]` | `scenario`, `risk_score_v2`, `priority_score` | Hidden |
| "How the Engine Works" | Static HTML | — | Always shown |

### Scope & Region
| Widget / Section | Data Source | Key / Column | Fallback |
|-----------------|-------------|--------------|---------|
| Region info card | `_load_w7()["region_scope"]` | `region`, `plant_count`, `revenue_share` | `ui.empty_state()` |
| Demand distribution bar | `_load_w7()["pipeline_quarterly"]` | `plant`, `quarter_id`, `expected_demand_pcs` | `ui.empty_state()` |
| `pipeline_timeline_bar()` | `_load_w7()["pipeline_quarterly"]` | `week`, `expected_demand_pcs`, `scenario` | `ui.empty_state()` |
| Factory drilldown | `_load_w7()["pipeline_quarterly"]` | `plant`, `priority_band`, `project_count` | hidden |
| Data coverage panel | `_load_w7()` key existence checks | All 5 W7 table keys | Shows MISSING status |

### Quarter History
| Widget / Section | Data Source | Key / Column | Fallback |
|-----------------|-------------|--------------|---------|
| Quarter selector | `_load_w7()["quarter_snapshot"]` | `quarter_id` | Default Q1 |
| Q-over-Q delta metrics | `_load_w7()["quarter_snapshot"]` | `total_actions`, `avg_risk_score`, `high_risk_projects` | Zeroes |
| Carry-over risk cards | `_load_w7()["rollforward"]` | `caution_flag`, `project_id`, `carry_over_reason` | `st.success("No carry-over caution")` |
| Roll-forward expander | `_load_w7()["rollforward"]` | `quarter_id`, `risk_delta` | hidden |
| `risk_rollforward_waterfall()` | `_load_w7()["rollforward"]` | `quarter_id`, `risk_score_v2` | `ui.empty_state()` |
| Learning signal count cards | `_load_w7()["learning_signals"]` | `signal_type`, `signal_count` | Zero counts |

### Capacity & Maintenance
| Widget / Section | Data Source | Key / Column | Fallback |
|-----------------|-------------|--------------|---------|
| Plant selector | `_load_w7()["capacity_weekly"]` | `plant` unique values | Default first plant |
| `effective_capacity_timeline()` | `_load_w7()["capacity_weekly"]` | `plant`, `work_center`, `week`, `nominal_capacity_hrs`, `effective_capacity_hrs` | `ui.empty_state()` |
| `maintenance_impact_bar()` | `_load_w7()["maintenance"]` | `plant`, `maintenance_event`, `capacity_lost_hrs` | `ui.empty_state()` |
| Bottleneck drilldown cards | `_load_w7()["bottlenecks"]` | `bottleneck_severity`, `suggested_capacity_lever`, `explanation_note` | `ui.empty_state()` |
| Scenario comparison bar | `_load_w7()["capacity_weekly"]` | `scenario`, `effective_capacity_hrs` aggregated | hidden |
| Maintenance detail table | `_load_w7()["maintenance"]` | all columns | hidden |

### Sourcing & Delivery
| Widget / Section | Data Source | Key / Column | Fallback |
|-----------------|-------------|--------------|---------|
| Shortage table | `_load_w7()["sourcing"]` filtered `shortage_flag==1` | `component_material`, `plant`, `shortage_qty`, `recommended_order_date` | `st.success("No shortages")` |
| Order-by recommendations | `_load_w7()["sourcing"]` | `recommended_order_date`, `sourcing_risk_score` | hidden |
| Material criticality cards | `_load_w7()["sourcing"]` | `sourcing_risk_score` top 3 | hidden |
| `delivery_commitment_chart()` | `_load_w7()["delivery"]` | `week`, `committed_qty`, `at_risk_qty` | `ui.empty_state()` |
| `risk_rollforward_waterfall()` | `_load_w7()["rollforward"]` | `quarter_id`, `risk_score_v2` | `ui.empty_state()` |
| Carry-over roll-forward | `_load_w7()["rollforward"]` | `caution_flag`, `carry_over_reason` | `st.success("No carry-over caution")` |
| Quarter filter propagation | `st.session_state["selected_quarter"]` | — | Default first quarter |

### Logistics & Disruptions
| Widget / Section | Data Source | Key / Column | Fallback |
|-----------------|-------------|--------------|---------|
| Shipping cost / transit summary | `_load_w7()["logistics"]` | `destination_country`, `shipping_cost`, `transit_time_days` | `ui.empty_state()` + `st.stop()` |
| Landed cost bar | `_load_w7()["logistics"]` | `landed_cost_proxy`, `destination_country` | hidden |
| Disruption before/after | `_load_w7()["logistics"]` scenario filter | `logistics_risk_score`, `on_time_feasible_flag` | hidden |
| Route/lane risk cards | `_load_w7()["logistics"]` | `logistics_risk_score`, `expedite_option_flag` | hidden |
| Mitigation lever cards | `_load_w7()["logistics"]` | `expedite_option_flag` count | hidden |
| Full table expander | `_load_w7()["logistics"]` | all columns | hidden |
| Scenario filter | `st.session_state["w7_scenario"]` | — | `"base"` default |

### Final Actions
| Widget / Section | Data Source | Key / Column | Fallback |
|-----------------|-------------|--------------|---------|
| Filter bar | Page-local widgets | scenario, action_type, plant, min_confidence | All = show all |
| Carry-over enrichment | `_load_w7()["rollforward"]` join | `project_id`, `caution_flag` | No enrichment shown |
| Top-3 action cards | `_load_w7()["actions_v2"]` | `action_score`, `action_type`, `confidence`, `reason` | `ui.empty_state()` + `st.stop()` |
| `action_type_donut()` | `_load_w7()["actions_v2"]` | `action_type` | hidden |
| `action_score_bar()` | `_load_w7()["actions_v2"]` | `action_score`, `scenario`, `project_id` | hidden |
| Confidence vs risk scatter | `_load_w7()["actions_v2"]` join `["integrated_risk"]` | `confidence`, `risk_score_v2`, `action_type` | hidden |
| Ranked table | `_load_w7()["actions_v2"]` | all columns filtered | hidden |
| `ui.why_panel()` drilldown | `_load_w7()["actions_v2"]` + `["integrated_risk"]` | `explanation_trace`, `top_driver`, `quarter_learning_penalty_or_boost` | "No project selected" |
| Baseline vs mitigated compare | `_load_w7()["integrated_risk"]` | `scenario`, `risk_score_v2` grouped | hidden |

### Classic Pages (Capacity planner, Bottlenecks, Sourcing & MRP, What-if planner, Ask Clarix)
| Page | Data Source | Notes |
|------|-------------|-------|
| All classic pages | `CanonicalData` via `_load_data()` | 13-sheet Excel; engine computed live |
| Capacity planner | `data.wc_capacity`, `data.wc_limits`, `data.tool_master`, `data.pipeline` | Via `build_demand_by_wc_week()` + `build_utilization()` |
| Bottlenecks | Same as Capacity planner + `detect_bottlenecks()` + `explain_constraint()` | — |
| Sourcing & MRP | `data.pipeline`, `data.bom`, `data.inventory`, `data.material_master` | Via `sourcing_recommendations()` |
| What-if planner | All of the above + `project_feasibility()` | Basket state in `st.session_state` |
| Ask Clarix | `CanonicalData` passed to `run_agent()` or `_fallback_planner()` | History in `st.session_state["chat_history"]` |

---

## v1 / v2 Fallback Logic

| Table | v1 (fallback) | v2 (preferred) | Logic |
|-------|--------------|----------------|-------|
| `fact_planner_actions` | `fact_planner_actions.csv` — basic action list | `fact_planner_actions_v2.csv` — adds `confidence`, `explanation_trace`, `action_score` | `_load_w7()` attempts v2 key first; if empty falls back to v1 via `demo_layer.derive_planner_actions()` |
| `fact_integrated_risk` | `fact_integrated_risk.csv` — 6-dimension scores | `fact_integrated_risk_v2.csv` — adds `quarter_learning_penalty_or_boost`, `action_score_v2` | `_load_w7()` loads v2 key `integrated_risk`; falls back to empty DataFrame (not v1, to avoid schema mismatch) |
| `fact_effective_capacity_weekly` | Not present in v1 | `fact_effective_capacity_weekly_v2.csv` | No v1 fallback; `ui.empty_state()` shown |

---

## Session State Keys Reference

| Key | Type | Set By | Read By |
|-----|------|--------|---------|
| `scenario` | str | Sidebar scenario radio | Classic pages |
| `w7_scenario` | str | Sidebar W7 scenario radio | Wave 3–5 advanced pages |
| `plant_filter` | str | Sidebar plant selector | Overview, Capacity planner |
| `region` | str | Scope & Region page selector | Scope & Region |
| `selected_quarter` | str | Quarter History page selector | Quarter History, Sourcing & Delivery |
| `maint_scenario` | str | Capacity & Maintenance selector | Capacity & Maintenance |
| `demo_mode` | bool | Demo mode toggle button | `_render_demo_banner()`, sidebar nav |
| `chat_history` | list | Ask Clarix chat input | Ask Clarix |
| `what_if_basket` | list | What-if planner add buttons | What-if planner |
