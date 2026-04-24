You are Luigi's implementation agent for Wave 4.

Read first:
- contracts.md
- assumptions.md
- integrated_risk_base_report.md
- disruption_engine_report.md
- qa_guardrails_report.md

Use as inputs:
- fact_integrated_risk_base
- fact_scenario_resilience_impact
- fact_data_quality_flags

Objective for Wave 4:
Build the final integrated risk table used by the planner action engine and the demo.

Required output:
1) fact_integrated_risk
2) integrated_risk_final_report.md

Required columns:
- scenario
- project_id
- plant
- week
- priority_score
- capacity_risk_score
- sourcing_risk_score
- logistics_risk_score
- disruption_risk_score
- lead_time_risk_score
- data_quality_penalty
- risk_score
- action_score
- top_driver
- explainability_note

Final scoring logic:
risk_score =
0.30 * capacity_risk +
0.25 * sourcing_risk +
0.20 * logistics_risk +
0.10 * disruption_risk +
0.10 * lead_time_risk +
0.05 * data_quality_penalty

action_score = priority_score * risk_score * scenario_confidence

Tasks:
1) merge base integrated risk with disruption impacts and QA penalties
2) compute final risk_score and final action_score
3) produce clear top_driver and explainability_note
4) verify final table is action-engine ready
5) keep scoring transparent and reproducible

Validation requirements:
- no duplicate rows at declared grain
- final scores bounded and explainable
- disruption and QA effects visible in the final output
- top 20 rows readable without extra debugging

Deliverables:
- Python modules
- processed outputs
- tests
- integrated_risk_final_report.md