You are the sole frontend implementation agent for Wave 2 of the Predictive Manufacturing Workflow Engine.

Read first:
- frontend_architecture.md
- design_system.md
- frontend_data_contracts.md
- wave1_frontend_report.md
- contracts.md
- assumptions.md

Objective:
Implement the core pages of the dashboard and wire them to the backend outputs so the main pipeline-to-action story works end to end.

Required pages to implement in this wave:
1) Overview
2) Scope & Region
3) Actions & Recommendations

These pages must already be demo-usable by the end of the wave.

Page 1 — Overview
Purpose:
Give a high-level, immediately understandable summary of the current scoped situation.

Required widgets:
- hero KPI strip
- pipeline summary cards
- expected demand / expected value cards
- top bottleneck summary
- top shortage summary
- top recommendation summary
- scenario summary
- quick explanation block: “How the engine works”

Required inputs:
- fact_pipeline_quarterly or fact_pipeline_monthly
- dim_project_priority
- fact_integrated_risk_v2 or latest available integrated risk
- fact_planner_actions_v2 or latest available planner actions

Page 2 — Scope & Region
Purpose:
Show that the MVP is intentionally focused on one region / few factories and allow controlled scoping.

Required widgets:
- region selector
- plant/factory inclusion summary
- scoped project distribution
- scoped demand distribution
- scope rationale panel
- data coverage panel
- selected-factory overview

Required inputs:
- dim_region_scope
- fact_pipeline_quarterly
- scoped capacity / sourcing summaries if available

Page 3 — Actions & Recommendations
Purpose:
Show the final value of the system in a product-owner-friendly way.

Required widgets:
- ranked planner action table
- top action cards
- action filters
- “why this recommendation?” drilldown panel
- expected effect panel
- confidence / risk breakdown panel
- compare baseline vs mitigated outcome if available

Required inputs:
- fact_planner_actions_v2 or fact_planner_actions
- fact_integrated_risk_v2 or fact_integrated_risk
- dim_action_policy if available

Integration requirements:
- implement data adapters for the current backend outputs
- support missing-table fallbacks gracefully
- do not crash if some v2 tables are missing; degrade gracefully to v1
- clearly label any synthetic fields or scenario enrichments

UX requirements:
- every page must be readable by product owners
- no raw table dumps without structure
- every complex section should have a short interpretation sentence
- filters should feel unified across pages

Validation requirements:
- changing global filters updates page content coherently
- top navigation works
- no broken charts
- no empty screens without fallback states
- top actions and top risks are visible in under 10 seconds

Success condition:
The user can already understand the product and see the overall business value from the dashboard.