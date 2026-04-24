# frontend_data_contracts.md
## Frontend Data Contracts — Wave 1

Date: 2026-04-18

All contracts are derived from actual CSV headers observed in `project/data/processed/`.
Each table lists: column name, type, nullable, description, and which page consumes it.

---

## Source 1: clarix canonical tables (from hackathon_dataset.xlsx)

### fact_pipeline_monthly
**Loaded by:** `clarix/data_loader.load_canonical()` → `CanonicalData.fact_pipeline_monthly`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| status | str | Y | Project status ("Open", "Won", etc.) |
| material | str | N | SAP material code |
| material_description | str | Y | Human-readable description |
| cycle_time_min | float | Y | Minutes per piece (SAP convention) |
| work_center | str | Y | Short WC code |
| work_center_full | str | Y | Full code e.g. `P01_NW01_PRESS_1` |
| tool | str | Y | Tool number |
| project_name | str | Y | Project name (join key to dim_project) |
| plant | str | Y | Plant code e.g. `NW01` |
| type | str | N | "Plate" \| "Gasket" |
| qty | float | N | Monthly quantity (pieces) |
| year | int | N | Calendar year |
| month | int | N | Calendar month (1–12) |
| period_date | datetime | N | First day of month |
| probability | float | Y | Probability as integer percent (10/25/50/75/90) |
| probability_frac | float | N | Probability as fraction [0,1] |
| expected_qty | float | N | qty × probability_frac |

**Pages:** Overview (funnel, treemap), Scope & Pipeline, What-if planner, Ask Clarix

---

### dim_project (from `1_3 Export Project list`)
**Loaded by:** `CanonicalData.dim_project`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| project_name | str | N | Join key |
| project_id | str | Y | SAP project ID |
| probability_pct | float | Y | 10/25/50/75/90 |
| probability_frac | float | N | Fraction |
| region | str | Y | Geographic region |
| owner | str | Y | Project owner |
| requested_delivery | datetime | Y | Target delivery date |
| segment | str | Y | Customer segment |
| total_pcs | float | Y | Total expected pieces |
| total_eur | float | Y | Total expected value EUR |
| revenue_tier | str | Y | Revenue tier label |
| status | str | Y | Pipeline status |

**Pages:** Overview (KPIs), Scope & Pipeline

---

### fact_wc_capacity_weekly
**Loaded by:** `CanonicalData.fact_wc_capacity_weekly`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| work_center | str | N | Full WC code |
| plant | str | N | Plant code |
| year | int | N | |
| week | int | N | ISO week number |
| week_start | datetime | Y | Monday of that week |
| available_hours | float | N | Available capacity hours |
| baseline_demand_qty | float | N | Baseline demand quantity |

**Pages:** Capacity & Maintenance (heatmap, drilldown)

---

## Source 2: Wave 6/7 processed CSVs (project/data/processed/)

### dim_region_scope
**File:** `dim_region_scope.csv`
**Key:** `scope_id` (unique)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scope_id | str | N | e.g. "mvp_3plant", "global_reference" |
| region_name | str | N | Display name |
| included_plants | str | N | Comma-separated plant codes |
| included_factories_note | str | Y | Human note |
| scope_rule | str | Y | Rule description |
| active_flag | bool | N | True = active scope for demo |

**Pages:** Scope & Pipeline (region card), sidebar filter, Actions & Recommendations (scope filter)

---

### dim_project_priority
**File:** `dim_project_priority.csv`
**Key:** `project_id`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| project_id | str | N | SAP project ID |
| project_name | str | Y | |
| owner | str | Y | |
| region | str | Y | |
| segment | str | Y | Customer segment |
| requested_delivery | str | Y | |
| revenue_tier | str | Y | "strategic" \| "core" \| "standard" |
| project_value | float | Y | Raw EUR value |
| expected_value | float | Y | prob-weighted EUR |
| probability_score | float | Y | [0,1] |
| urgency_score | float | Y | [0,1] |
| revenue_tier_score | float | Y | [0,1] |
| expected_value_score | float | Y | [0,1] |
| strategic_segment_score | float | Y | [0,1] |
| priority_score | float | Y | [0,1] composite |
| priority_band | str | Y | "high" \| "medium" \| "low" |
| score_version | str | Y | |
| reason_code | str | Y | Human explanation |

**Pages:** Scope & Pipeline (project table), Actions & Recommendations (priority band filter)

---

### fact_pipeline_quarterly
**File:** `fact_pipeline_quarterly.csv`
**Key:** (scope_id, scenario, quarter_id, project_id, plant, material)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scope_id | str | N | |
| scenario | str | N | |
| quarter_id | str | N | "2026-Q1" format |
| project_id | str | N | |
| plant | str | N | |
| material | str | Y | |
| expected_qty_quarter | float | N | prob-weighted qty for quarter |
| expected_value_quarter | float | Y | prob-weighted EUR |

**Pages:** Scope & Pipeline (pipeline-by-quarter bar chart, project breakdown table)

---

