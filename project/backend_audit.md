# Backend Audit

Date: 2026-04-18

This audit evaluates the existing backend before any workflow-first implementation. The intent is reuse-first migration, not rebuild-first replacement.

## Audit Summary

The current backend is a compact pandas-based stack organized around:

1. workbook ingestion and canonicalization in `clarix.data_loader`
2. deterministic planning logic in `clarix.engine`
3. presentation and orchestration in `app.py`, `clarix.charts`, and `clarix.agent`

The codebase already contains reusable facts, dimensions, and demo surfaces. The main weakness is architectural coupling: workflow stages are compressed into a single engine file and page logic, and several required target facts are still missing.

## Structured Inventory

| Name | Type | Purpose | Current inputs | Current outputs | Dependencies | Code quality / maintainability | Fit with target architecture | Action |
|---|---|---|---|---|---|---|---|---|
| `clarix.data_loader` | module | Reads workbook sheets and builds canonical tables with parquet cache | `data/hackathon_dataset.xlsx` sheets | `CanonicalData` tables | pandas, pyarrow, openpyxl | good; clear builders and stable contracts | strong fit for pipeline intake and canonical layer | `KEEP` |
| `CanonicalData` | dataclass | In-memory contract for canonical tables | dataframe builders in `data_loader` | named dataframes | dataclasses, pandas | good but narrow | good base, needs extension for new scenario/risk/action facts | `ADAPT` |
| `clarix.engine` | module | Utilization, bottlenecks, sourcing, explainability, what-if checks | `CanonicalData`, scenario names, basket inputs | dataframes and dict payloads | pandas, numpy, `clarix.data_loader` | medium; useful logic but monolithic and tightly coupled | partial fit; should be decomposed into workflow modules | `ADAPT` |
| `_apply_scenario()` | function | Applies probability scenario to monthly pipeline rows | `fact_pipeline_monthly`, scenario key | `demand_qty`-enriched dataframe | numpy, pandas | simple and usable | good seed for demand qualification, but should become explicit scenario fact logic | `ADAPT` |
| `build_demand_by_wc_week()` | function | Converts monthly pipeline demand into weekly WC demand hours | pipeline fact, cycle times, scenario | WC-week demand dataframe | pandas, scenario helper | medium; logic is understandable | useful, but current even-spread week allocation should be replaced by calendar weighting | `ADAPT` |
| `build_utilization()` | function | Merges WC demand with capacity baseline | capacity fact, weekly demand fact | utilization dataframe | pandas, numpy | good | strong base for `fact_scenario_capacity_weekly` | `ADAPT` |
| `detect_bottlenecks()` | function | Finds WCs above warn/critical thresholds | utilization dataframe | ranked bottleneck dataframe | numpy, pandas | good | useful downstream risk primitive | `ADAPT` |
| `sourcing_recommendations()` | function | BOM explosion plus ATP netting to create buy recommendations | pipeline fact, BOM fact, inventory fact | ranked sourcing dataframe | pandas, numpy | good prototype | useful for material feasibility, but too narrow for full sourcing/risk/action architecture | `ADAPT` |
| `project_feasibility()` | function | Tests basket projects against current capacity load | canonical data, scenario, basket | verdict dict with project and quarter impacts | pandas, numpy | medium; practical demo logic | useful as scenario injection pattern; not a final workflow contract | `ADAPT` |
| `clarix.agent` | module | Chat orchestration over deterministic tools | user message, `CanonicalData` | response text and tool traces | anthropic sdk, pandas | medium; orchestration only | reusable consumer, not core backend | `ADAPT` |
| `clarix.charts` | module | Plotly chart factories | canonical/engine outputs | figures | plotly, pandas | good | reusable demo surface | `KEEP` |
| `app.py` | app entrypoint | Streamlit dashboard and page orchestration | canonical data, engine functions | UI pages | streamlit, pandas, plotly, clarix modules | medium; page file is large and coupled to backend calls | presentation-only; should consume derived facts instead of owning logic | `ADAPT` |
| `scripts/_inspect.py` | script | Quick schema inspection for workbook sheets | workbook path | console schema summary | pandas | simple and useful | good utility | `KEEP` |
| `scripts/generate_dataset.py` | script | Dataset generation helper | generation logic, source rules | workbook or derived dataset assets | pandas and local logic | not fully audited, but likely useful as support tooling | peripheral runtime fit | `KEEP` |
| `notebooks/starter_notebook.ipynb` | notebook | exploratory analysis | manual analyst inputs | notebook artifacts | jupyter stack | low maintainability | poor fit for shared backend implementation | `DEPRECATE` |
| `data/hackathon_dataset.xlsx` | dataset | primary repo-backed source dataset | workbook sheets | source data for all canonical tables | Excel workbook | strong source asset | foundational | `KEEP` |
| `data/.clarix_cache/*.parquet` | cache | cached canonical tables | canonical dataframes | parquet cache files | pyarrow | useful runtime optimization | good for current canonical layer | `KEEP` |

