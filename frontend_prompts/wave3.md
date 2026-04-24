You are the sole frontend implementation agent for Wave 3 of the Predictive Manufacturing Workflow Engine.

Read first:
- frontend_architecture.md
- design_system.md
- frontend_data_contracts.md
- wave2_frontend_report.md if available
- contracts.md
- assumptions.md

Objective:
Implement the advanced workflow pages that make the dashboard truly differentiating:
quarter memory, maintenance-aware capacity, sourcing/delivery feasibility, and disruption scenarios.

Required pages to implement in this wave:
1) Quarter History / Learning
2) Capacity & Maintenance
3) Sourcing & Delivery
4) Logistics & Disruptions

Page 1 — Quarter History / Learning
Purpose:
Show the “more live” aspect of the product: what happened in Q1 influences Q2 planning.

Required widgets:
- quarter selector
- quarter-over-quarter KPI comparison
- prior decisions summary
- repeated risk summary
- carry-over project/material risk panel
- “what changed from last quarter?” panel
- learning / caution indicators

Required inputs:
- fact_decision_history
- fact_capacity_state_history
- fact_material_decision_history
- fact_quarter_learning_signals
- fact_quarter_service_memory

Page 2 — Capacity & Maintenance
Purpose:
Show effective capacity, not just nominal capacity, including maintenance and downtime.

Required widgets:
- scoped WC heatmap
- bottleneck drilldown
- nominal vs effective capacity comparison
- maintenance/downtime calendar view
- maintenance scenario selector
- bottleneck explanation panel
- before/after maintenance impact summary

Required inputs:
- fact_effective_capacity_weekly_v2
- fact_capacity_bottleneck_summary
- fact_maintenance_downtime_calendar
- fact_maintenance_impact_summary
- dim_maintenance_policy_synth

Page 3 — Sourcing & Delivery
Purpose:
Show material feasibility and delivery feasibility together in an operationally meaningful way.

Required widgets:
- shortage table
- order-by recommendations
- material criticality view
- delivery commitment panel
- service-level violation risk view
- expedite eligibility view
- stock / ATP / in-transit interpretation panel

Required inputs:
- fact_scenario_sourcing_weekly
- fact_delivery_commitment_weekly
- fact_inventory_snapshot
- dim_procurement_logic
- dim_service_level_policy_synth

Page 4 — Logistics & Disruptions
Purpose:
Show landed-cost tradeoffs, transit-time tradeoffs, and disruption-aware scenarios.

Required widgets:
- logistics scenario selector
- shipping cost / transit time summary
- landed cost proxy comparison
- route/lane risk panel
- disruption before/after comparison
- mitigation lever summary
- synthetic enrichment badge/explanation panel

Required inputs:
- fact_scenario_logistics_weekly
- dim_shipping_lane_synth
- dim_country_cost_index_synth
- dim_disruption_scenario_synth
- fact_scenario_resilience_impact

UX requirements:
- advanced pages must still feel simple
- use progressive disclosure: summary first, detail on click
- do not overload the screen with every metric at once
- clearly distinguish capacity problems from material problems from logistics problems

Validation requirements:
- quarter switch updates learning/history widgets coherently
- maintenance scenario switch updates capacity widgets coherently
- disruption scenario switch updates logistics/resilience widgets coherently
- every advanced page has at least one short “what this means” interpretation block

Success condition:
The dashboard now shows the full workflow and all the new product-owner-requested features in a coherent way.