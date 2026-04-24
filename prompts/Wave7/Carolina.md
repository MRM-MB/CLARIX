You are Carolina's implementation agent for Wave 7.

Read first:
- contracts.md
- assumptions.md
- planner_actions_v2_report.md
- wave6_carolina_report.md
- demo_readiness_checklist.md if available

Use as inputs:
- dim_region_scope
- fact_pipeline_quarterly
- fact_effective_capacity_weekly_v2
- fact_delivery_commitment_weekly
- fact_integrated_risk_v2
- fact_planner_actions_v2

Objective for Wave 7:
Refresh the demo layer so the product owners can clearly see:
1) single-region focus,
2) quarter-over-quarter learning,
3) maintenance/downtime-aware planning,
4) stronger decision workflow.

Required outputs:
1) refreshed demo app or demo notebook flow
2) deterministic_demo_script_v2.md
3) screenshot_ready_views_v2
4) demo_readiness_checklist_v2.md

Required pages/sections:
- Scope & Region View
- Quarter History / Learning View
- Capacity with Maintenance View
- Sourcing & Delivery View
- Final Actions View

Required widgets/views:
- region selector (with one default active region)
- quarter selector (Q1 / Q2 / carry-over)
- maintenance scenario selector
- scoped capacity heatmap
- quarter memory summary
- delivery feasibility panel
- planner actions v2 table
- “what changed from last quarter?” panel
- “why this recommendation?” panel

Tasks:
1) refresh the demo flow to emphasize the new product-owner requirements
2) clearly label real vs synthetic data
3) make quarter history understandable
4) make maintenance/downtime scenarios visible and intuitive
5) ensure the demo tells a workflow story, not just a dashboard story

Validation requirements:
- no broken screens
- quarter switch updates downstream views coherently
- maintenance scenario switch updates capacity views coherently
- demo path still runnable in under 3 minutes

Deliverables:
- app/notebook code
- deterministic_demo_script_v2.md
- demo_readiness_checklist_v2.md
- screenshot-ready outputs