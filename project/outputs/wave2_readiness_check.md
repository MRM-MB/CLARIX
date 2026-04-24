# Wave 2 Readiness Check

Unified source-of-truth code lives under `project/src`.

## Required tables

- `fact_pipeline_monthly`: READY (13140 rows)
- `dim_project_priority`: READY (720 rows)
- `bridge_material_tool_wc`: READY (7625 rows)
- `fact_wc_capacity_weekly`: READY (17004 rows)
- `bridge_month_week_calendar`: READY (187 rows)
- `fact_finished_to_component`: READY (9490 rows)
- `fact_inventory_snapshot`: READY (7625 rows)
- `dim_procurement_logic`: READY (7625 rows)
- `dim_country_cost_index_synth`: READY (15 rows)
- `dim_shipping_lane_synth`: READY (225 rows)
- `dim_service_level_policy_synth`: READY (4 rows)

## Unification

- Root-level `src/` was legacy Wave 1 code and has been superseded by `project/src/`.
- All materializers now target `project/data/processed/` or `project/data/synthetic/`.
- Downstream Wave 2 work should import only from `project.src.*`.