### fact_effective_capacity_weekly_v2
**File:** `fact_effective_capacity_weekly_v2.csv`
**Key:** (scope_id, scenario, plant, work_center, week)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scope_id | str | N | |
| scenario | str | N | Maintenance scenario |
| plant | str | N | |
| work_center | str | N | |
| week | str | N | "2026-W01" format |
| nominal_available_capacity_hours | float | N | Before maintenance |
| scheduled_maintenance_hours | float | N | Planned downtime |
| downtime_buffer_hours | float | N | Buffer |
| effective_available_capacity_hours | float | N | After deductions |
| total_load_hours | float | N | Demand load |
| overload_hours | float | N | max(0, load - effective) |
| overload_pct | float | N | [0,1] overload fraction |
| bottleneck_flag | bool | N | True if overloaded |

**Pages:** Capacity & Maintenance (maintenance heatmap, scenario comparison)

---

### fact_maintenance_impact_summary
**File:** `fact_maintenance_impact_summary.csv`
**Key:** (scope_id, scenario, plant, work_center)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scope_id | str | N | |
| scenario | str | N | |
| plant | str | N | |
| work_center | str | N | |
| nominal_avg_available_hours | float | N | Baseline |
| effective_avg_available_hours | float | N | After maintenance |
| avg_maintenance_reduction_hours | float | N | |
| pct_capacity_lost_to_maintenance | float | N | [0,1] |
| effective_bottleneck_weeks | int | N | |
| nominal_bottleneck_weeks | int | N | |
| delta_avg_overload_hours | float | N | Change in overload hours |
| worst_week | str | Y | Week with peak impact |
| impact_severity | str | Y | "low" \| "medium" \| "high" |

**Pages:** Capacity & Maintenance (impact summary table)

---

### fact_scenario_sourcing_weekly
**File:** `fact_scenario_sourcing_weekly.csv`
**Key:** (scenario, project_id, plant, week)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scenario | str | N | |
| project_id | str | N | |
| plant | str | N | |
| week | str | N | |
| shortage_flag | bool | N | True if ATP < requirement |
| *(additional columns vary)* | | | |

**Pages:** Overview (KPI: shortage rows), Sourcing & Delivery

---

### fact_scenario_logistics_weekly
**File:** `fact_scenario_logistics_weekly.csv`
**Key:** (scenario, project_id, plant, week)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scenario | str | N | |
| project_id | str | N | |
| plant | str | N | |
| destination_country | str | Y | |
| week | str | N | |
| transit_time_days | float | Y | |
| shipping_cost | float | Y | SYNTHETIC |
| landed_cost_proxy | float | Y | SYNTHETIC |
| on_time_feasible_flag | bool | N | |
| expedite_option_flag | bool | Y | |
| logistics_risk_score | float | N | [0,1] |
| synthetic_dependency_flag | bool | Y | |

**Pages:** Logistics & Disruptions

---

### fact_delivery_commitment_weekly
**File:** `fact_delivery_commitment_weekly.csv`
**Key:** (scenario, project_id, plant, week)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scenario | str | N | |
| project_id | str | N | |
| plant | str | N | |
| week | str | N | |
| on_time_feasible_flag | bool | N | |
| service_violation_risk | float | N | [0,1] |
| expedite_option_flag | bool | Y | |
| transit_time_days | float | Y | Real data |
| requested_delivery_date | str | Y | SYNTHETIC (week+28d) |
| production_time_proxy_days | float | Y | SYNTHETIC (14d) |

**Pages:** Sourcing & Delivery (delivery feasibility scatter, on-time KPI)

---

### fact_delivery_risk_rollforward
**File:** `fact_delivery_risk_rollforward.csv`
**Key:** (project_id, source_quarter_id, carry_forward_quarter_id)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| project_id | str | N | |
| source_quarter_id | str | N | Quarter the caution originated from |
| carry_forward_quarter_id | str | N | Quarter receiving the caution |
| recommended_caution_level | str | N | "high" \| "medium" \| "low" |
| caution_explanation | str | Y | Human explanation |

**Pages:** Quarter History (delivery caution), Sourcing & Delivery (caution bar), Actions & Recommendations (enrichment)

---

### fact_quarter_service_memory
**File:** `fact_quarter_service_memory.csv`
**Key:** (scope_id, quarter_id, project_id)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scope_id | str | N | |
| quarter_id | str | N | |
| project_id | str | N | |
| carry_over_service_caution_flag | bool | N | True = action needed |
| prior_service_violation_risk | float | N | [0,1] |
| explanation_note | str | Y | |

**Pages:** Quarter History (service memory table), Actions & Recommendations (context enrichment)

---

### fact_quarter_learning_signals
**File:** `fact_quarter_learning_signals.csv`
**Key:** (quarter_id, project_id)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| quarter_id | str | N | |
| project_id | str | N | |
| repeated_risk_flag | bool | N | Same risk class reappearing |
| repeated_action_flag | bool | N | Same action recommended again |
| repeated_delay_flag | bool | N | Project delayed again |
| confidence_adjustment_signal | float | N | Positive = boost, negative = penalty |
| explanation_note | str | Y | |

