"""Shared constants for contract validation and test scaffolding."""

GOLD_TABLES = [
    "fact_pipeline_monthly",
    "dim_project_priority",
    "bridge_material_tool_wc",
    "fact_wc_capacity_weekly",
    "bridge_month_week_calendar",
    "fact_finished_to_component",
    "fact_inventory_snapshot",
    "fact_scenario_capacity_weekly",
    "fact_scenario_sourcing_weekly",
    "fact_scenario_logistics_weekly",
    "fact_integrated_risk",
    "fact_planner_actions",
]

SCENARIOS = [
    "all_in",
    "expected_value",
    "high_confidence",
    "monte_carlo_light",
    "baseline_logistics",
    "expedited_shipping",
    "fuel_price_spike",
    "border_delay",
    "lane_blockage",
    "war_disruption",
    "plant_outage",
    "energy_shock",
    "conflict_disruption",
]

RECOMMENDED_ACTIONS = [
    "buy",
    "wait",
    "reroute",
    "upshift",
    "reschedule",
    "expedite",
    "escalate",
]
