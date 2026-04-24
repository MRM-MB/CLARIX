You are Luigi's implementation agent for Wave 2.

Read first:
- contracts.md
- assumptions.md
- wave1_luigi_report.md
- wave1_lara_report.md

Use as inputs:
- fact_pipeline_monthly
- dim_project_priority
- bridge_material_tool_wc
- bridge_month_week_calendar

Objective for Wave 2:
Build the Scenario & Translation Engine that converts monthly project demand into weekly manufacturable demand.

Required outputs:
1) fact_translated_project_demand_weekly
2) scenario_generation_report.md

Required columns:
- scenario
- project_id
- plant
- material
- week
- raw_weekly_qty
- expected_weekly_qty
- tool_no
- work_center
- cycle_time
- priority_score
- scenario_confidence
- mapping_status
- reason_code

Required scenarios:
- all_in
- expected_value
- high_confidence
- monte_carlo_light

Tasks:
1) allocate monthly demand into weekly buckets using bridge_month_week_calendar
2) implement scenario generation logic
3) join translated weekly demand to bridge_material_tool_wc
4) preserve and surface unmapped rows with reason codes
5) compute scenario_confidence and keep explainable logic
6) produce one clean weekly manufacturable-demand table for downstream consumers

Validation requirements:
- no duplicate (scenario, project_id, plant, material, week)
- translated demand traceable back to monthly demand
- scenario logic deterministic except explicitly seeded monte_carlo_light
- all unmapped rows retained or flagged, never silently dropped

Deliverables:
- Python modules
- processed outputs
- tests
- scenario_generation_report.md