You are Carolina's implementation agent for Wave 5.

Read first:
- contracts.md
- assumptions.md
- sourcing_logistics_report.md
- qa_guardrails_report.md
- backend_audit.md
- migration_plan.md

Use as inputs:
- fact_scenario_sourcing_weekly
- fact_scenario_logistics_weekly
- fact_inventory_snapshot
- dim_procurement_logic
- dim_country_cost_index_synth
- dim_shipping_lane_synth
- dim_service_level_policy_synth

Objective for Wave 5:
Build the scoped sourcing/logistics foundation and quarter-history layer for material and delivery decisions.

Business intent:
The MVP should focus on one region/few factories, and the system should remember what was bought, expedited, delayed, or exposed in the previous quarter so that the next quarter is planned more consciously.

Required outputs:
1) fact_scoped_sourcing_weekly
2) fact_scoped_logistics_weekly
3) fact_sourcing_quarterly_snapshot
4) fact_logistics_quarterly_snapshot
5) fact_material_decision_history
6) wave5_carolina_report.md

Required columns for fact_material_decision_history:
- scope_id
- quarter_id
- plant
- component_material
- prior_order_recommendation
- prior_shortage_flag
- prior_expedite_flag
- prior_on_time_feasible_flag
- carry_over_material_risk_flag
- learning_note

Tasks:
1) implement scope-aware filtering for sourcing and logistics outputs
2) create quarter-level sourcing and logistics snapshots
3) create material/logistics decision history tables for Q1 -> Q2 continuity
4) preserve delivery-related fields and on_time feasibility
5) ensure all synthetic logistics enrichments remain labeled
6) surface whether previous-quarter risks were unresolved and should influence next-quarter caution

Validation requirements:
- scoped outputs reconcile with base outputs
- quarter snapshots reconcile with weekly data
- decision-history outputs remain traceable to prior quarter rows
- synthetic dependencies remain visible

Deliverables:
- Python modules
- processed tables
- tests
- wave5_carolina_report.md