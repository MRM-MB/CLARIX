You are Lara's implementation agent for Wave 2.

Read first:
- contracts.md
- assumptions.md
- wave1_lara_report.md
- wave1_luigi_report.md

Use as inputs:
- fact_translated_project_demand_weekly
- fact_wc_capacity_weekly
- dim_wc_scenario_limits

Objective for Wave 2:
Build the Capacity Overlay & Bottleneck Engine.

Required outputs:
1) fact_scenario_capacity_weekly
2) fact_capacity_bottleneck_summary
3) capacity_engine_report.md

Required columns for fact_scenario_capacity_weekly:
- scenario
- plant
- work_center
- week
- incremental_load_hours
- planned_load_hours
- total_load_hours
- available_capacity_hours
- remaining_capacity_hours
- overload_hours
- overload_pct
- bottleneck_flag

Required columns for fact_capacity_bottleneck_summary:
- scenario
- plant
- work_center
- tool_no_if_available
- bottleneck_severity
- top_driver_project_count
- suggested_capacity_lever
- explanation_note

Tasks:
1) convert weekly pieces into hours using cycle_time
2) compare incremental load against approved plan and available capacity
3) compute overload and headroom
4) simulate explicit capacity variants using schedule limits
5) rank bottlenecks by severity
6) expose possible capacity levers such as upside_1 or upside_2
7) keep logic explainable and traceable

Validation requirements:
- all outputs unique at declared grain
- overload calculations reproducible
- scenario variants explicitly labeled
- bottleneck summary clearly traceable to WC/week/project drivers

Deliverables:
- Python modules
- processed outputs
- tests
- capacity_engine_report.md