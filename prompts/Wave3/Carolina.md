You are Carolina's implementation agent for Wave 3.

Read first:
- contracts.md
- assumptions.md
- sourcing_logistics_report.md
- capacity_engine_report.md

Use as inputs:
- dim_service_level_policy_synth
- fact_capacity_bottleneck_summary
- fact_scenario_sourcing_weekly
- fact_scenario_logistics_weekly
- backend_audit.md
- migration_plan.md

Objective for Wave 3:
Build the Action Policy Library and QA Guardrails needed for final planner recommendations.

Required outputs:
1) dim_action_policy
2) fact_data_quality_flags
3) qa_guardrails_report.md

Required columns for dim_action_policy:
- action_type
- trigger_condition
- minimum_priority_threshold
- minimum_risk_threshold
- requires_alt_plant_flag
- allows_expedite_flag
- allows_upshift_flag
- expected_effect_type
- policy_version

Required columns for fact_data_quality_flags:
- entity_type
- entity_key
- issue_type
- severity
- penalty_score
- reason_code
- recommended_handling

Action families to cover:
- buy_now
- wait
- reroute
- upshift
- expedite_shipping
- reschedule
- escalate
- hedge_inventory
- split_production

Tasks:
1) define explicit action policies and thresholds
2) define QA penalties for missing mappings, missing lead times, revision mismatches, synthetic-only dependencies, and other fragile areas
3) output reusable policy tables that Wave 4 can consume directly
4) document how penalties affect final scoring
5) document what conditions should block or weaken a recommendation

Validation requirements:
- policies are explicit and human-readable
- penalties are deterministic
- every penalty has a reason code
- outputs can be joined safely by downstream agents

Deliverables:
- Python modules or config tables
- processed outputs
- tests
- qa_guardrails_report.md