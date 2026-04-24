You are Carolina's implementation agent for Wave 6.

Read first:
- contracts.md
- assumptions.md
- wave5_carolina_report.md
- sourcing_logistics_report.md
- qa_guardrails_report.md

Use as inputs:
- fact_scoped_sourcing_weekly
- fact_scoped_logistics_weekly
- fact_material_decision_history
- fact_logistics_quarterly_snapshot
- dim_service_level_policy_synth

Objective for Wave 6:
Build the rolling service-level and quarter-aware delivery logic for sourcing and logistics.

Business intent:
The product owners want a system that behaves more “live” and reasons from one quarter to the next. Delivery time must remain a hard constraint, and previous-quarter expedite/late-risk decisions should influence next-quarter planning caution.

Required outputs:
1) fact_delivery_commitment_weekly
2) fact_quarter_service_memory
3) fact_delivery_risk_rollforward
4) wave6_carolina_report.md

Required columns for fact_delivery_commitment_weekly:
- scope_id
- scenario
- project_id
- plant
- week
- requested_delivery_date
- transit_time_days
- production_time_proxy_days
- total_commitment_time_days
- on_time_feasible_flag
- expedite_option_flag
- service_violation_risk

Required columns for fact_quarter_service_memory:
- scope_id
- quarter_id
- project_id
- prior_on_time_feasible_flag
- prior_expedite_flag
- prior_service_violation_risk
- carry_over_service_caution_flag
- explanation_note

Tasks:
1) formalize delivery-time feasibility as a first-class table
2) add quarter-memory logic for service-level and logistics decisions
3) ensure previous-quarter late-risk can influence next-quarter caution
4) preserve service-level policies by revenue tier
5) keep all synthetic logistics dependencies visible

Validation requirements:
- delivery feasibility traceable to requested date + production/logistics timing
- quarter-service memory reproducible
- service-caution logic explainable
- no hidden overwriting of original requested-date fields

Deliverables:
- Python modules
- processed outputs
- tests
- wave6_carolina_report.md