**Pages:** Quarter History (learning signals table)

---

### fact_quarter_rollforward_inputs
**File:** `fact_quarter_rollforward_inputs.csv`
**Key:** (project_id, from_quarter, to_quarter)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| project_id | str | N | |
| from_quarter | str | N | |
| to_quarter | str | N | |
| carry_over_probability_adjustment | float | N | Delta applied to base probability |
| carry_over_priority_adjustment | float | N | Delta applied to priority score |
| unresolved_action_penalty | float | N | Penalty for unresolved prior action |
| deferred_project_flag | bool | N | |
| rollforward_note | str | Y | |

**Pages:** Quarter History (roll-forward panel)

---

### fact_integrated_risk_v2
**File:** `fact_integrated_risk_v2.csv`
**Key:** (scope_id, scenario, quarter_id, project_id, plant, week)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scope_id | str | N | |
| scenario | str | N | |
| quarter_id | str | N | |
| project_id | str | N | |
| plant | str | N | |
| week | str | N | |
| priority_score | float | N | [0,1] from dim_project_priority |
| capacity_risk_score | float | N | [0,1] |
| sourcing_risk_score | float | N | [0,1] |
| logistics_risk_score | float | N | [0,1] |
| disruption_risk_score | float | N | [0,1] |
| delivery_risk_score | float | N | [0,1] |
| maintenance_risk_score | float | N | [0,1] |
| quarter_learning_penalty_or_boost | float | N | From learning signals |
| risk_score_v2 | float | N | [0,1] composite |
| action_score_v2 | float | N | [0,1] |
| top_driver | str | Y | e.g. "capacity_risk" |
| explainability_note | str | Y | |

**Pages:** Overview (avg risk KPI), Actions & Recommendations (risk context)
**Note:** Not currently loaded in demo_layer `_REAL_FILES`. Must be added.

---

### fact_planner_actions_v2
**File:** `fact_planner_actions_v2.csv`
**Key:** (scope_id, scenario, quarter_id, project_id, plant)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| scope_id | str | N | |
| scenario | str | N | |
| quarter_id | str | N | |
| action_type | str | N | One of 11 action families |
| action_score | float | N | [0,1] adjusted |
| project_id | str | N | |
| plant | str | N | |
| material_or_wc | str | Y | Target resource |
| recommended_target_plant | str | Y | Reroute target |
| reason | str | N | Human-readable explanation |
| expected_effect | str | N | Effect type |
| confidence | float | N | [0,1] |
| explanation_trace | str | N | JSON with full decision chain |

**Pages:** Actions & Recommendations (primary), Overview (count KPI)

### Action type vocabulary

| action_type | Meaning |
|-------------|---------|
| `buy_now` | Order immediately — sourcing risk above threshold |
| `hedge_inventory` | Add safety stock — moderate sourcing risk |
| `upshift` | Increase shift hours — capacity risk |
| `reschedule` | Defer/spread production — manageable risk |
| `split_production` | Distribute load — critical capacity |
| `escalate` | Escalate to management |
| `reroute` | Switch shipping lane |
| `expedite_shipping` | Expedite freight |
| `shift_maintenance` | Move maintenance to lower-load window |
| `protect_capacity_window` | Defer maintenance near bottleneck |
| `wait` | No action — risk within range |

---

## Contract stability guarantees

| Table | Stability | Notes |
|-------|-----------|-------|
| fact_pipeline_monthly | STABLE | Generated from Excel, won't change |
| dim_project | STABLE | Generated from Excel |
| fact_wc_capacity_weekly | STABLE | Generated from Excel |
| dim_region_scope | STABLE | Hand-authored |
| dim_project_priority | STABLE | Output of Wave 3 runner |
| fact_planner_actions_v2 | STABLE | Output of Wave 7 Lara runner |
| fact_integrated_risk_v2 | STABLE | Output of Wave 7 Luigi runner |
| fact_effective_capacity_weekly_v2 | STABLE | Output of Wave 6 runner |
| fact_delivery_commitment_weekly | STABLE | Output of Wave 6 Carolina runner |
| fact_delivery_risk_rollforward | STABLE | Output of Wave 6 Carolina runner |
| fact_quarter_service_memory | STABLE | Output of Wave 6 Carolina runner |
| fact_quarter_learning_signals | STABLE | Output of Wave 6 Carolina runner |
| fact_quarter_rollforward_inputs | STABLE | Output of Wave 6 Carolina runner |
| fact_scenario_sourcing_weekly | STABLE | Output of Wave 2 runner |
| fact_scenario_logistics_weekly | STABLE | Output of Wave 2 runner |
| fact_maintenance_impact_summary | STABLE | Output of Wave 6 Lara runner |

---

## Missing from demo_layer (must add)

`fact_integrated_risk_v2.csv` exists in `project/data/processed/` but is NOT in `demo_layer._REAL_FILES`. Add:

```python
"integrated_risk_v2": "fact_integrated_risk_v2.csv",
```
