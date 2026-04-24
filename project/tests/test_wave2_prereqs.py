from project.src.loaders.materialize_wave2_prereqs import materialize_wave2_prereqs


def test_wave2_prereq_tables_materialize():
    results = materialize_wave2_prereqs()
    required = {
        "fact_pipeline_monthly",
        "dim_project_priority",
        "bridge_material_tool_wc",
        "fact_wc_capacity_weekly",
        "bridge_month_week_calendar",
        "fact_finished_to_component",
        "fact_inventory_snapshot",
        "dim_procurement_logic",
        "dim_country_cost_index_synth",
        "dim_shipping_lane_synth",
        "dim_service_level_policy_synth",
    }
    assert required.issubset(results.keys())
    for name in required:
        assert not results[name].empty, f"{name} should not be empty"
