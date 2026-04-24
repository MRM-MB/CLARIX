# planner_actions_v2_report.md

Wave 7 Lara — Maintenance-aware, region-scoped, quarter-aware planner action engine

Date: 2026-04-18

## Inputs

- `fact_integrated_risk` (Wave 5)
- `fact_effective_capacity_weekly_v2` (Wave 6 Lara)
- `fact_maintenance_impact_summary` (Wave 6 Lara)
- `dim_region_scope` (Wave 1)
- `dim_action_policy` (Wave 3)
- `fact_quarter_service_memory` (Wave 6 Carolina)

## Action Families

| Action | Description |
|--------|-------------|
| buy_now | Order immediately — sourcing risk above threshold |
| hedge_inventory | Add safety stock buffer — moderate sourcing risk |
| upshift | Increase shift hours — capacity risk detected |
| reschedule | Defer/spread production — manageable risk level |
| split_production | Distribute load across plants/weeks — critical capacity |
| escalate | Escalate to management — risk above safe operating range |
| reroute | Switch shipping lane — high logistics risk |
| expedite_shipping | Expedite freight — logistics pressure |
| shift_maintenance | Move maintenance to lower-load window — maintenance conflicts high-load period |
| protect_capacity_window | Defer maintenance — bottleneck WC has scheduled downtime |
| wait | No action — risk within acceptable range |

## Output

- `fact_planner_actions_v2`: 5,672 rows
  - scope_ids: `['denmark_demo', 'global_reference']`
  - scenarios: `['all_in', 'expected_value', 'high_confidence', 'monte_carlo_light']`
  - quarters: `['2026-Q1', '2026-Q2', '2026-Q3', '2026-Q4', '2027-Q1', '2027-Q2', '2027-Q3', '2027-Q4', '2028-Q1', '2028-Q2', '2028-Q3', '2028-Q4']`
  - action type distribution: `{'buy_now': 3920, 'shift_maintenance': 581, 'escalate': 561, 'protect_capacity_window': 240, 'split_production': 139, 'wait': 110, 'hedge_inventory': 107, 'upshift': 14}`
  - avg action_score: 0.3516
  - avg confidence: 0.7933
  - maintenance-specific actions (shift_maintenance + protect_capacity_window): 821

## Design Decisions

- **Grain:** (scope_id, scenario, quarter_id, project_id, plant) — one action per combination
- **Risk aggregation:** integrated_risk weekly rows aggregated to quarter by mean; mode of top_driver
- **Scope assignment:** plant → region via dim_region_scope.included_plants; fallback to global_reference
- **Maintenance context:** derived from fact_maintenance_impact_summary (worst WC per plant)
- **Protect opportunity:** detected when effective_capacity has bottleneck_flag=True AND scheduled_maintenance_hours>0 in same WC-week
- **Caution carry-over:** service_memory carry_over_service_caution_flag boosts action_score by 5%
- **Reroute target:** plant with lowest avg capacity_risk in same scope+scenario+quarter
- **Deterministic:** seeded inputs, no randomness

## Validation

- Every action maps to a visible driver (top_driver in explanation_trace)
- maintenance-related actions carry maint_severity and has_protect_opportunity in trace
- action_score ∈ [0, 1]
- confidence ∈ [0, 1]
- No null scope_id, scenario, quarter_id, project_id, plant
- Unique on natural key (scope_id, scenario, quarter_id, project_id, plant)
