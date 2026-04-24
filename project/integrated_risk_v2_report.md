# Integrated Risk V2 Report

Date: 2026-04-18

## Inputs

- `fact_integrated_risk`
- `fact_quarter_rollforward_inputs`
- `fact_quarter_learning_signals`
- `fact_delivery_risk_rollforward`
- `fact_maintenance_impact_summary` (supplemental Wave 6 Lara output used to satisfy maintenance-risk requirement)

## What Changed From V1

- v1 was project-week risk without explicit scope or quarter context.
- v2 adds `scope_id` and `quarter_id` so the same project-week can be evaluated inside different business scopes.
- v2 adds explicit `delivery_risk_score`, `maintenance_risk_score`, and signed `quarter_learning_penalty_or_boost`.
- v2 keeps v1 risk drivers intact and uses additive adjustments so scores remain comparable to v1 rather than being fully re-based.

## V2 Formula

- `risk_score_v2 = risk_score_v1 + 0.10*delivery_risk_score + 0.05*maintenance_risk_score + 0.10*max(quarter_learning_penalty_or_boost, 0)`
- `action_score_v2 = clip(priority_score + quarter_learning_penalty_or_boost, 0, 1) * risk_score_v2`
- negative learning values reduce business weight in `action_score_v2` but do not hide the original v1 risk signal.

## Validation

- rows: `71404`
- duplicate grain rows: `0`
- bounded risk violations: `0`
- bounded action violations: `0`
- non-zero delivery rows: `3260`
- non-zero maintenance rows: `13144`
- non-zero learning rows: `68700`
- mean absolute risk delta vs v1: `0.0115`
- score comparison summary: `{'v1_mean_risk': 0.6939, 'v2_mean_risk': 0.7054, 'v1_mean_action': 0.3428, 'v2_mean_action': 0.5012}`
- top drivers: `{'sourcing_risk': 46685, 'capacity_risk': 21859, 'quarter_learning': 2728, 'logistics_risk': 132}`

## Scope Note

- Luigi business scopes are `global_reference` and `denmark_demo`.
- delivery and maintenance feeds come from `mvp_3plant` assets built by other agents, so Wave 7 uses project-quarter delivery joins and plant-level maintenance joins as explicit adapters instead of pretending the scope models already match.

## Top 20 V2 Rows

        scope_id        scenario quarter_id project_id plant  risk_score_v2  action_score_v2    top_driver
global_reference  expected_value    2028-Q4  SF-100675  NW05       0.875159         0.875159 sourcing_risk
global_reference high_confidence    2028-Q4  SF-100675  NW05       0.875159         0.875159 sourcing_risk
global_reference          all_in    2028-Q4  SF-100675  NW05       0.875159         0.875159 sourcing_risk
global_reference  expected_value    2028-Q4  SF-100675  NW05       0.875158         0.875158 capacity_risk
global_reference high_confidence    2028-Q4  SF-100675  NW05       0.875158         0.875158 capacity_risk
global_reference          all_in    2028-Q4  SF-100675  NW05       0.875158         0.875158 capacity_risk
global_reference high_confidence    2028-Q3  SF-100675  NW05       0.875158         0.875158 sourcing_risk
global_reference  expected_value    2028-Q3  SF-100675  NW05       0.875158         0.875158 sourcing_risk
global_reference          all_in    2028-Q3  SF-100675  NW05       0.875158         0.875158 sourcing_risk
global_reference  expected_value    2028-Q3  SF-100675  NW05       0.875157         0.875157 capacity_risk
global_reference high_confidence    2028-Q3  SF-100675  NW05       0.875157         0.875157 capacity_risk
global_reference  expected_value    2028-Q3  SF-100675  NW05       0.875157         0.875157 capacity_risk
global_reference          all_in    2028-Q3  SF-100675  NW05       0.875157         0.875157 capacity_risk
global_reference          all_in    2028-Q3  SF-100675  NW05       0.875157         0.875157 capacity_risk
global_reference high_confidence    2028-Q3  SF-100675  NW05       0.875157         0.875157 capacity_risk
global_reference high_confidence    2028-Q4  SF-100675  NW05       0.875153         0.875153 capacity_risk
global_reference  expected_value    2028-Q4  SF-100675  NW05       0.875153         0.875153 capacity_risk
global_reference          all_in    2028-Q4  SF-100675  NW05       0.875153         0.875153 capacity_risk
global_reference high_confidence    2028-Q1  SF-100675  NW05       0.875150         0.875150 sourcing_risk
global_reference          all_in    2028-Q1  SF-100675  NW05       0.875150         0.875150 sourcing_risk
