You are Luigi's implementation agent for Wave 6.

Read first:
- contracts.md
- assumptions.md
- wave5_luigi_report.md
- wave5_lara_report.md
- wave5_carolina_report.md

Use as inputs:
- fact_pipeline_quarterly
- fact_decision_history
- dim_project_priority
- fact_integrated_risk

Objective for Wave 6:
Build the rolling planning and quarterly learning layer for demand-side decision making.

Required outputs:
1) fact_quarter_rollforward_inputs
2) fact_quarter_learning_signals
3) wave6_luigi_report.md

Required columns for fact_quarter_rollforward_inputs:
- scope_id
- from_quarter
- to_quarter
- project_id
- carry_over_probability_adjustment
- carry_over_priority_adjustment
- unresolved_action_penalty
- deferred_project_flag
- rollforward_note

Required columns for fact_quarter_learning_signals:
- scope_id
- quarter_id
- project_id
- repeated_risk_flag
- repeated_action_flag
- repeated_delay_flag
- confidence_adjustment_signal
- explanation_note

Tasks:
1) create roll-forward logic from one quarter to the next
2) allow previous unresolved actions or repeated risks to influence next-quarter business prioritization
3) keep probability itself separate from business-priority adjustments
4) do not invent actual observed business outcomes unless explicitly synthetic-labeled
5) output reusable quarter-learning signals that Wave 7 can consume

Validation requirements:
- roll-forward logic deterministic
- no hidden changes to base probability
- learning signals explainable and auditable

Deliverables:
- Python modules
- processed tables
- tests
- wave6_luigi_report.md