# Legacy Map

This file is the integration map between the old backend and the new workflow architecture.

## Legacy To Workflow Mapping

| Legacy asset | Current role | New workflow role | Adapter strategy | Notes |
|---|---|---|---|---|
| `clarix.data_loader.load_canonical()` | canonical workbook ingestion | Sales Pipeline Intake foundation | wrap in `src/legacy_adapters/legacy_loader.py` | keep as default loader until native loaders fully replace adapters |
| `CanonicalData.fact_pipeline_monthly` | pipeline fact | `fact_pipeline_monthly` | direct reuse with contract aliasing | rename `qty` to `raw_qty` at contract boundary |
| `CanonicalData.dim_project` | project dimension | `dim_project_priority` seed | adapter plus new scoring layer | do not replace until scoring contract exists |
| `CanonicalData.bridge_material_tool_wc` | routing bridge | `bridge_material_tool_wc` | direct reuse plus enrichment | add `work_center_full`, `routing_source`, reason codes |
| `CanonicalData.fact_wc_capacity_weekly` | capacity fact | `fact_wc_capacity_weekly` and `fact_scenario_capacity_weekly` input | direct reuse | preserve as baseline source-of-truth |
| `CanonicalData.fact_wc_limits_monthly` | schedule limits | capacity flex driver | reuse in capacity module | useful for upshift/downshift action logic |
| `CanonicalData.fact_inventory_snapshot` | inventory fact | `fact_inventory_snapshot` and sourcing input | direct reuse | preserve snapshot semantics |
| `CanonicalData.fact_finished_to_component` | BOM fact | `fact_finished_to_component` and sourcing input | direct reuse | preserve plant-specific BOM behavior |
| `CanonicalData.dim_material_master` | material master | sourcing and logistics enrichment source | direct reuse | complement with synthetic logistics dims |
| `clarix.engine._apply_scenario()` | scenario transform | demand qualification seed | migrate into scenario module | rename `expected` to `expected_value` at new contract boundary |
| `clarix.engine.build_demand_by_wc_week()` | production translation | Translate to Production Demand | adapt and replace week spread logic | calendar bridge required |
| `clarix.engine.build_utilization()` | capacity feasibility | `fact_scenario_capacity_weekly` builder | adapt | keep utilization math visible |
| `clarix.engine.detect_bottlenecks()` | bottleneck detection | risk and actions driver | adapt | should not remain a terminal output only |
| `clarix.engine.sourcing_recommendations()` | sourcing recommendation prototype | `fact_scenario_sourcing_weekly` seed and action source | adapt | split sourcing fact from action output |
| `clarix.engine.project_feasibility()` | what-if scoring prototype | planner action simulation helper | isolate | useful for scenario simulation patterns |
| `clarix.charts` | demo visualization | app consumer | retain | no contract changes required |
| `clarix.agent` | conversational surface | app consumer and orchestration adapter | isolate | keep tools thin over stable contracts |
| `app.py` | Streamlit UI | app consumer | isolate | migrate page data dependencies gradually |

## Keep Immediately

- `clarix.data_loader`
- current canonical facts already matching target gold tables
- charting layer and Streamlit demo surfaces
- practical math in capacity and sourcing logic

## Isolate Behind Adapters

- scenario naming differences between legacy and target contracts
- monolithic `clarix.engine`
- direct page-to-engine coupling in `app.py`
- direct agent-to-engine coupling in `clarix.agent`

## Replace Later

- equal month-to-week spreading in `build_demand_by_wc_week()`
- UI-shaped outputs as de facto backend contracts
- implicit logic buried in page code instead of materialized facts
