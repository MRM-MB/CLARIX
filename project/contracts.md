# Contracts

Date: 2026-04-18

This document defines the shared canonical contracts, scenario families, scoring rules, reason-code rules, and merge rules for all future implementation agents.

## Contract Rules

- Gold tables are source-of-truth analytics contracts.
- All tables must be reproducible from repo-backed raw or synthetic inputs.
- Missing mappings must be flagged with reason codes, never dropped silently.
- Real and synthetic fields must remain distinguishable at schema level.
- New columns may be appended safely, but existing column meaning may not change without a breaking-change note.

## Naming Conventions

### Synthetic-field naming convention

- synthetic columns must use suffix `_synth`
- synthetic boolean flags must use prefix `is_synth_`
- synthetic score drivers should use suffix `_synth_score`

Examples:

- `lane_transit_days_synth`
- `is_synth_transit_days`
- `country_energy_cost_synth_score`

### Scenario naming convention

- scenario keys use lowercase snake_case
- scenario families are stable enums
- every scenario record must include `scenario_name`, `scenario_family`, and `scenario_confidence`

### Reason code rules

- use uppercase snake case
- one primary `reason_code`
- optional pipe-delimited `reason_code_detail`
- reason codes must point to observable drivers, not conclusions

Examples:

- `MISSING_WC_MAPPING`
- `ATP_BELOW_SAFETY_STOCK`
- `WC_UTILIZATION_CRITICAL`
- `LANE_RELIABILITY_WEAK`

## Gold Tables

### `fact_pipeline_monthly`

- Grain: one row per `project_id x plant x material x month`
- Required keys:
  - `project_id`
  - `plant`
  - `material`
  - `period_date`
- Required columns:
  - `project_name`
  - `status`
  - `material_description`
  - `type`
  - `raw_qty`
  - `probability`
  - `expected_qty`
  - `project_value`
  - `expected_value`
  - `priority_score`
  - `mapping_ready_flag`
  - `requested_delivery_date`
  - `revenue_tier`
  - `customer_segment`
  - `source_system`
  - `reason_code`
- Nullable columns:
  - `tool`
  - `work_center`
  - `work_center_full`
  - `mapping_gap_detail`
- Enum columns:
  - `status`
  - `type`
  - `revenue_tier`
- Legacy-to-canonical mapping rules:
  - `qty` in legacy becomes `raw_qty`
  - `probability_frac` becomes `probability`
  - preserve legacy `expected_qty`
  - unresolved route/tool/WC values remain null and get mapping reason codes

### `scenario_project_demand_seed`

- Grain: one row per `scenario_name x project_id x plant x material x month`
- Required keys:
  - `scenario_name`
  - `project_id`
  - `plant`
  - `material`
  - `month`
- Required columns:
  - `scenario_family`
  - `scenario_confidence`
  - `raw_qty`
  - `probability`
  - `scenario_qty`
  - `project_value`
  - `expected_value`
  - `priority_score`
  - `mapping_ready_flag`
  - `reason_code`
- Enum columns:
  - `scenario_name` in `{all_in, expected_value, high_confidence}`

### `dim_project_priority`

- Grain: one row per `project_id`
- Required keys:
  - `project_id`
- Required columns:
  - `project_name`
  - `probability_score`
  - `urgency_score`
  - `revenue_tier_score`
  - `expected_value_score`
  - `strategic_segment_score`
  - `priority_score`
  - `priority_band`
  - `reason_code`
- Nullable columns:
  - `owner`
  - `region`
  - `segment`
- Enum columns:
  - `priority_band` in `{low, medium, high, critical}`

### `bridge_material_tool_wc`

- Grain: one row per `plant x material x tool x work_center`
- Required keys:
  - `plant`
  - `material`
  - `tool`
  - `work_center`
- Required columns:
  - `work_center_full`
  - `cycle_time_min`
  - `material_status`
  - `routing_source`
  - `reason_code`
- Nullable columns:
  - `tool`
  - `work_center`
  - `work_center_full`
