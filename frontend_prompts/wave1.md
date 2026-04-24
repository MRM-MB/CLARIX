You are the sole frontend implementation agent for Wave 1 of the Predictive Manufacturing Workflow Engine.

Read first:
- frontend_audit.md
- frontend_migration_plan.md
- frontend_information_architecture.md
- contracts.md
- assumptions.md

Objective:
Define and scaffold the final frontend architecture, design system, state model, and data contracts for a polished dashboard application.

Important:
You should reuse clarix where possible, but move toward a cleaner app architecture.
Do not produce page-level hacks before the shared structure is stable.

Required deliverables:
1) frontend_architecture.md
2) design_system.md
3) frontend_data_contracts.md
4) app shell / routing scaffold
5) reusable layout and shared UI primitives
6) wave1_frontend_report.md

Required app-level structure:
- App shell with top navigation or left sidebar
- Global filters / scenario controls
- Shared state for scope, quarter, scenario, plant/factory, and project filters
- Reusable page header pattern
- Reusable KPI card pattern
- Reusable explanation / assumption panel
- Reusable empty-state / fallback-state components
- Reusable chart container and drilldown panel
- Reusable “why this recommendation?” panel

Required final page architecture:
1) Overview
2) Scope & Region
3) Quarter History / Learning
4) Capacity & Maintenance
5) Sourcing & Delivery
6) Logistics & Disruptions
7) Actions & Recommendations

Required global filters/state:
- region / scope selector
- quarter selector
- scenario selector
- plant/factory selector
- work-center selector
- project priority band filter
- material criticality filter
- show real vs synthetic data toggle or badge system

Required data contracts to support:
- fact_pipeline_monthly
- dim_project_priority
- fact_pipeline_quarterly
- fact_translated_project_demand_weekly
- fact_effective_capacity_weekly_v2
- fact_scenario_sourcing_weekly
- fact_scenario_logistics_weekly
- fact_delivery_commitment_weekly
- fact_integrated_risk_v2
- fact_planner_actions_v2
- quarter memory / decision history tables
- maintenance policy / downtime tables
- disruption scenario tables

Design requirements:
- modern, clean, product-quality dashboard
- visually consistent
- strong hierarchy
- avoid clutter
- emphasize actionability and workflow
- preserve explainability
- support demo under time pressure

Technical requirements:
- define final folder structure for frontend
- define shared hooks/services/data adapters
- define API or file-loading adapters
- define charting/component strategy
- define loading, error, and empty states
- define badge system for synthetic/enriched data

Validation requirements:
- every page must have a clear purpose
- every page must consume stable contracts
- every reusable component must have a reason to exist
- page hierarchy must support the demo flow from pipeline to action

Success condition:
The frontend foundation is stable enough that page implementation can proceed without redesigning the structure later.