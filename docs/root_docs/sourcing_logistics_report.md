# Wave 2 Carolina Report — Sourcing & Logistics Feasibility

## Inputs Used

| Input | File | Source | Status |
|-------|------|--------|--------|
| Finished-goods BOM | `fact_finished_to_component.csv` | Wave 1 Carolina | Real |
| Inventory snapshot | `fact_inventory_snapshot.csv` | Wave 1 Carolina | Real |
| Procurement logic | `dim_procurement_logic.csv` | Wave 1 Carolina | Real |
| Shipping lanes | `dim_shipping_lane_synth.csv` | Wave 1 Carolina (synthetic) | Synthetic |
| Country cost index | `dim_country_cost_index_synth.csv` | Wave 1 Carolina (synthetic) | Synthetic |
| Service level policy | `dim_service_level_policy_synth.csv` | Wave 1 Carolina (synthetic) | Synthetic |
| Translated project demand | `fact_translated_project_demand_weekly.csv` | Luigi Wave 2 | **MISSING — synthetic stub used** |

> `fact_translated_project_demand_weekly.csv` was not present at pipeline execution time.
> A synthetic stub was generated from unique (plant, header_material) pairs in the BOM,
> covering W01–W12 2026 at three scenario quantities (50 / 25 / 10 units/week).

---

## Outputs Produced

| File | Location | Rows | Scenarios | Notes |
|------|----------|------|-----------|-------|
| `fact_scenario_sourcing_weekly.csv` | `processed/` | Varies | all_in, expected_value, high_confidence | BOM-exploded weekly sourcing requirements |
| `fact_scenario_logistics_weekly.csv` | `processed/` | Varies | all_in, expected_value, high_confidence | Logistics feasibility per demand row |

---

## Sourcing Engine Logic

- **BOM explosion**: `fact_finished_to_component` joined on `(plant, header_material)` to expand finished goods demand to raw component demand
- **Component demand**: `component_demand_qty = expected_weekly_qty × effective_component_qty`
- **Aggregation**: Sum `component_demand_qty` by `(scenario, plant, component_material, week)`
- **Available qty**: `stock_qty + in_transit_qty` (in-transit treated as available within the week)
- **Shortage**: `max(0, component_demand_qty - available_qty)`
- **Order date**: `week_start_date - lead_time_days` (week string parsed via ISO week format `%G-W%V-%u`)
- **Coverage**: `(available_qty / max(component_demand_qty, 0.001)) × 7` days
- **Risk score**: `clamp(shortage_qty / max(component_demand_qty, 1), 0, 1)`
- **Default lead time**: 30 days when `dim_procurement_logic` has no entry for a component

---

## Logistics Engine Logic

- **Origin country**: mapped from plant code using `PLANT_TO_COUNTRY` lookup (15 plants)
- **Destination country**: estimated from plant region grouping (synthetic assumption — no real order destination data available)
- **Shipping cost**: `base_shipping_cost_synth × max(expected_weekly_qty, 1) × 0.01` (per-unit proxy)
- **Landed cost**: `shipping_cost × (1 + labor_index×0.1 + energy_index×0.05 + overhead_index×0.05)`
- **Revenue tier**: derived from `priority_score` — Small (<0.3), Medium (0.3–0.5), Large (0.5–0.75), Strategic (≥0.75)
- **On-time feasibility**: `transit_time_days ≤ max_allowed_late_days + 28` (delivery assumed 4 weeks from week start)
- **Logistics risk score**: `(1 - route_reliability_score_synth) × disruption_sensitivity_score_synth`, clamped [0, 1]
- **All logistics rows carry** `synthetic_dependency_flag = True`

---

## Synthetic Dependency Warning

The following outputs depend **entirely** on synthetic input data:

| Output Column | Synthetic Source |
|---------------|-----------------|
| `transit_time_days` | `dim_shipping_lane_synth.csv` |
| `shipping_cost` | `dim_shipping_lane_synth.csv` |
| `landed_cost_proxy` | `dim_shipping_lane_synth.csv` + `dim_country_cost_index_synth.csv` |
| `on_time_feasible_flag` | `dim_service_level_policy_synth.csv` + shipping lane synth |
| `expedite_option_flag` | `dim_service_level_policy_synth.csv` |
| `logistics_risk_score` | `dim_shipping_lane_synth.csv` |
| `destination_country` | Hardcoded plant-region mapping (no real order data) |
| All sourcing rows | `fact_translated_project_demand_weekly` was a synthetic stub (W01–W12 2026, fixed quantities) |

All logistics rows carry `synthetic_dependency_flag = True` to make this dependency machine-readable.

**These outputs should NOT be used for real procurement decisions without replacing the synthetic dimensions with real data.**

---

## Blockers for Wave 3

1. **`fact_translated_project_demand_weekly` from Luigi Wave 2** — this is the critical missing input. When available, it replaces the synthetic stub and provides real project-level weekly demand with proper probability weighting, tool routing, and work center assignments. Drop `processed/fact_translated_project_demand_weekly.csv` into the `processed/` directory and re-run `python -m src.carolina.wave2_pipeline` to use real demand automatically.

2. **Destination country logic** — currently estimated from plant region. Replace with real project region data from sheet `1_3 Export Project list` (column `Region` or similar) joined via `project_id`. This requires the Luigi Wave 2 demand output to carry the project region field through.

3. **Shipping lane coverage** — the synthetic lane matrix covers all 15 country pairs used in the plant mapping. If real shipping routes differ (e.g. NW08 ships to US, not DE), update `PLANT_TO_DEST_COUNTRY` in `logistics_engine.py`.

4. **Lead time units** — `dim_procurement_logic.lead_time_days_or_weeks` is treated as days throughout. If some entries are in weeks, a unit-aware parse is needed.