- Enum columns:
  - `routing_source` in `{legacy_tool_master, inferred, synthetic}`

### `fact_wc_capacity_weekly`

- Grain: one row per `plant x work_center x iso_year x iso_week`
- Required keys:
  - `plant`
  - `work_center`
  - `year`
  - `week`
- Required columns:
  - `week_start`
  - `available_hours`
  - `baseline_demand_qty`
  - `source_system`
  - `reason_code`
- Nullable columns:
  - none

### `bridge_month_week_calendar`

- Grain: one row per `period_month x iso_year x iso_week`
- Required keys:
  - `period_date`
  - `year`
  - `week`
- Required columns:
  - `month_number`
  - `days_in_month_week_overlap`
  - `month_week_weight`
  - `week_start`
  - `calendar_source`
- Nullable columns:
  - `plant`
- Notes:
  - optional plant-specific extension is allowed for working-day-weighted variants

### `fact_finished_to_component`

- Grain: one row per `plant x header_material x component_material`
- Required keys:
  - `plant`
  - `header_material`
  - `component_material`
- Required columns:
  - `qty_per`
  - `qty_per_effective`
  - `lead_time_weeks`
  - `component_description`
  - `bom_status`
  - `reason_code`

### `fact_inventory_snapshot`

- Grain: one row per `snapshot_date x plant x material`
- Required keys:
  - `snapshot_date`
  - `plant`
  - `material`
- Required columns:
  - `material_description`
  - `stock_qty`
  - `atp_qty`
  - `safety_stock_qty`
  - `in_transit_qty`
  - `total_stock_value_eur`
  - `reason_code`

### `fact_scenario_capacity_weekly`

- Grain: one row per `scenario_name x plant x work_center x year x week`
- Required keys:
  - `scenario_name`
  - `plant`
  - `work_center`
  - `year`
  - `week`
- Required columns:
  - `demand_qty`
  - `demand_hours`
  - `available_hours`
  - `utilization`
  - `capacity_risk`
  - `capacity_status`
  - `scenario_confidence`
  - `reason_code`
- Enum columns:
  - `capacity_status` in `{ok, warn, critical}`

### `fact_scenario_sourcing_weekly`

- Grain: one row per `scenario_name x plant x component_material x year x week`
- Required keys:
  - `scenario_name`
  - `plant`
  - `component_material`
  - `year`
  - `week`
- Required columns:
  - `gross_requirement_qty`
  - `projected_atp_qty`
  - `safety_stock_qty`
  - `shortfall_qty`
  - `lead_time_weeks`
  - `sourcing_risk`
  - `order_by_date`
  - `scenario_confidence`
  - `reason_code`

### `fact_scenario_logistics_weekly`

- Grain: one row per `scenario_name x origin_country x destination_country x year x week`
- Required keys:
  - `scenario_name`
  - `origin_country`
  - `destination_country`
  - `year`
  - `week`
- Required columns:
  - `lane_id`
  - `transit_days_synth`
  - `landed_cost_index_synth`
  - `lane_reliability_synth`
  - `logistics_risk`
  - `scenario_confidence`
  - `reason_code`

### `fact_integrated_risk`

- Grain: one row per `scenario_name x project_id x plant x material x year x week`
- Required keys:
  - `scenario_name`
  - `project_id`
  - `plant`
  - `material`
  - `year`
  - `week`
- Required columns:
  - `priority_score`
  - `capacity_risk`
  - `sourcing_risk`
  - `logistics_risk`
  - `disruption_risk`
  - `lead_time_risk`
  - `data_quality_penalty`
  - `risk_score`
  - `scenario_confidence`
  - `reason_code`
  - `reason_code_detail`

### `fact_planner_actions`

- Grain: one row per `scenario_name x project_id x plant x material x recommended_action`
- Required keys:
  - `scenario_name`
  - `project_id`
  - `plant`
  - `material`
  - `recommended_action`
