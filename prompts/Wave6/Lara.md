You are Lara's implementation agent for Wave 6.

Read first:
- contracts.md
- assumptions.md
- wave5_lara_report.md
- capacity_engine_report.md
- disruption_engine_report.md

Use as inputs:
- fact_scoped_capacity_weekly
- fact_capacity_state_history
- dim_wc_scenario_limits
- bridge_material_tool_wc

Objective for Wave 6:
Build the maintenance and downtime simulation engine and produce effective-capacity outputs that can be used in scoped quarterly scenarios.

Important context:
Current logic already uses schedule limits and downtime-aware assumptions, but this is not yet a complete maintenance/downtime engine.
This wave must make maintenance and downtime explicit and scenario-driven.

Required outputs:
1) dim_maintenance_policy_synth
2) fact_maintenance_downtime_calendar
3) fact_effective_capacity_weekly_v2
4) fact_maintenance_impact_summary
5) wave6_lara_report.md

Required columns for dim_maintenance_policy_synth:
- policy_id
- plant
- work_center
- tool_no_if_available
- maintenance_trigger_type
- estimated_interval_weeks_synth
- expected_downtime_hours_synth
- policy_generation_rule

Required columns for fact_maintenance_downtime_calendar:
- scope_id
- scenario
- plant
- work_center
- week
- scheduled_maintenance_hours
- unscheduled_downtime_buffer_hours
- maintenance_source_type
- synthetic_flag

Required columns for fact_effective_capacity_weekly_v2:
- scope_id
- scenario
- plant
- work_center
- week
- nominal_available_capacity_hours
- scheduled_maintenance_hours
- downtime_buffer_hours
- effective_available_capacity_hours
- total_load_hours
- overload_hours
- overload_pct
- bottleneck_flag

Tasks:
1) create an explicit maintenance policy layer
2) create a maintenance/downtime calendar by WC/week
3) subtract maintenance and downtime from nominal capacity to produce effective capacity
4) support scenarios such as:
   - baseline_maintenance
   - maintenance_overrun
   - unexpected_breakdown
   - preventive_maintenance_shift
5) generate before/after comparisons vs previous capacity outputs
6) keep all synthetic maintenance assumptions labeled and documented

Validation requirements:
- effective capacity never exceeds nominal capacity
- maintenance scenarios explicitly state what changed
- downtime logic is visible and reproducible
- before/after capacity differences are inspectable

Deliverables:
- Python modules
- synthetic/config tables
- processed outputs
- tests
- wave6_lara_report.md