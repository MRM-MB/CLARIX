You are Carolina's implementation agent for Wave 2.

Read first:
- contracts.md
- assumptions.md
- wave1_carolina_report.md
- wave1_luigi_report.md

Use as inputs:
- fact_translated_project_demand_weekly
- fact_finished_to_component
- fact_inventory_snapshot
- dim_procurement_logic
- dim_country_cost_index_synth
- dim_shipping_lane_synth
- dim_service_level_policy_synth

Objective for Wave 2:
Build the Sourcing & Logistics Feasibility Engine.

Required outputs:
1) fact_scenario_sourcing_weekly
2) fact_scenario_logistics_weekly
3) sourcing_logistics_report.md

Required columns for fact_scenario_sourcing_weekly:
- scenario
- plant
- component_material
- week
- component_demand_qty
- available_qty
- shortage_qty
- coverage_days_or_weeks
- recommended_order_date
- shortage_flag
- sourcing_risk_score

Required columns for fact_scenario_logistics_weekly:
- scenario
- project_id
- plant
- destination_country
- week
- transit_time_days
- shipping_cost
- landed_cost_proxy
- on_time_feasible_flag
- expedite_option_flag
- logistics_risk_score
- synthetic_dependency_flag

Tasks:
1) explode translated finished demand through the BOM
2) compute weekly component demand
3) compare demand vs on-hand / ATP / in-transit with explicit timing assumptions
4) compute shortage and order-by logic
5) build logistics feasibility using synthetic lanes and country-cost indices
6) compute landed_cost_proxy using shipping + labor/energy/overhead proxies
7) compute on_time_feasible_flag using requested delivery timing and service-level policies
8) expose expedited_shipping as an explicit option, not a hidden assumption

Validation requirements:
- sourcing outputs unique at declared grain
- logistics outputs unique at declared grain
- all synthetic contributions labeled
- shortage logic and on-time logic documented explicitly

Deliverables:
- Python modules
- processed outputs
- tests
- sourcing_logistics_report.md