- Required columns:
  - `priority_score`
  - `risk_score`
  - `scenario_confidence`
  - `action_score`
  - `recommended_owner`
  - `reason_code`
  - `reason_code_detail`
  - `action_rank`
  - `action_status`
- Enum columns:
  - `recommended_action` in `{buy, wait, reroute, upshift, reschedule, expedite, escalate}`
  - `action_status` in `{proposed, accepted, rejected, simulated}`

### `dim_region_scope`

- Grain: one row per `scope_id`
- Required keys:
  - `scope_id`
- Required columns:
  - `region_name`
  - `included_plants`
  - `included_factories_note`
  - `scope_rule`
  - `active_flag`
- Notes:
  - region scopes are explicit business filters, not ERP geography master data
  - `included_plants` stores a comma-delimited stable plant list

### `fact_pipeline_quarterly`

- Grain: one row per `scope_id x quarter_id x project_id x plant x material`
- Required keys:
  - `scope_id`
  - `quarter_id`
  - `project_id`
  - `plant`
  - `material`
- Required columns:
  - `raw_qty_quarter`
  - `expected_qty_quarter`
  - `expected_value_quarter`
  - `priority_score`
  - `requested_date_min`
  - `requested_date_max`

### `fact_quarter_business_snapshot`

- Grain: one row per `scope_id x quarter_id`
- Required keys:
  - `scope_id`
  - `quarter_id`
- Required columns:
  - `total_projects`
  - `total_expected_qty`
  - `total_expected_value`
  - `avg_priority_score`
  - `high_confidence_project_count`
  - `strategic_project_count`

### `fact_decision_history`

- Grain: one row per `scope_id x quarter_id x project_id`
- Required keys:
  - `scope_id`
  - `quarter_id`
  - `project_id`
- Required columns:
  - `previous_action_type`
  - `previous_action_score`
  - `previous_top_driver`
  - `previous_confidence`
  - `action_outcome_status`
  - `carry_over_flag`
  - `learning_note`
- Notes:
  - history is quarter-to-quarter state carry-forward for the business layer
  - any inferred or pending outcome values must be labeled explicitly in field values

### `fact_quarter_rollforward_inputs`

- Grain: one row per `scope_id x from_quarter x to_quarter x project_id`
- Required keys:
  - `scope_id`
  - `from_quarter`
  - `to_quarter`
  - `project_id`
- Required columns:
  - `carry_over_probability_adjustment`
  - `carry_over_priority_adjustment`
  - `unresolved_action_penalty`
  - `deferred_project_flag`
  - `rollforward_note`
- Notes:
  - adjustments are reusable signals for next-quarter planning inputs
  - the table must not overwrite base probability or base priority in source dimensions

### `fact_quarter_learning_signals`

- Grain: one row per `scope_id x quarter_id x project_id`
- Required keys:
  - `scope_id`
  - `quarter_id`
  - `project_id`
- Required columns:
  - `repeated_risk_flag`
  - `repeated_action_flag`
  - `repeated_delay_flag`
  - `confidence_adjustment_signal`
  - `explanation_note`
- Notes:
  - learning signals are explainable intermediate outputs for later policy layers
  - confidence signals must remain separate from base probability and from business-priority adjustments

### `fact_integrated_risk_v2`

- Grain: one row per `scope_id x scenario x quarter_id x project_id x plant x week`
- Required keys:
  - `scope_id`
  - `scenario`
  - `quarter_id`
  - `project_id`
  - `plant`
  - `week`
- Required columns:
  - `priority_score`
  - `capacity_risk_score`
  - `sourcing_risk_score`
  - `logistics_risk_score`
  - `disruption_risk_score`
  - `delivery_risk_score`
  - `maintenance_risk_score`
  - `quarter_learning_penalty_or_boost`
  - `risk_score_v2`
  - `action_score_v2`
  - `top_driver`
  - `explainability_note`
- Notes:
  - v2 must remain comparable to `fact_integrated_risk` v1 by preserving all original visible risk drivers
  - quarter-aware learning adjustments must remain explicit, signed, and auditable

