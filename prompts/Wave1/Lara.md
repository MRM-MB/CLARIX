You are Lara's implementation agent for Wave 1.

Read first:
- backend_audit.md
- migration_plan.md
- contracts.md
- assumptions.md
- synthetic_data_policy.md

Objective for Wave 1:
Build the Operational Spine & Capacity Foundation, while reusing any useful legacy backend modules already identified in the audit.

Important:
Do NOT rebuild existing working logic for mappings, calendars, or capacity parsing if reusable modules already exist.
Use legacy adapters where necessary.

Your scope in this wave:
1) build the operational mapping backbone
2) build the weekly capacity baseline
3) build the month-to-week bridge
4) build schedule-limit scenario dimension

Primary real inputs:
- 2_6 Tool_material nr master
- 2_1 Work Center Capacity Weekly
- 2_4 Model Calendar
- 2_5 WC Schedule_limits

Required outputs:
1) bridge_material_tool_wc
2) fact_wc_capacity_weekly
3) bridge_month_week_calendar
4) dim_wc_scenario_limits
5) wave1_lara_report.md

Required columns for bridge_material_tool_wc:
- plant
- material
- revision
- tool_no
- work_center
- cycle_time
- mapping_status
- reason_code

Required columns for fact_wc_capacity_weekly:
- plant
- work_center
- week
- available_capacity_hours
- planned_load_hours
- remaining_capacity_hours
- missing_capacity_hours

Required columns for bridge_month_week_calendar:
- plant
- month
- week
- allocation_weight
- working_day_weight
- bridge_version

Required columns for dim_wc_scenario_limits:
- plant
- work_center
- scenario_limit_name
- available_hours_variant
- oee_variant
- weekly_time_variant
- source_level

Tasks:
1) inspect the backend audit and identify reusable legacy modules for operational mapping, calendar handling, and capacity parsing
2) document which legacy modules are reused, adapted, or ignored
3) normalize 2_6 into plant-material-revision-tool-work_center-cycle_time mapping
4) normalize 2_1 into long format and select only required measures
5) build plant-aware month-to-week allocation weights from 2_4
6) normalize schedule up/down limits from 2_5
7) add reason codes for missing work center / cycle time / tool / mapping failures
8) create schema-stable outputs for Wave 2 consumers

Validation requirements:
- every capacity row unique by (plant, work_center, week)
- month-to-week weights sum correctly by plant-month
- unresolved mappings explicitly counted
- revision mismatches surfaced explicitly
- wave1_lara_report.md must include KEEP / ADAPT / DEPRECATE / REPLACE decisions for any touched legacy modules

Deliverables:
- Python modules
- processed tables
- tests
- wave1_lara_report.md summarizing:
  - reused legacy components
  - new modules created
  - validation status
  - mapping gaps
  - blockers for Wave 2

Done when:
Downstream agents can translate monthly demand into weekly manufacturable demand using stable mapping and calendar contracts.