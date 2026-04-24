# Wave 5 Carolina Report — Scoped Sourcing & Quarter History

## Scope Definition

MVP scope: plants NW01 (North America), NW02 (Europe West), NW05 (East Asia)
Scope ID: `mvp_3plant`

## Outputs Produced

| File | Rows | Cols | Notes |
|------|------|------|-------|
| `fact_scoped_sourcing_weekly.csv` | 12,428 | 12 | Subset of fact_scenario_sourcing_weekly for 3 plants |
| `fact_scoped_logistics_weekly.csv` | 12,544 | 13 | Subset of fact_scenario_logistics_weekly for 3 plants |
| `fact_sourcing_quarterly_snapshot.csv` | 1,140 | 12 | Aggregated by (scope_id, scenario, plant, material, quarter) |
| `fact_logistics_quarterly_snapshot.csv` | 144 | 13 | Aggregated by (scope_id, scenario, plant, country, quarter) |
| `fact_material_decision_history.csv` | 66 | 10 | Q1 carry-over risk per (plant, material) |

## Scoped Filter

- `fact_scoped_sourcing_weekly`: 51,276 base rows -> 12,428 scoped rows (NW01/NW02/NW05 only)
- `fact_scoped_logistics_weekly`: 57,792 base rows -> 12,544 scoped rows (NW01/NW02/NW05 only)
- Row reconciliation: scoped <= base (validated by assertion in filter functions)
- `scope_id` column added to both outputs with value `mvp_3plant`

## Quarterly Snapshots

- Week -> quarter mapping: W01-W13=Q1, W14-W26=Q2, W27-W39=Q3, W40-W53=Q4
- Quarters covered: 2026-Q1 through 2028-Q4 (12 quarters across 3-year horizon)
- Sourcing snapshot: real data — `synthetic_dependency_flag=False`
- Logistics snapshot: uses synthetic shipping lane dimensions — `synthetic_dependency_flag=True`
- Sourcing aggregates: total_demand_qty, total_shortage_qty, shortage_weeks_count, avg/max sourcing_risk_score, earliest_recommended_order_date
- Logistics aggregates: route_count, avg_transit_time_days, avg/total shipping costs, pct_on_time_feasible, pct_expedite_option, avg_logistics_risk_score

## Material Decision History (Q1 -> Q2)

- Source: `expected_value` scenario, Q1 data only (quarter_id ends in "Q1")
- One row per (scope_id, quarter_id, plant, component_material) — 66 materials flagged
- `carry_over_material_risk_flag` triggers: shortage in Q1 OR (expedite needed AND on-time infeasible)
- `learning_note`: human-readable guidance derived from flag combination:
  - carry_over=True: "Q1 had shortages or expedite issues — increase safety buffer in Q2"
  - shortage only: "Q1 shortage detected — order earlier in Q2"
  - expedite only: "Q1 required expediting — review lead time assumptions"
  - all OK: "Q1 performance acceptable — maintain current strategy"
- Real data result: 66/66 materials flagged as carry-over risk (100%) — all NW01/NW02/NW05 materials in the expected_value Q1 snapshot showed shortages, reflecting the tightness of the MVP scope plants in Q1 2026

## Synthetic Dependency Visibility

- `fact_logistics_quarterly_snapshot`: `synthetic_dependency_flag=True` (inherits from synthetic shipping lane data in `dim_shipping_lane_synth.csv`)
- `fact_sourcing_quarterly_snapshot`: `synthetic_dependency_flag=False` (sourcing data is real — from fact_scenario_sourcing_weekly)
- `fact_material_decision_history`: no synthetic_dependency_flag column (derived logic only, no direct synthetic join)

## Test Coverage

29 tests — all passing:
- 9 parametrized week_to_quarter boundary tests (W01/W13/W14/W26/W27/W39/W40/W52/W53)
- 6 scoped filter tests (plant subset, row count, scope_id column)
- 6 quarterly snapshot tests (quarter format, uniqueness, synthetic flags)
- 5 decision history tests (required columns, bool type, non-null notes, uniqueness, Q1 source)
- 3 integration tests against real processed CSVs

## Blockers for Wave 6

None. All 5 outputs stable for downstream consumption.

## Files

- `project/src/wave5/scoped_filter.py` — filter_sourcing, filter_logistics, DEFAULT_SCOPE
- `project/src/wave5/quarterly_snapshot.py` — week_to_quarter, build_sourcing_quarterly_snapshot, build_logistics_quarterly_snapshot
- `project/src/wave5/decision_history.py` — build_material_decision_history
- `project/src/wave5/runner.py` — run_carolina_wave5 orchestrator
- `project/tests/test_wave5_carolina.py` — 29 tests
