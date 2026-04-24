# Wave 6 Luigi Report

Date: 2026-04-18

## Objective

- built deterministic quarter-learning signals and quarter-to-quarter roll-forward inputs for the demand-side business layer.
- probability adjustments remain explicit signals only; no source probability values are overwritten.

## Inputs Used

- `fact_pipeline_quarterly`
- `fact_decision_history`
- `dim_project_priority`
- `fact_integrated_risk`

## Learning Logic

- `repeated_risk_flag`: current quarter top driver matches the prior quarter top driver within the same scope/project.
- `repeated_action_flag`: the inherited previous action type repeats across consecutive quarters.
- `repeated_delay_flag`: the inherited action is a delay-style action (`wait`, `reschedule`, `reroute`, `expedite_shipping`) and still carries over.
- `confidence_adjustment_signal`: deterministic non-positive signal derived from repeated risk/action/delay plus low inherited confidence.

## Roll-Forward Logic

- `carry_over_probability_adjustment` reuses the confidence signal and stays separate from business-priority changes.
- `carry_over_priority_adjustment` increases planner attention for unresolved actions, repeated risks, repeated actions, and deferred projects, weighted by current priority band.
- `unresolved_action_penalty` is explicit and synthetic-labeled through the inherited `pending_outcome_synth` status from Wave 5.

## Validation Summary

- learning rows: `4,212`
- roll-forward rows: `3,861`
- repeated risk rows: `873`
- repeated action rows: `2824`
- repeated delay rows: `104`
- confidence adjustment distribution: `{-0.25: 24, -0.2: 548, -0.15000000000000002: 289, -0.1: 1897, -0.05: 838, 0.0: 616}`

## Cross-Wave Note

- Wave 5 Luigi uses `denmark_demo` and `global_reference`, while Wave 5 Lara/Carolina use `mvp_3plant`. Wave 6 therefore only materializes learning on the Luigi business scopes provided by its declared inputs.
- Wave 7 should unify scope identifiers across business, capacity, and material learning layers if a single integrated roll-forward policy is required.

## Top Roll-Forward Inputs

        scope_id from_quarter to_quarter project_id  carry_over_priority_adjustment  carry_over_probability_adjustment
global_reference      2027-Q1    2027-Q2  SF-100712                             0.3                              -0.20
    denmark_demo      2028-Q1    2028-Q2  SF-100023                             0.3                              -0.20
global_reference      2026-Q4    2027-Q1  SF-100712                             0.3                              -0.20
global_reference      2026-Q3    2026-Q4  SF-100712                             0.3                              -0.20
global_reference      2027-Q1    2027-Q2  SF-100719                             0.3                              -0.15
global_reference      2027-Q2    2027-Q3  SF-100719                             0.3                              -0.15
global_reference      2027-Q3    2027-Q4  SF-100719                             0.3                              -0.15
global_reference      2027-Q4    2028-Q1  SF-100719                             0.3                              -0.15
global_reference      2028-Q1    2028-Q2  SF-100719                             0.3                              -0.15
global_reference      2028-Q3    2028-Q4  SF-100716                             0.3                              -0.20
global_reference      2026-Q3    2026-Q4  SF-100065                             0.3                              -0.20
global_reference      2026-Q2    2026-Q3  SF-100065                             0.3                              -0.20
global_reference      2027-Q3    2027-Q4  SF-100063                             0.3                              -0.20
global_reference      2026-Q2    2026-Q3  SF-100663                             0.3                              -0.20
global_reference      2028-Q1    2028-Q2  SF-100070                             0.3                              -0.20
global_reference      2027-Q4    2028-Q1  SF-100070                             0.3                              -0.20
global_reference      2027-Q3    2027-Q4  SF-100070                             0.3                              -0.20
global_reference      2027-Q3    2027-Q4  SF-100053                             0.3                              -0.20
global_reference      2027-Q2    2027-Q3  SF-100053                             0.3                              -0.20
global_reference      2027-Q1    2027-Q2  SF-100053                             0.3                              -0.20
