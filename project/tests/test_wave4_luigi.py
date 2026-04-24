import pandas as pd

from project.src.loaders.materialize_wave4_luigi import materialize_wave4_luigi
from project.src.risk.integrated_risk_final import build_fact_integrated_risk, load_wave4_inputs


def test_wave4_fact_has_required_columns():
    inputs = load_wave4_inputs("project/data/processed")
    fact = build_fact_integrated_risk(**inputs)
    required = {
        "scenario",
        "project_id",
        "plant",
        "week",
        "priority_score",
        "capacity_risk_score",
        "sourcing_risk_score",
        "logistics_risk_score",
        "disruption_risk_score",
        "lead_time_risk_score",
        "data_quality_penalty",
        "risk_score",
        "action_score",
        "top_driver",
        "explainability_note",
        "scenario_confidence",
    }
    assert required.issubset(fact.columns)


def test_wave4_fact_has_unique_grain():
    inputs = load_wave4_inputs("project/data/processed")
    fact = build_fact_integrated_risk(**inputs)
    assert not fact.duplicated(["scenario", "project_id", "plant", "week"]).any()


def test_wave4_scores_follow_contract_formula():
    inputs = load_wave4_inputs("project/data/processed")
    fact = build_fact_integrated_risk(**inputs)
    expected_risk = (
        0.30 * fact["capacity_risk_score"]
        + 0.25 * fact["sourcing_risk_score"]
        + 0.20 * fact["logistics_risk_score"]
        + 0.10 * fact["disruption_risk_score"]
        + 0.10 * fact["lead_time_risk_score"]
        + 0.05 * fact["data_quality_penalty"]
    )
    expected_action = fact["priority_score"] * fact["risk_score"] * fact["scenario_confidence"]
    pd.testing.assert_series_equal(fact["risk_score"], expected_risk, check_names=False)
    pd.testing.assert_series_equal(fact["action_score"], expected_action, check_names=False)


def test_wave4_disruption_and_qa_are_visible():
    inputs = load_wave4_inputs("project/data/processed")
    fact = build_fact_integrated_risk(**inputs)
    assert (fact["disruption_risk_score"] > 0).any()
    assert (fact["data_quality_penalty"] > 0).any()


def test_wave4_top_driver_is_traceable():
    inputs = load_wave4_inputs("project/data/processed")
    fact = build_fact_integrated_risk(**inputs)
    allowed = {
        "capacity_risk",
        "sourcing_risk",
        "logistics_risk",
        "disruption_risk",
        "lead_time_risk",
        "data_quality_penalty",
    }
    assert set(fact["top_driver"].unique()).issubset(allowed)


def test_wave4_materializer_writes_output():
    fact = materialize_wave4_luigi()
    assert not fact.empty
    assert "explainability_note" in fact.columns
