# Wave 1 Luigi Report

Date: 2026-04-18

## Legacy Component Decisions

`clarix.data_loader` | canonical workbook ingestion and monthly unpivot | action=KEEP | reused directly through `project/src/legacy_adapters/legacy_loader.py` because it already normalizes 1_1, 1_2, and 1_3 reliably

`CanonicalData.fact_pipeline_monthly` | legacy monthly pipeline fact | action=ADAPT | reused as the Wave 1 base and reshaped to the shared contract with explicit mapping flags and de-duplication at `(project_id, plant, material, month)` grain

`CanonicalData.dim_project` | legacy project metadata dimension | action=ADAPT | reused as the seed for `dim_project_priority` and value/date metadata enrichment

`clarix.engine._apply_scenario()` | legacy scenario transform pattern | action=ADAPT | logic concept preserved, but Wave 1 emits explicit `scenario_project_demand_seed` rows instead of relying on UI-time transforms

`notebooks/starter_notebook.ipynb` | exploratory notebook | action=DEPRECATE | not used in Wave 1 because downstream agents need stable contracts, not notebook state

## New Modules Created

- `project/src/legacy_adapters/legacy_loader.py`
- `project/src/canonical/pipeline_demand.py`
- `project/src/canonical/project_priority.py`
- `project/src/scenarios/demand_qualification.py`
- `project/src/loaders/materialize_wave1.py`

## Schema Compliance

- `fact_pipeline_monthly` rows: `13140`
- duplicate `(project_id, plant, material, month)` keys: `0`
- invalid probabilities: `0`
- unresolved mappings: `612`
- `dim_project_priority` rows: `720`
- priority score bounds: `0.2438` to `0.9635`
- scenario seed rows: `39420`

## Edge Cases

- Legacy pipeline contained unresolved route/material rows; Wave 1 preserves them with explicit reason codes instead of dropping them. Summary: `{'READY': 12528, 'MISSING_PLANT_MATERIAL_MAPPING': 612}`
- Legacy pipeline contained duplicate null-key rows across plate/gasket unresolved records; Wave 1 aggregates them to contract grain and recomputes deterministic quantities.
- Requested date exists for all current projects, so urgency scoring is deterministic for this dataset snapshot dated 2026-04-18.

## Blockers For Wave 2

- Month-to-week translation still depends on a future calendar bridge from sheet `2_4 Model Calendar`.
- Logistics, disruption, and integrated risk layers still require new contracts and synthetic enrichment inputs.
- `mapping_ready_flag` currently captures missing route and material mapping, but Wave 2 may need a more granular routing-exception table.
