You are Luigi's implementation agent for Wave 1.

Read first:
- backend_audit.md
- migration_plan.md
- contracts.md
- assumptions.md
- synthetic_data_policy.md

Objective for Wave 1:
Build the Demand & Business Priority Foundation, while reusing any useful legacy backend modules already identified in the audit.

Important:
Do NOT rebuild existing working logic if it already covers part of pipeline loading, normalization, or scoring preparation.
Reuse old backend modules through adapters if needed.

Your scope in this wave:
1) build the canonical pipeline-demand layer
2) build the project-priority layer
3) produce scenario seed tables for downstream engines

Primary real inputs:
- 1_1 Export Plates
- 1_2 Gaskets
- 1_3 Export Project list

Required outputs:
1) fact_pipeline_monthly
2) dim_project_priority
3) scenario_project_demand_seed
4) wave1_luigi_report.md

Required columns for fact_pipeline_monthly:
- project_id
- plant
- material
- month
- raw_qty
- probability
- expected_qty
- requested_date
- revenue_tier
- customer_segment
- project_value
- expected_value
- priority_score
- mapping_ready_flag
- reason_code

Required columns for dim_project_priority:
- project_id
- probability_score
- urgency_score
- revenue_tier_score
- expected_value_score
- strategic_segment_score
- priority_score
- score_version

Priority score v1:
priority_score =
0.35 * probability_score +
0.20 * urgency_score +
0.20 * revenue_tier_score +
0.15 * expected_value_score +
0.10 * strategic_segment_score

Tasks:
1) inspect the backend audit and identify reusable legacy modules for pipeline loading or metadata normalization
2) document which legacy modules are reused, adapted, or ignored
3) normalize and unpivot 1_1 and 1_2
4) join 1_3 metadata
5) compute expected_qty = raw_qty * probability
6) compute expected_value = project_value * probability
7) compute normalized score components
8) compute priority_score
9) produce scenario seed tables for:
   - all_in
   - expected_value
   - high_confidence
10) surface unresolved joins explicitly with reason codes

Validation requirements:
- no duplicate (project_id, plant, material, month)
- probabilities in valid range
- expected_qty and expected_value computed deterministically
- priority score bounded and interpretable
- unresolved joins explicitly counted
- wave1_luigi_report.md must include KEEP / ADAPT / DEPRECATE / REPLACE decisions for any touched legacy modules

Deliverables:
- Python modules
- table outputs in processed/interim locations
- tests
- wave1_luigi_report.md summarizing:
  - reused legacy components
  - new modules created
  - schema compliance
  - edge cases
  - blockers for Wave 2

Done when:
Downstream agents can consume fact_pipeline_monthly and dim_project_priority without touching raw files directly.