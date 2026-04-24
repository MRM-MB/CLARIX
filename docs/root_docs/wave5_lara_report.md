# Wave 5 Lara Report — Scoped Regional Capacity Foundation

Date: 2026-04-18

## Scope

- scope_id: `mvp_3plant`
- plants: `['NW01', 'NW02', 'NW05']`
- description: MVP scope: 3 representative plants across NA/EU/APAC

## Inputs

- `fact_scenario_capacity_weekly` (Lara Wave 2)
- `fact_capacity_bottleneck_summary` (Lara Wave 2)
- `bridge_material_tool_wc` (Lara Wave 1)

## Outputs

- `fact_scoped_capacity_weekly`: 40,716 rows
- `fact_capacity_quarterly_snapshot`: 348 rows
- `fact_capacity_state_history`: 348 rows

## Coverage

- plants in scope: `['NW01', 'NW02', 'NW05']`
- unique work centers: `29`
- quarters covered: `['2026-Q1', '2026-Q2', '2026-Q3', '2026-Q4', '2027-Q1', '2027-Q2', '2027-Q3', '2027-Q4', '2028-Q1', '2028-Q2', '2028-Q3', '2028-Q4']`

## Quarterly Bottleneck Summary

- total bottleneck-weeks by quarter: `{'2026-Q1': 1131, '2026-Q2': 1131, '2026-Q3': 1131, '2026-Q4': 1131, '2027-Q1': 1131, '2027-Q2': 1131, '2027-Q3': 1131, '2027-Q4': 1131, '2028-Q1': 1131, '2028-Q2': 1131, '2028-Q3': 1131, '2028-Q4': 1131}`
- carry-over capacity risk pairs (WC bottlenecked in consecutive quarters): `319`

## State History Logic

- prior_quarter_bottleneck_flag: True if the preceding quarter had ≥1 bottleneck week
- carry_over_capacity_risk_flag: True if BOTH prior AND current quarter had bottleneck weeks
- prior_quarter_mitigation_used: lever from fact_capacity_bottleneck_summary
- learning_note: human-readable carry-over explanation per WC

## Validation

- scoped row count ≤ unscoped source row count (asserted in _scope_capacity_weekly)
- quarterly totals reconcile with weekly aggregates under same plant+scenario filter
- state history rows = quarterly rows (one history entry per snapshot row)
- prior-quarter lookups are deterministic — reproducible on re-run
- no hidden filtering logic — scope plants list is fully explicit
