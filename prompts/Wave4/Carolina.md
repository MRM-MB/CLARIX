You are Carolina's implementation agent for Wave 4.

Read first:
- contracts.md
- assumptions.md
- integrated_risk_final_report.md
- planner_actions_report.md
- qa_guardrails_report.md

Use as inputs:
- fact_pipeline_monthly
- dim_project_priority
- fact_translated_project_demand_weekly
- fact_scenario_capacity_weekly
- fact_scenario_sourcing_weekly
- fact_scenario_logistics_weekly
- fact_integrated_risk
- fact_planner_actions

Objective for Wave 4:
Build the demo layer and final validation materials for the hackathon walkthrough.

Required outputs:
1) demo app or demo notebook flow
2) demo_readiness_checklist.md
3) deterministic_demo_script.md
4) screenshot_ready_views

Required pages or sections:
- Overview
- Capacity
- Sourcing
- Logistics & Disruptions
- Actions

Required widgets/views:
- scenario selector
- project priority table
- translated demand summary
- work-center overload heatmap
- material shortage table
- logistics feasibility table
- disruption scenario comparison
- planner action table
- “why this recommendation?” explanation panel

Tasks:
1) build a deterministic demo path from pipeline to action
2) clearly label real vs synthetic inputs
3) include fallback messages for weak or missing sections
4) ensure the story is understandable by product owners
5) produce a demo_readiness_checklist.md and deterministic_demo_script.md

Validation requirements:
- no broken screens
- every chart backed by a stable table
- scenario changes update downstream views coherently
- demo path runnable in under 3 minutes

Deliverables:
- app or notebook code
- markdown scripts/checklists
- screenshot-ready outputs