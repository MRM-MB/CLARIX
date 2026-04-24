# Integrated Risk Base Report

Date: 2026-04-18

## Inputs

- `dim_project_priority`
- `fact_scenario_capacity_weekly`
- `fact_scenario_sourcing_weekly`
- `fact_scenario_logistics_weekly`

## Merge Logic

- base grain comes from `fact_scenario_logistics_weekly` because it already carries `scenario x project_id x plant x week`.
- capacity risk is aggregated to `scenario x plant x week` and joined onto project rows.
- sourcing and lead-time risk are aggregated to `scenario x plant x week` and joined onto project rows.
- `monte_carlo_light` uses `expected_value` capacity as explicit fallback because capacity Wave 2 did not materialize Monte Carlo rows.
- disruption and QA penalties remain explicit zero-value placeholders for Wave 4.

## Validation

- rows: `57792`
- duplicate grain rows: `0`
- non-zero disruption placeholders: `0`
- non-zero QA placeholders: `0`
- top drivers: `{'sourcing_risk': 54506, 'logistics_risk': 2868, 'lead_time_risk': 418}`
- average risk by scenario: `{'all_in': 0.7297, 'expected_value': 0.7297, 'high_confidence': 0.7211, 'monte_carlo_light': 0.7297}`
