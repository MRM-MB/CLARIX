# Wave 6 Lara Report — Maintenance & Downtime Simulation Engine

Date: 2026-04-18

## Inputs

- `fact_scoped_capacity_weekly` (Lara Wave 5)
- `fact_capacity_state_history` (Lara Wave 5)
- `bridge_material_tool_wc` (Lara Wave 1)

## Maintenance Scenarios

- **baseline_maintenance**: Nominal maintenance schedule per policy
- **maintenance_overrun**: Maintenance takes 50% longer + small unscheduled component
- **unexpected_breakdown**: On top of scheduled, 25% of nominal capacity lost to random breakdowns
- **preventive_maintenance_shift**: More frequent (75% interval) but shorter (70% duration) events

## Outputs

- `dim_maintenance_policy_synth`: 29 rows
  - trigger type distribution: `{'scheduled_preventive': 23, 'corrective_unscheduled': 3, 'regulatory_inspection': 3}`
- `fact_maintenance_downtime_calendar`: 18,096 rows
  - scenario distribution: `{'baseline_maintenance': 4524, 'maintenance_overrun': 4524, 'unexpected_breakdown': 4524, 'preventive_maintenance_shift': 4524}`
- `fact_effective_capacity_weekly_v2`: 18,096 rows
- `fact_maintenance_impact_summary`: 116 rows

## Impact Analysis

- mean pct capacity lost by scenario: `{'baseline_maintenance': 0.018, 'maintenance_overrun': 0.027, 'preventive_maintenance_shift': 0.0166, 'unexpected_breakdown': 0.018}`
- max additional avg overload hours by scenario: `{'baseline_maintenance': 2.0, 'maintenance_overrun': 5.4077, 'preventive_maintenance_shift': 1.9385, 'unexpected_breakdown': 23.5385}`

## Validation

- effective_available_capacity_hours ≤ nominal_available_capacity_hours (enforced by clip)
- every downtime event references a policy_id with explicit interval and duration
- all synthetic maintenance assumptions carry synthetic_flag=True
- before/after comparison available in fact_maintenance_impact_summary
- phase offsets are seeded and deterministic — reproducible on re-run
