ºYou are Carolina's implementation agent for Wave 1.

Read first:
- backend_audit.md
- migration_plan.md
- contracts.md
- assumptions.md
- synthetic_data_policy.md

Objective for Wave 1:
Build the Material, Procurement, and Synthetic Logistics Foundations, while reusing any useful legacy backend modules already identified in the audit.

Important:
Do NOT rebuild existing working logic for BOM parsing, inventory handling, procurement fields, or helper utilities if they already exist and are reusable.
Use adapters where needed.

Your scope in this wave:
1) build BOM and inventory foundations
2) build procurement / lead-time foundation
3) build synthetic logistics and service-level dimensions needed later

Primary real inputs:
- 3_2 Component_SF_RM
- 3_1 Inventory ATP
- 2_3 SAP MasterData

Required synthetic outputs:
- dim_country_cost_index_synth
- dim_shipping_lane_synth
- dim_service_level_policy_synth

Required real outputs:
1) fact_finished_to_component
2) fact_inventory_snapshot
3) dim_procurement_logic
4) dim_country_cost_index_synth
5) dim_shipping_lane_synth
6) dim_service_level_policy_synth
7) wave1_carolina_report.md

Required columns for fact_finished_to_component:
- plant
- header_material
- component_material
- effective_component_qty
- scrap_factor

Required columns for fact_inventory_snapshot:
- plant
- material
- stock_qty
- atp_qty
- in_transit_qty
- safety_stock_qty
- inventory_snapshot_date

Required columns for dim_procurement_logic:
- plant
- material
- procurement_type
- lead_time_days_or_weeks
- order_policy_note
- reason_code

Required columns for dim_country_cost_index_synth:
- country_code
- labor_cost_index_synth
- energy_cost_index_synth
- overhead_cost_index_synth
- risk_cost_index_synth
- synthetic_generation_rule

Required columns for dim_shipping_lane_synth:
- origin_country
- destination_country
- transit_time_days_synth
- base_shipping_cost_synth
- expedited_shipping_cost_synth
- route_reliability_score_synth
- disruption_sensitivity_score_synth
- synthetic_generation_rule

Required columns for dim_service_level_policy_synth:
- revenue_tier
- max_allowed_late_days
- expedite_allowed_flag
- reroute_allowed_flag
- premium_shipping_allowed_flag
- service_penalty_weight
- synthetic_generation_rule

Tasks:
1) inspect the backend audit and identify reusable legacy modules for BOM parsing, inventory parsing, procurement logic, or utility functions
2) document which legacy modules are reused, adapted, or ignored
3) normalize BOM from 3_2
4) normalize inventory snapshot from 3_1
5) normalize procurement and lead-time fields from 2_3
6) create reproducible synthetic country cost indices
7) create reproducible synthetic shipping lanes and transit times
8) create service-level policy table by revenue tier
9) label all synthetic fields explicitly
10) document every synthetic generation rule

Validation requirements:
- no duplicate (plant, header_material, component_material)
- inventory unique by (plant, material)
- missing lead times surfaced explicitly
- every synthetic table includes generation rules
- wave1_carolina_report.md must include KEEP / ADAPT / DEPRECATE / REPLACE decisions for any touched legacy modules

Deliverables:
- Python modules
- processed and synthetic tables
- tests
- wave1_carolina_report.md summarizing:
  - reused legacy components
  - synthetic-data logic
  - schema compliance
  - blockers for Wave 2

Done when:
Wave 2 can consume stable BOM, inventory, procurement, and logistics-dimension outputs without reading raw or ad hoc synthetic logic.