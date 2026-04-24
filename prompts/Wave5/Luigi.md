You are Luigi's implementation agent for Wave 5.

Read first:
- contracts.md
- assumptions.md
- integrated_risk_final_report.md
- planner_actions_report.md
- backend_audit.md
- migration_plan.md

Use as inputs:
- fact_pipeline_monthly
- dim_project_priority
- fact_integrated_risk
- fact_planner_actions

Objective for Wave 5:
Build the regional scope layer and quarter-state foundation for the demand and business side of the predictive manufacturing engine.

Business intent:
The product owners want the MVP to focus on a single region (for example Denmark) and, if needed, a subset of factories, so that the system becomes narrower, easier to validate, and easier to demonstrate.
They also want a more “live” system that can carry lessons and decisions from one quarter into the next.

Your scope in this wave:
1) define regional scoping contracts
2) build quarter-aware demand snapshots
3) build business decision history for Q1 -> Q2 continuity

Required outputs:
1) dim_region_scope
2) fact_pipeline_quarterly
3) fact_quarter_business_snapshot
4) fact_decision_history
5) wave5_luigi_report.md

Required columns for dim_region_scope:
- scope_id
- region_name
- included_plants
- included_factories_note
- scope_rule
- active_flag

Required columns for fact_pipeline_quarterly:
- scope_id
- quarter_id
- project_id
- plant
- material
- raw_qty_quarter
- expected_qty_quarter
- expected_value_quarter
- priority_score
- requested_date_min
- requested_date_max

Required columns for fact_quarter_business_snapshot:
- scope_id
- quarter_id
- total_projects
- total_expected_qty
- total_expected_value
- avg_priority_score
- high_confidence_project_count
- strategic_project_count

Required columns for fact_decision_history:
- scope_id
- quarter_id
- project_id
- previous_action_type
- previous_action_score
- previous_top_driver
- previous_confidence
- action_outcome_status
- carry_over_flag
- learning_note

Tasks:
1) inspect the existing codebase and reuse any reporting, snapshot, or state logic already present
2) define a region/factory scoping mechanism that can restrict the engine to one region and selected plants
3) create quarterly aggregations from fact_pipeline_monthly
4) build a quarter-state layer that summarizes what was planned/decided in Q1
5) build a decision history table that can be consumed in Q2
6) preserve explainability and traceability back to project-level rows
7) do not invent actual realized outcomes; if needed, mark synthetic or pending outcome fields explicitly

Validation requirements:
- every scoped output must be reproducible from explicit region/plant filters
- quarter aggregations must reconcile with monthly source tables
- decision-history rows must be uniquely keyed and traceable
- all synthetic or inferred history fields must be labeled

Deliverables:
- Python modules
- processed tables
- tests
- wave5_luigi_report.md summarizing:
  - region-scope logic
  - quarter aggregation logic
  - decision-history assumptions
  - blockers for Wave 6