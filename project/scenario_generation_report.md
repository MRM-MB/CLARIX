# Scenario Generation Report

Date: 2026-04-18

## Inputs Used

- `fact_pipeline_monthly`
- `dim_project_priority`
- `bridge_material_tool_wc`
- `bridge_month_week_calendar`

## Scenario Logic

- `all_in`: weekly raw demand allocated from monthly `raw_qty`; `scenario_confidence = 1.0`.
- `expected_value`: weekly expected demand allocated from monthly `expected_qty`; `scenario_confidence = probability`.
- `high_confidence`: uses raw weekly qty only for rows with `probability >= 0.70`; otherwise `expected_weekly_qty = 0`; confidence is `0.90` for included rows and `0.60` otherwise.
- `monte_carlo_light`: seeded Bernoulli simulation with `seed=42` and `n_trials=200`; weekly qty is monthly seeded mean allocation and confidence is derived from sampling error.

## Validation

- rows: `58156`
- scenarios: `4`
- duplicate `(scenario, project_id, plant, material, week)` keys: `0`
- unmapped rows retained: `2868`
- demand by scenario: `{'all_in': 12193337.97, 'expected_value': 6397159.95, 'high_confidence': 5589771.35, 'monte_carlo_light': 6401404.98}`
- unmapped reason codes: `{'MISSING_PLANT_MATERIAL_MAPPING': 2868}`

## Notes

- Weekly allocation uses `bridge_month_week_calendar` and the month-level `month_week_weight`.
- `week` is stored as `YYYY-Www` to avoid collisions across years while preserving the prompt’s single `week` column.
- Unmapped rows are kept via left join to routing and flagged with `mapping_status = UNMAPPED`.
