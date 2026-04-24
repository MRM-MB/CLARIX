# Backend Audit

Date: 2026-04-18

This audit evaluates the existing backend before any workflow-first extension work. The goal is to maximize reuse of structurally useful code and data contracts, then fill the architectural gaps required for a probabilistic capacity-and-sourcing engine.

## Current Backend Summary

The current backend is a compact pandas-based application with three clear layers:

1. Workbook ingestion and canonicalization in `clarix.data_loader`
2. Deterministic planning logic in `clarix.engine`
3. Presentation and chat orchestration in `app.py`, `clarix.charts`, and `clarix.agent`

It already contains several reusable canonical facts and dimensions:

- `fact_pipeline_monthly`
- `fact_wc_capacity_weekly`
- `bridge_material_tool_wc` as currently implemented
- `fact_inventory_snapshot`
- `fact_finished_to_component`
- `dim_project`
- `dim_material_master`

The current architecture is useful, but still flat. It does not yet express the target workflow as independent, explainable stages:

`pipeline intake -> demand qualification -> production translation -> material/capacity/logistics feasibility -> disruption scenarios -> integrated risk -> planner actions`

## Module Inventory

Format:
`MODULE_NAME | purpose | current status | architectural fit | action={KEEP|ADAPT|DEPRECATE|REPLACE} | rationale`

`app.py | Streamlit UI and orchestration layer over canonical data and engine outputs | working | presentation layer only; not suitable for core backend logic growth | ADAPT | Keep as demo/UI shell, but move new workflow-first backend logic out of the page file`

`clarix.data_loader | Reads workbook sheets and builds canonical pandas tables with parquet cache | working and structurally valuable | strong fit for ingestion/canonical fact layer | KEEP | This is the most reusable backend asset; it already normalizes source data into stable tables`

`clarix.engine | Deterministic capacity, bottleneck, sourcing, and what-if logic on top of canonical tables | working but monolithic | partial fit; good computational core but missing modular workflow stages and explicit scenario/risk/action facts | ADAPT | Preserve the logic, split into stage-specific modules, and promote intermediate fact tables`

`clarix.agent | Chat/tool orchestration over deterministic backend functions | working | useful consumer of backend services, not a core planning layer | ADAPT | Retain as thin orchestration layer after new backend services/facts are introduced`

`clarix.charts | Plotly visualization factories | working | presentation-only | KEEP | Reusable for demo surfaces; does not block backend evolution`

`scripts/_inspect.py | Ad hoc workbook schema inspection helper | working | low architectural significance | KEEP | Useful for source-data inspection and validation`

`scripts/generate_dataset.py | Dataset generation helper for hackathon workbook | not audited deeply for runtime dependency | peripheral to target backend runtime | KEEP | Useful as data-generation support; not part of serving path`

`notebooks/starter_notebook.ipynb | exploratory notebook | exploratory | weak fit for productionized backend | DEPRECATE | Keep for exploration only; do not add workflow logic here`

`data/.clarix_cache/*.parquet | cached canonical tables | working | good runtime optimization for canonical layer | KEEP | Reuse for deterministic source caching`

## Dependency Map

## Runtime dependency graph

```text
data/hackathon_dataset.xlsx
  -> clarix.data_loader.load_canonical()
     -> CanonicalData
        -> fact_pipeline_monthly
        -> fact_wc_capacity_weekly
        -> fact_wc_limits_monthly
        -> bridge_material_tool_wc
        -> fact_inventory_snapshot
        -> fact_finished_to_component
        -> dim_project
        -> dim_material_master

CanonicalData
  -> clarix.engine._apply_scenario()
  -> clarix.engine.build_demand_by_wc_week()
  -> clarix.engine.build_utilization()
  -> clarix.engine.detect_bottlenecks()
  -> clarix.engine.sourcing_recommendations()
  -> clarix.engine.explain_constraint()
  -> clarix.engine.project_feasibility()

clarix.engine outputs
  -> app.py dashboard pages
  -> clarix.agent tool handlers
  -> clarix.charts visualizations
```

## Data-contract dependency notes

- `fact_pipeline_monthly` depends on sheets `1_1 Export Plates`, `1_2 Gaskets`, and `1_3 Export Project list`
- `fact_wc_capacity_weekly` depends on `2_1 Work Center Capacity Weekly`
- `fact_wc_limits_monthly` depends on `2_5 WC Schedule_limits`
- `bridge_material_tool_wc` depends on `2_6 Tool_material nr master`
- `fact_inventory_snapshot` depends on `3_1 Inventory ATP`
- `fact_finished_to_component` depends on `3_2 Component_SF_RM`
- `dim_project` depends on `1_3 Export Project list`
- `dim_material_master` depends on `2_3 SAP MasterData`

## Existing Table Inventory

Observed from live load on 2026-04-18:

