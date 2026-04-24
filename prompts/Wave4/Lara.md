You are Lara's implementation agent for Wave 4.

Read first:
- contracts.md
- assumptions.md
- integrated_risk_final_report.md
- disruption_engine_report.md
- qa_guardrails_report.md

Use as inputs:
- fact_integrated_risk
- dim_action_policy
- fact_capacity_bottleneck_summary
- fact_scenario_resilience_impact

Objective for Wave 4:
Build the final Planner Action Engine.

Required output:
1) fact_planner_actions
2) planner_actions_report.md

Required columns:
- scenario
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
1) apply explicit action policies to final integrated risk
2) generate explainable recommendations:
   - buy_now
   - wait
   - reroute
   - upshift
   - expedite_shipping
   - reschedule
   - escalate
   - hedge_inventory
   - split_production
3) use disruption impacts and bottleneck summaries where relevant
4) provide recommended_target_plant only when supported and clearly qualified
5) keep every recommendation explainable and traceable

Validation requirements:
- every action maps to visible drivers
- no black-box output
- top 20 actions readable by product owners
- explanation_trace must clearly show why that action was chosen

Deliverables:
- Python modules
- processed outputs
- tests
- planner_actions_report.md