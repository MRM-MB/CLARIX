# Migration Plan

Date: 2026-04-18

This plan maps legacy backend components into the target workflow-first architecture and identifies the first implementation slices for parallel agents.

## Migration Strategy

Principles:

- preserve working canonical loaders and facts
- isolate legacy logic behind adapters before deep refactors
- materialize reusable derived facts rather than recomputing UI-specific tables
- make assumptions, synthetic fields, and scenario logic explicit

## Target Architecture Mapping

| Target block | Required functionality | Reusable legacy modules | Missing functionality | New modules to build | Integration notes | Blockers / risks |
|---|---|---|---|---|---|---|
| 1. Sales Pipeline Intake | ingest workbook pipeline, normalize fields, flag mapping issues | `clarix.data_loader`, `_build_pipeline()`, `fact_pipeline_monthly` | explicit quality flags and exception outputs | `src/loaders/pipeline_loader.py`, `src/canonical/pipeline_quality.py` | wrap legacy loader first, then extend schema | unresolved source mappings must be flagged, not dropped |
| 2. Demand Qualification & Prioritization | expected demand, expected value, priority scores, reason codes | `dim_project`, `_apply_scenario()` | no `dim_project_priority`, no scoring contract implementation, no urgency logic | `src/scenarios/demand_qualification.py`, `src/canonical/project_priority.py` | start from `dim_project` and `fact_pipeline_monthly` | urgency drivers may require explicit assumptions |
| 3. Translate to Production Demand | allocate monthly demand into weekly plant/WC demand using routing and calendar | `build_demand_by_wc_week()`, `bridge_material_tool_wc` | no calendar bridge, equal-spread allocation is too coarse | `src/canonical/calendar_bridge.py`, `src/capacity/production_translation.py` | adapt legacy logic, but replace week allocation | source `2_4 Model Calendar` is not yet loaded |
| 4. Material Feasibility | BOM explosion, inventory netting, sourcing risk | `sourcing_recommendations()`, `fact_finished_to_component`, `fact_inventory_snapshot` | no scenario sourcing fact, no reason codes for missing BOM/inventory | `src/sourcing/scenario_sourcing.py` | retain legacy BOM and ATP logic as baseline adapter | incomplete inventory/BOM coverage needs explicit exceptions |
| 5. Capacity Feasibility | weekly utilization, headroom, bottlenecks, flex limits | `build_utilization()`, `detect_bottlenecks()`, `fact_wc_capacity_weekly`, `fact_wc_limits_monthly` | no `fact_scenario_capacity_weekly`, no risk score columns | `src/capacity/scenario_capacity.py` | keep formulas, move output into stable fact | current outputs are UI-shaped, not contract-shaped |
| 6. Logistics & Landed-Cost Feasibility | lane cost, transit, landed cost, route reliability | `dim_material_master` only | almost entirely missing | `src/logistics/lane_enrichment.py`, `src/logistics/scenario_logistics.py` | use labeled synthetic dims initially | no real lane table in repo; synthetic policy required |
| 7. Disruption Scenarios | named disruption families and parameterization | scenario naming pattern only | no disruption scenario dims or rule engine | `src/disruption/scenario_catalog.py`, `src/disruption/scenario_impacts.py` | build explicit scenario catalog first | synthetic scenario assumptions must be transparent |
| 8. Bottleneck & Risk Synthesis | combine business and operational drivers into explainable risk | bottleneck outputs, sourcing outputs | no integrated risk fact or scoring breakdowns | `src/risk/integrated_risk.py` | consume priority, sourcing, capacity, logistics, disruption facts | dependency on upstream facts |
| 9. Planner Action Plan | ranked actions with action score and reason codes | sourcing recommendations, project feasibility outputs | no action taxonomy, no action score, no combined recommendation layer | `src/actions/planner_actions.py` | keep legacy recommendation logic as one action source | action ranking depends on completed priority/risk contracts |

## Legacy To New Module Mapping

| Legacy component | New home | Migration mode |
|---|---|---|
| `clarix.data_loader.load_canonical()` | `src/legacy_adapters/legacy_loader.py` then `src/loaders/` | adapter first |
| `CanonicalData` | `src/utils/contract_registry.py` plus future canonical containers | adapt |
| `clarix.engine._apply_scenario()` | `src/scenarios/demand_qualification.py` | adapt |
| `clarix.engine.build_demand_by_wc_week()` | `src/capacity/production_translation.py` | adapt and improve |
| `clarix.engine.build_utilization()` | `src/capacity/scenario_capacity.py` | adapt |
| `clarix.engine.detect_bottlenecks()` | `src/risk/integrated_risk.py` and `src/actions/planner_actions.py` | adapt |
| `clarix.engine.sourcing_recommendations()` | `src/sourcing/scenario_sourcing.py` | adapt |
| `clarix.engine.project_feasibility()` | `src/actions/planner_actions.py` and scenario analysis services | adapt |
| `clarix.agent` | `src/app/` with adapter boundary | isolate |
| `app.py` | `src/app/` consumers and legacy UI integration | isolate |

## Recommended Migration Phases

### Phase 0: Contract and scaffold

- create `project/` source-of-truth docs
- create package and test scaffold
- freeze naming conventions and merge rules

### Phase 1: Canonical extension

- load sheet `2_4 Model Calendar`
- add `bridge_month_week_calendar`
- create `dim_project_priority`
- enrich `bridge_material_tool_wc`

### Phase 2: Scenario facts

- materialize `fact_scenario_capacity_weekly`
- materialize `fact_scenario_sourcing_weekly`
- add initial logistics synthetic dimensions and `fact_scenario_logistics_weekly`

### Phase 3: Risk and actions

- derive `fact_integrated_risk`
- derive `fact_planner_actions`
- connect actions back to reason codes and visible drivers

### Phase 4: Consumer migration

- refit Streamlit pages to consume stable derived facts
- refit chat tools to use adapters over the new modules

## Recommended First Parallel Workstreams

1. Calendar and capacity translation
2. Project priority dimension and scoring
3. Sourcing scenario fact
4. Logistics synthetic dimensions
5. Risk and action contract implementation

Each workstream should preserve compatibility with legacy adapters and update `assumptions.md` when adding heuristics.
