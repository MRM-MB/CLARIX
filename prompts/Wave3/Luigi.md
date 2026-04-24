You are Luigi's implementation agent for Wave 3.

Read first:
- contracts.md
- assumptions.md
- scenario_generation_report.md
- capacity_engine_report.md
- sourcing_logistics_report.md

Use as inputs:
- dim_project_priority
- fact_scenario_capacity_weekly
- fact_scenario_sourcing_weekly
- fact_scenario_logistics_weekly

Objective for Wave 3:
Build the Base Integrated Risk Engine, without waiting for final disruption-adjusted outputs.

Required outputs:
1) fact_integrated_risk_base
2) integrated_risk_base_report.md

Required columns:
- scenario
- project_id
- plant
- week
- priority_score
- capacity_risk_score
- sourcing_risk_score
- logistics_risk_score
- disruption_risk_score_placeholder
- lead_time_risk_score
- data_quality_penalty_placeholder
- risk_score_base
- action_score_base
- top_driver
- explainability_note

Scoring logic:
risk_score_base =
0.35 * capacity_risk +
0.30 * sourcing_risk +
0.25 * logistics_risk +
0.10 * lead_time_risk

action_score_base = priority_score * risk_score_base * scenario_confidence

Tasks:
1) merge priority, capacity, sourcing, and logistics risk
2) compute base risk and base action scores
3) produce human-readable top_driver and explainability_note
4) leave explicit placeholders/hooks for disruption_risk and data_quality_penalty
5) make final merge in Wave 4 easy and deterministic

Validation requirements:
- one row per declared grain
- top drivers clearly traceable
- no black-box scoring logic
- hooks for disruption and QA penalties must be explicit

Deliverables:
- Python modules
- processed outputs
- tests
- integrated_risk_base_report.md