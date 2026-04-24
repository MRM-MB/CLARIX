# Synthetic Data Policy

Date: 2026-04-18

Synthetic enrichment is allowed only to fill known repo-data gaps and must never obscure where the real dataset ends.

## Allowed Synthetic Tables

- `dim_country_cost_index_synth`
- `dim_shipping_lane_synth`
- `dim_disruption_scenario_synth`
- `dim_service_level_policy_synth`

## Required Rules

- every synthetic field must be labeled
- every synthetic table must include generation logic
- every synthetic dataset must be reproducible
- synthetic data must enrich the workflow, not hide the real-data limitations
- real and synthetic fields must remain distinguishable at schema level

## Table Requirements

### `dim_country_cost_index_synth`

Purpose:

- provide explainable labor, wage, and energy-cost multipliers by country

Minimum columns:

- `country_code`
- `labor_cost_index_synth`
- `energy_cost_index_synth`
- `generation_logic`
- `generation_version`
- `random_seed`

### `dim_shipping_lane_synth`

Purpose:

- provide origin-destination lanes, transit-time estimates, lane reliability, and cost proxies

Minimum columns:

- `lane_id`
- `origin_country`
- `destination_country`
- `transit_days_synth`
- `lane_cost_index_synth`
- `lane_reliability_synth`
- `generation_logic`
- `generation_version`
- `random_seed`

### `dim_disruption_scenario_synth`

Purpose:

- define disruption families and explainable impact multipliers

Minimum columns:

- `scenario_name`
- `scenario_family`
- `impact_scope`
- `capacity_multiplier_synth`
- `sourcing_multiplier_synth`
- `logistics_multiplier_synth`
- `reason_code`
- `generation_logic`
- `generation_version`
- `random_seed`

### `dim_service_level_policy_synth`

Purpose:

- convert revenue tier and urgency into service-level and expedite rules

Minimum columns:

- `revenue_tier`
- `urgency_band`
- `target_service_level_synth`
- `expedite_days_threshold_synth`
- `generation_logic`
- `generation_version`
- `random_seed`

## Generation Rules

- Prefer explicit rule-based generation over opaque simulation.
- If randomization is used, include a fixed `random_seed`.
- Generation logic must be stored as metadata columns and in code.
- Synthetic tables must be written to `project/data/synthetic/`.
- Each synthetic table should include a short README or code header describing the heuristic.

## Schema Separation Rules

- do not overwrite real columns with synthetic estimates
- keep real and synthetic columns side by side when both exist
- every synthetic table name must end in `_synth`
- every synthetic field must use the `_synth` suffix

## Usage Rules

- synthetic data may support logistics, disruption, service-level, and cost feasibility
- synthetic data may not be used to silently backfill missing real pipeline, BOM, inventory, or capacity rows
- when a recommendation depends on synthetic inputs, its `reason_code_detail` must mention the synthetic driver
