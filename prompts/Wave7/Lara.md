You are Lara's implementation agent for Wave 7.

Read first:
- contracts.md
- assumptions.md
- integrated_risk_v2_report.md
- wave6_lara_report.md

Use as inputs:
- fact_integrated_risk_v2
- fact_effective_capacity_weekly_v2
- fact_maintenance_impact_summary
- dim_action_policy
- fact_capacity_bottleneck_summary

Objective for Wave 7:
Upgrade the planner action engine so that it becomes region-scoped, maintenance-aware, and quarter-aware.

Required outputs:
1) fact_planner_actions_v2
2) planner_actions_v2_report.md

Required action families:
- buy_now
- wait
- reroute
- upshift
- expedite_shipping
- reschedule
- escalate
- hedge_inventory
- split_production
- shift_maintenance
- protect_capacity_window

Required columns:
- scope_id
- scenario
- quarter_id
- action_type
- action_score
- project_id
- plant
- material_or_wc
- recommended_target_plant
- reason
- expected_effect
- confidence
- explanation_trace

Tasks:
1) add maintenance-aware recommendations such as shift_maintenance and protect_capacity_window
2) use region scoping and quarter memory in action selection
3) preserve explainability
4) rank actions for product-owner readability, not just technical accuracy
5) keep outputs demo-friendly

Validation requirements:
- every action maps to visible drivers
- maintenance-related actions clearly justified
- top action list readable without extra debugging

Deliverables:
- Python modules
- processed outputs
- tests
- planner_actions_v2_report.md