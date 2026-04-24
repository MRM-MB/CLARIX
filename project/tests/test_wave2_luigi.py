import pandas as pd

from project.src.loaders.materialize_wave2_luigi import materialize_wave2_luigi
from project.src.scenarios.weekly_translation import build_fact_translated_project_demand_weekly, load_wave2_inputs


def test_wave2_fact_has_no_duplicate_business_keys():
    inputs = load_wave2_inputs("project/data/processed")
    fact = build_fact_translated_project_demand_weekly(**inputs)
    assert not fact.duplicated(["scenario", "project_id", "plant", "material", "week"]).any()


def test_wave2_fact_contains_required_scenarios():
    inputs = load_wave2_inputs("project/data/processed")
    fact = build_fact_translated_project_demand_weekly(**inputs)
    assert set(fact["scenario"].unique()) == {
        "all_in",
        "expected_value",
        "high_confidence",
        "monte_carlo_light",
    }


def test_wave2_monte_carlo_is_seeded_and_deterministic():
    inputs = load_wave2_inputs("project/data/processed")
    fact_a = build_fact_translated_project_demand_weekly(**inputs)
    fact_b = build_fact_translated_project_demand_weekly(**inputs)
    mc_a = fact_a[fact_a["scenario"] == "monte_carlo_light"].reset_index(drop=True)
    mc_b = fact_b[fact_b["scenario"] == "monte_carlo_light"].reset_index(drop=True)
    pd.testing.assert_frame_equal(mc_a, mc_b)


def test_wave2_fact_preserves_unmapped_rows():
    inputs = load_wave2_inputs("project/data/processed")
    fact = build_fact_translated_project_demand_weekly(**inputs)
    assert (fact["mapping_status"] == "UNMAPPED").any()


def test_wave2_materializer_writes_output():
    fact = materialize_wave2_luigi()
    assert not fact.empty
    assert "scenario_confidence" in fact.columns