| Table | Rows | Status | Notes |
|---|---:|---|---|
| `fact_pipeline_monthly` | 13,176 | Present | Good base for probabilistic demand qualification |
| `fact_wc_capacity_weekly` | 204,048 | Present | Useful baseline capacity fact |
| `fact_wc_limits_monthly` | 6,540 | Present | Good source for upshift/downshift policy logic |
| `bridge_material_tool_wc` | 7,625 | Present | Present but should be enriched/standardized |
| `fact_inventory_snapshot` | 7,625 | Present | Good material feasibility input |
| `fact_finished_to_component` | 9,490 | Present | Good BOM explosion input |
| `dim_project` | 720 | Present | Useful but should be upgraded into prioritization dimension |
| `dim_material_master` | 7,625 | Present | Useful for lead time and cost enrichment |

## Keep / Adapt / Deprecate / Replace Table

| Component | Action | Rationale |
|---|---|---|
| `CanonicalData` dataclass | `ADAPT` | Good contract container, but it needs to grow to include scenario, logistics, risk, and planner-action facts |
| Workbook sheet readers in `load_canonical()` | `KEEP` | They already map the source workbook into stable dataframe contracts |
| `_build_pipeline()` | `ADAPT` | Strong base, but it should explicitly flag unmapped rows and support demand qualification outputs |
| `_build_wc_capacity()` | `KEEP` | Correctly shapes weekly capacity and should remain the source-of-truth capacity baseline |
| `_build_wc_limits()` | `KEEP` | Reusable for capacity flex/upshift logic |
| `_build_tool_master()` | `ADAPT` | Good seed for `bridge_material_tool_wc`, but currently too thin and naming is inconsistent |
| `_build_inventory()` | `KEEP` | Stable base for sourcing feasibility |
| `_build_bom()` | `KEEP` | Stable base for BOM explosion |
| `_build_project_dim()` | `ADAPT` | Should evolve into `dim_project_priority` with explicit priority drivers and reason codes |
| `_build_material_master()` | `KEEP` | Useful source for procurement and cost attributes |
| `_apply_scenario()` | `ADAPT` | Scenario logic should be moved into scenario-specific derived facts with transparent assumptions |
| `build_demand_by_wc_week()` | `ADAPT` | Valuable logic, but week allocation should use the repo calendar instead of equal spreading |
| `build_utilization()` | `ADAPT` | Good capacity-feasibility primitive, but should write reusable fact outputs instead of just ad hoc UI dataframes |
| `detect_bottlenecks()` | `ADAPT` | Keep the concept, but integrate with risk scoring and planner actions |
| `sourcing_recommendations()` | `ADAPT` | Useful first-pass material logic, but too narrow for workflow-first sourcing and action generation |
| `project_feasibility()` | `ADAPT` | Useful prototype logic for scenario injection, but should be reframed as workflow services and scenario facts |
| Streamlit page logic in `app.py` | `ADAPT` | Keep UI, remove backend intelligence from the page file over time |
| Notebook-driven exploration | `DEPRECATE` | Not suitable as a backend delivery mechanism |
| Current monolithic `clarix.engine` file | `REPLACE` at file-structure level, `ADAPT` at logic level | Do not discard the logic; split it into modular backend components while preserving computations that already work |

## Gap Analysis Against Target Architecture

## 1. Pipeline intake

Status: partially implemented

Already present:
- `fact_pipeline_monthly`
- `dim_project`
- source workbook normalization

Gaps:
- no explicit missing-mapping fact or exception table
- no clear separation between raw pipeline intake and qualified pipeline demand
- no assumption registry or synthetic-field labeling

Recommended action:
- keep current pipeline ingestion
- add explicit mapping/quality flags and a pipeline qualification stage

## 2. Demand qualification

Status: partially implemented

Already present:
- probability-based `expected_qty`
- scenario variants: `all_in`, `expected`, `high_confidence`, `monte_carlo`

Gaps:
- no dedicated qualified-demand fact
- no transparent business-priority model from revenue tier, urgency, or customer importance
- no traceable confidence/reason-code outputs

Recommended action:
- derive `dim_project_priority`
- create a scenario-ready qualified-demand fact keyed by project, plant, material, month, and scenario

## 3. Production translation

Status: partially implemented

Already present:
- material-to-tool/work-center bridge
- cycle-time-based conversion from quantity to hours
- weekly utilization rollup

Gaps:
- current week allocation spreads monthly demand evenly across overlapping ISO weeks instead of using `2_4 Model Calendar`
- no explicit `bridge_month_week_calendar`
- no explicit translation fact for finished-good demand to work-center demand with reason codes

Recommended action:
- preserve existing conversion logic
- replace equal-spread allocation with calendar-weighted allocation
- add explicit translation artifacts rather than hiding logic inside `build_demand_by_wc_week()`

## 4. Material feasibility

Status: partially implemented

Already present:
- `fact_finished_to_component`
- `fact_inventory_snapshot`
- BOM explosion and ATP netting in `sourcing_recommendations()`

Gaps:
- no scenario-specific sourcing fact
- no explicit missing-BOM or missing-inventory exception handling
- no synthetic service-level rules by revenue tier
- no landed-cost or supplier-country enrichment

Recommended action:
- keep BOM and inventory bases
- create `fact_scenario_sourcing_weekly`
- add labeled synthetic enrichment tables where repo data is missing

