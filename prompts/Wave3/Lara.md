You are Lara's implementation agent for Wave 3.

Read first:
- contracts.md
- assumptions.md
- capacity_engine_report.md
- sourcing_logistics_report.md

Use as inputs:
- fact_scenario_capacity_weekly
- fact_scenario_sourcing_weekly
- fact_scenario_logistics_weekly
- dim_shipping_lane_synth
- dim_country_cost_index_synth

Objective for Wave 3:
Build the Disruption & Resilience Scenario Engine.

Required outputs:
1) dim_disruption_scenario_synth
2) fact_scenario_resilience_impact
3) disruption_engine_report.md

Required disruption families:
- war_disruption
- lane_blockage
- border_delay
- plant_outage
- labor_shortage
- energy_shock
- fuel_price_spike
- maintenance_overrun

Required columns for dim_disruption_scenario_synth:
- scenario_name
- affected_region_or_lane
- affected_plants
- affected_materials
- transit_multiplier
- shipping_cost_multiplier
- available_capacity_multiplier
- lead_time_multiplier
- reliability_penalty
- synthetic_generation_rule

Required columns for fact_scenario_resilience_impact:
- scenario
- project_id_if_available
- plant
- week
- affected_branch
- delta_capacity_risk
- delta_sourcing_risk
- delta_logistics_risk
- disruption_risk_score
- mitigation_candidate
- explanation_note

Tasks:
1) define explainable disruption scenarios with explicit multipliers
2) apply scenario effects to capacity, sourcing, and logistics outputs
3) compute before/after impacts
4) compute disruption_risk_score
5) suggest mitigation candidates such as reroute, expedite, upshift, or reschedule
6) keep all disruption logic fully explicit and synthetic-labeled

Validation requirements:
- every disruption scenario states clearly what changed
- before/after comparisons are inspectable
- mitigation suggestions remain explainable
- no hidden logic

Deliverables:
- Python modules
- synthetic tables
- processed outputs
- tests
- disruption_engine_report.md