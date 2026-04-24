from project.src.utils.contract_registry import (
    GOLD_TABLES,
    RECOMMENDED_ACTIONS,
    SCENARIOS,
)


def test_gold_tables_are_registered():
    assert "fact_pipeline_monthly" in GOLD_TABLES
    assert "fact_planner_actions" in GOLD_TABLES
    assert len(GOLD_TABLES) == 12


def test_required_scenarios_are_registered():
    assert "expected_value" in SCENARIOS
    assert "plant_outage" in SCENARIOS
    assert len(SCENARIOS) == 13


def test_action_taxonomy_is_registered():
    assert RECOMMENDED_ACTIONS == [
        "buy",
        "wait",
        "reroute",
        "upshift",
        "reschedule",
        "expedite",
        "escalate",
    ]