## 5. Capacity feasibility

Status: partially implemented

Already present:
- `fact_wc_capacity_weekly`
- `fact_wc_limits_monthly`
- utilization and bottleneck calculations

Gaps:
- no explicit `fact_scenario_capacity_weekly`
- no actionability layer using schedule-limit levers
- no transparent capacity risk score

Recommended action:
- reuse current utilization logic
- promote outputs into a stable scenario capacity fact
- fold schedule-limit data into upshift/downshift recommendations

## 6. Logistics feasibility

Status: missing

Already present:
- material lead-time and cost hints in `dim_material_master`

Gaps:
- no logistics table
- no shipping lanes, transit time, landed cost, or route reliability
- no disruption sensitivity by route or country

Recommended action:
- introduce synthetic but labeled logistics reference tables
- derive `fact_scenario_logistics_weekly`

## 7. Disruption scenarios

Status: missing

Already present:
- lightweight scenario idea in `_apply_scenario()`

Gaps:
- no disruption scenario catalog
- no plant outage, border delay, lane blockage, war, or fuel spike modeling
- no scenario-to-driver traceability

Recommended action:
- create explicit disruption scenario dimensions and parameter tables
- derive `fact_scenario_capacity_weekly`, `fact_scenario_sourcing_weekly`, and `fact_scenario_logistics_weekly` under named scenarios

## 8. Integrated risk

Status: missing

Already present:
- isolated bottleneck and sourcing outputs

Gaps:
- no unified risk model combining business priority, capacity risk, sourcing risk, logistics risk, and disruption risk
- no explainable reason-code layer

Recommended action:
- add `fact_integrated_risk`
- ensure every score is decomposable into visible drivers

## 9. Planner actions

Status: missing

Already present:
- raw sourcing recommendations
- raw bottleneck visibility
- simple what-if feasibility verdicts

Gaps:
- no ranked action list
- no transparent action score
- no action taxonomy covering buy, wait, reroute, upshift, reschedule, expedite, escalate

Recommended action:
- add `fact_planner_actions`
- produce explicit action scores and top reason codes

## Required Target Outputs: Current Status

| Target output | Current status | Decision |
|---|---|---|
| `fact_pipeline_monthly` | exists | KEEP |
| `dim_project_priority` | missing; closest source is `dim_project` | ADAPT from `dim_project` |
| `bridge_material_tool_wc` | partially exists with thin schema | ADAPT |
| `fact_wc_capacity_weekly` | exists | KEEP |
| `bridge_month_week_calendar` | missing though source calendar sheet exists in workbook | ADD |
| `fact_finished_to_component` | exists | KEEP |
| `fact_inventory_snapshot` | exists | KEEP |
| `fact_scenario_capacity_weekly` | missing | ADD |
| `fact_scenario_sourcing_weekly` | missing | ADD |
| `fact_scenario_logistics_weekly` | missing | ADD |
| `fact_integrated_risk` | missing | ADD |
| `fact_planner_actions` | missing | ADD |

## Assumptions Logged During Audit

Format:
`ASSUMPTION_ID | description | rationale | impact | synthetic=true/false`

`A001 | The current backend code in clarix/ is the primary backend to evolve, despite the Streamlit UI wrapper | It contains the only reusable deterministic planning and canonical-data logic in the repo | High; it determines where refactoring should begin | synthetic=false`

`A002 | Sheet 2_4 Model Calendar is available in the workbook even though it is not currently loaded by data_loader | The repo data dictionary documents it clearly as a normalized source sheet | High; it should become the basis for month-to-week allocation and a new bridge table | synthetic=false`

`A003 | The target workflow-first engine should be implemented incrementally on top of current pandas contracts rather than replaced wholesale with a new framework | Existing pandas tables and engine functions already provide working base behavior and demo value | High; this drives a reuse-first migration strategy | synthetic=false`

## Recommended Refactor Direction

Implement the next backend iteration as an evolution of the current codebase:

- Keep `clarix.data_loader` as the canonical ingestion entry point
- Split `clarix.engine` into workflow-oriented modules such as:
  - `clarix/workflows/demand.py`
  - `clarix/workflows/production.py`
  - `clarix/workflows/capacity.py`
  - `clarix/workflows/sourcing.py`
  - `clarix/workflows/logistics.py`
  - `clarix/workflows/risk.py`
  - `clarix/workflows/actions.py`
- Extend `CanonicalData` into a broader contract or introduce a second derived-facts container
- Materialize reusable derived facts instead of recomputing everything inline for the UI
- Preserve the current dashboard and agent as consumers of the new backend facts

## Suggested Next Implementation Slice

The lowest-risk next slice is:

1. Load sheet `2_4 Model Calendar`
2. Add `bridge_month_week_calendar`
3. Upgrade monthly-to-week allocation to use calendar weights
4. Derive `dim_project_priority`
5. Materialize `fact_scenario_capacity_weekly`

This sequence preserves existing behavior where possible, improves explainability immediately, and establishes the first workflow-first derived facts without breaking the demo app.
