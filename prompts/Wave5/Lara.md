You are Lara's implementation agent for Wave 5.

Read first:
- contracts.md
- assumptions.md
- capacity_engine_report.md
- disruption_engine_report.md
- backend_audit.md
- migration_plan.md

Use as inputs:
- bridge_material_tool_wc
- fact_wc_capacity_weekly
- fact_scenario_capacity_weekly
- fact_capacity_bottleneck_summary

Objective for Wave 5:
Build the scoped regional capacity foundation and quarter-aware capacity state layer.

Business intent:
The MVP should be narrowed to one region and possibly a few factories. Capacity analysis must become easier to validate, and quarter-over-quarter planning must be possible.

Required outputs:
1) fact_scoped_capacity_weekly
2) fact_capacity_quarterly_snapshot
3) fact_capacity_state_history
4) wave5_lara_report.md

Required columns for fact_scoped_capacity_weekly:
- scope_id
- scenario
- plant
- work_center
- week
- available_capacity_hours
- planned_load_hours
- incremental_load_hours
- total_load_hours
- overload_hours
- overload_pct
- bottleneck_flag

Required columns for fact_capacity_quarterly_snapshot:
- scope_id
- quarter_id
- plant
- work_center
- total_available_capacity_hours
- total_planned_load_hours
- total_incremental_load_hours
- total_overload_hours
- bottleneck_weeks_count

Required columns for fact_capacity_state_history:
- scope_id
- quarter_id
- plant
- work_center
- prior_quarter_bottleneck_flag
- prior_quarter_overload_hours
- prior_quarter_mitigation_used
- carry_over_capacity_risk_flag
- learning_note

Tasks:
1) reuse any existing capacity filtering, partitioning, or summary logic from the old backend if available
2) implement scope-aware filtering to one region / selected plants
3) produce scoped weekly capacity tables
4) aggregate weekly capacity into quarter-level state snapshots
5) create a carry-over capacity history layer for Q1 -> Q2 continuity
6) ensure bottleneck memory is visible, e.g. “this WC was overloaded last quarter too”
7) keep all logic explainable and aligned with existing capacity contracts

Validation requirements:
- scoped weekly rows reconcile with unscoped source rows under the same filter
- quarter snapshots reconcile with weekly aggregates
- prior-quarter history is deterministic and reproducible
- no hidden filtering logic

Deliverables:
- Python modules
- processed tables
- tests
- wave5_lara_report.md