## Existing Reusable Tables

Observed from live load:

| Table | Rows | Reuse assessment | Action |
|---|---:|---|---|
| `fact_pipeline_monthly` | 13,176 | already one of the target gold tables | `KEEP` |
| `fact_wc_capacity_weekly` | 204,048 | already one of the target gold tables | `KEEP` |
| `fact_wc_limits_monthly` | 6,540 | valuable capacity-flex source table | `KEEP` |
| `bridge_material_tool_wc` | 7,625 | strong seed for target bridge, but schema should be enriched | `ADAPT` |
| `fact_inventory_snapshot` | 7,625 | already one of the target gold tables | `KEEP` |
| `fact_finished_to_component` | 9,490 | already one of the target gold tables | `KEEP` |
| `dim_project` | 720 | good source for `dim_project_priority` | `ADAPT` |
| `dim_material_master` | 7,625 | useful enrichment for sourcing and logistics | `KEEP` |

## Required Audit Questions

### Which existing modules already solve part of pipeline loading?

- `clarix.data_loader._build_pipeline()` already loads and normalizes the sales pipeline into `fact_pipeline_monthly`.
- `clarix.data_loader._build_project_dim()` already attaches probability and project metadata that should feed demand qualification and prioritization.

### Which modules already implement transformations, joins, or business rules?

- `clarix.data_loader` implements workbook-to-canonical joins and column normalization.
- `clarix.engine` implements scenario conversion, quantity-to-hours translation, capacity joins, bottleneck logic, BOM explosion, ATP netting, and feasibility logic.

### Are there existing APIs, services, or ETL scripts worth preserving?

- The workbook loader and parquet cache path in `clarix.data_loader` should be preserved.
- `scripts/_inspect.py` is worth preserving as a schema inspection utility.
- `clarix.agent` is worth preserving as an orchestration client on top of the future workflow services.

### Are there existing tables or schemas that can become canonical datasets?

Yes:

- `fact_pipeline_monthly`
- `fact_wc_capacity_weekly`
- `bridge_material_tool_wc`
- `fact_inventory_snapshot`
- `fact_finished_to_component`
- `dim_project`
- `dim_material_master`

### Are there existing dashboards or outputs that can be reused in the demo?

Yes:

- Streamlit pages in `app.py`
- chart factories in `clarix.charts`
- chat planner mode and agent surface in `clarix.agent`

### Which parts are tightly coupled and should be isolated behind adapters instead of rewritten?

- `clarix.engine` should be wrapped behind `src/legacy_adapters/` during migration.
- `app.py` page logic should consume adapters or new workflow services instead of direct engine internals.
- `clarix.agent` tool dispatch should be isolated from changing backend module layouts.

## Integration Fit By Target Architecture

| Target block | Reusable legacy asset | Fit | Note |
|---|---|---|---|
| Sales Pipeline Intake | `clarix.data_loader`, `fact_pipeline_monthly` | strong | keep the loader and table |
| Demand Qualification & Prioritization | `_apply_scenario()`, `dim_project` | partial | add explicit priority dimension and reason codes |
| Translate to Production Demand | `build_demand_by_wc_week()`, `bridge_material_tool_wc` | partial | replace even spread with calendar-weighted allocation |
| Material Feasibility | `sourcing_recommendations()`, inventory and BOM facts | partial | lift into scenario fact and action-ready outputs |
| Capacity Feasibility | `build_utilization()`, `detect_bottlenecks()`, capacity facts | strong | promote to explicit scenario fact |
| Logistics & Landed-Cost Feasibility | `dim_material_master` | weak | mostly missing; needs synthetic enrichment |
| Disruption Scenarios | `_apply_scenario()` naming pattern only | weak | add explicit disruption scenario dimension |
| Bottleneck & Risk Synthesis | bottleneck outputs only | weak | integrated risk layer is missing |
| Planner Action Plan | sourcing outputs and what-if verdicts | weak | ranking/action-score contract missing |

## Key Findings

- The old backend should not be discarded.
- `clarix.data_loader` is the highest-value component and should remain the canonical intake layer.
- The current engine logic is reusable, but it should be migrated behind adapters and decomposed by workflow stage.
- The repo already contains several target gold tables; the main work is completing missing scenario, logistics, risk, and action layers.
- The current monthly-to-week translation is the first place that needs architectural improvement because the workbook already includes a better calendar source.
