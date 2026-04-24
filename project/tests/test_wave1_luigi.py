import pandas as pd

from project.src.canonical.pipeline_demand import build_fact_pipeline_monthly
from project.src.canonical.project_priority import build_dim_project_priority
from project.src.legacy_adapters.legacy_loader import load_legacy_canonical
from project.src.scenarios.demand_qualification import build_scenario_project_demand_seed


def test_fact_pipeline_monthly_has_unique_contract_grain():
    fact = build_fact_pipeline_monthly()
    assert not fact.duplicated(["project_id", "plant", "material", "month"]).any()


def test_fact_pipeline_monthly_computes_expected_values_deterministically():
    fact = build_fact_pipeline_monthly()
    pd.testing.assert_series_equal(
        fact["expected_qty"],
        fact["raw_qty"] * fact["probability"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        fact["expected_value"],
        fact["project_value"] * fact["probability"],
        check_names=False,
    )


def test_fact_pipeline_monthly_probabilities_are_bounded():
    fact = build_fact_pipeline_monthly()
    assert fact["probability"].between(0.0, 1.0).all()


def test_dim_project_priority_is_bounded_and_versioned():
    legacy = load_legacy_canonical()
    dim_project_priority = build_dim_project_priority(legacy.dim_project)
    assert dim_project_priority["priority_score"].between(0.0, 1.0).all()
    assert dim_project_priority["score_version"].nunique() == 1


def test_scenario_seed_contains_required_scenarios():
    fact = build_fact_pipeline_monthly()
    seed = build_scenario_project_demand_seed(fact)
    assert set(seed["scenario_name"].unique()) == {"all_in", "expected_value", "high_confidence"}

    expected = seed[seed["scenario_name"] == "expected_value"].reset_index(drop=True)
    pd.testing.assert_series_equal(
        expected["scenario_qty"],
        expected["raw_qty"] * expected["probability"],
        check_names=False,
    )