## Scoring Contracts

### Formula 1

`expected_qty = raw_qty * probability`

### Formula 2

`expected_value = project_value * probability`

### Formula 3: business priority score

```text
priority_score =
0.35 * probability_score +
0.20 * urgency_score +
0.20 * revenue_tier_score +
0.15 * expected_value_score +
0.10 * strategic_segment_score
```

Implementation notes:

- all component scores must be normalized to `0..1`
- `priority_score` must remain in `0..1`
- each component must be exposed as a separate column in `dim_project_priority`

### Formula 4: operational risk score

```text
risk_score =
0.30 * capacity_risk +
0.25 * sourcing_risk +
0.20 * logistics_risk +
0.10 * disruption_risk +
0.10 * lead_time_risk +
0.05 * data_quality_penalty
```

Implementation notes:

- all inputs normalized to `0..1`
- score must be stored in `fact_integrated_risk`
- driver columns must remain visible

### Formula 5: final action score

```text
action_score = priority_score * risk_score * scenario_confidence
```

Implementation notes:

- `scenario_confidence` must be `0..1`
- `action_rank` is descending by `action_score` within a planning run

## Scenario Families

Mandatory scenarios:

- `all_in`
- `expected_value`
- `high_confidence`
- `monte_carlo_light`
- `baseline_logistics`
- `expedited_shipping`
- `fuel_price_spike`
- `border_delay`
- `lane_blockage`
- `war_disruption`
- `plant_outage`
- `energy_shock`
- `conflict_disruption`

Recommended family grouping:

| Scenario name | Scenario family |
|---|---|
| `all_in` | `pipeline` |
| `expected_value` | `pipeline` |
| `high_confidence` | `pipeline` |
| `monte_carlo_light` | `pipeline` |
| `baseline_logistics` | `logistics` |
| `expedited_shipping` | `logistics` |
| `fuel_price_spike` | `logistics` |
| `border_delay` | `disruption` |
| `lane_blockage` | `disruption` |
| `war_disruption` | `disruption` |
| `plant_outage` | `disruption` |
| `energy_shock` | `disruption` |
| `conflict_disruption` | `disruption` |

## Legacy-To-Canonical Mapping Rules

- legacy `fact_pipeline_monthly` maps directly to gold `fact_pipeline_monthly`, but rename `qty` to `raw_qty` in contract-facing outputs
- legacy `dim_project` is the seed for `dim_project_priority`
- legacy `bridge_material_tool_wc` is retained but enriched with `work_center_full`, `routing_source`, and mapping reason codes
- legacy `fact_wc_capacity_weekly`, `fact_inventory_snapshot`, and `fact_finished_to_component` map directly with additive columns allowed
- legacy engine outputs must be written into explicit scenario facts rather than passed directly to UI consumers

## Merge Rules For Future Agents

### Source-of-truth files

- schema and scoring rules: `contracts.md`
- migration sequencing: `migration_plan.md`
- reuse decisions: `backend_audit.md` and `legacy_map.md`
- assumptions: `assumptions.md`
- synthetic policy: `synthetic_data_policy.md`

### How to add new columns safely

- append columns; do not repurpose existing ones
- update `contracts.md` before or with implementation
- mark nullable status explicitly
- add a reason code when the new column can be unavailable

### How to add synthetic fields safely

- use `_synth` naming
- document generator logic and reproducibility in `synthetic_data_policy.md`
- do not replace real columns with synthetic ones unless both are preserved separately

### How to register new assumptions

- append to `assumptions.md` using:
  - `ASSUMPTION_ID | description | rationale | impact | synthetic=true/false`

### How to report breaking changes

- add a `BREAKING CHANGE` note in the relevant markdown file
- list impacted tables, columns, and consumers
- provide migration path or adapter note

### How to preserve compatibility with reusable old backend components

- prefer wrappers in `src/legacy_adapters/`
- keep legacy field names available inside adapters where needed
- expose contract-shaped outputs at adapter boundaries
