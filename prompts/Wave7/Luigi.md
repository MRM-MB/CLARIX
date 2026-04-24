You are Luigi's implementation agent for Wave 7.

Read first:
- contracts.md
- assumptions.md
- wave6_luigi_report.md
- wave6_lara_report.md
- wave6_carolina_report.md

Use as inputs:
- fact_integrated_risk
- fact_quarter_rollforward_inputs
- fact_quarter_learning_signals
- fact_delivery_risk_rollforward

Objective for Wave 7:
Upgrade the integrated risk model so it becomes region-scoped, quarter-aware, and learning-aware.

Required outputs:
1) fact_integrated_risk_v2
2) integrated_risk_v2_report.md

Required columns:
- scope_id
- scenario
- quarter_id
- project_id
- plant
- week
- priority_score
- capacity_risk_score
- sourcing_risk_score
- logistics_risk_score
- disruption_risk_score
- delivery_risk_score
- maintenance_risk_score
- quarter_learning_penalty_or_boost
- risk_score_v2
- action_score_v2
- top_driver
- explainability_note

Tasks:
1) merge quarter roll-forward signals into the final risk layer
2) add delivery-risk and maintenance-risk dimensions
3) make the table explicitly scope-aware
4) preserve explainability and comparability with fact_integrated_risk v1
5) document what changed from v1 to v2

Validation requirements:
- all new risk components explicit
- v2 remains comparable with v1
- no opaque learning adjustments

Deliverables:
- Python modules
- processed outputs
- tests
- integrated_risk_v2_report.md