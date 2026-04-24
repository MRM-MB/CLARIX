import pandas as pd

from project.src.loaders.materialize_wave3_luigi import materialize_wave3_luigi
from project.src.risk.integrated_risk_base import build_fact_integrated_risk_base, load_wave3_inputs


def test_wave3_fact_has_unique_grain():
    inputs = load_wave3_inputs("project/data/processed")
    fact = build_fact_integrated_risk_base(**inputs)
    assert not fact.duplicated(["scenario", "project_id", "plant", "week"]).any()


def test_wave3_placeholders_are_explicit_zero():
    inputs = load_wave3_inputs("project/data/processed")
    fact = build_fact_integrated_risk_base(**inputs)
    assert (fact["disruption_risk_score_placeholder"] == 0).all()
    assert (fact["data_quality_penalty_placeholder"] == 0).all()


def test_wave3_action_score_is_deterministic_formula():
    inputs = load_wave3_inputs("project/data/processed")
    fact = build_fact_integrated_risk_base(**inputs)
    expected = fact["priority_score"] * fact["risk_score_base"] * fact["scenario_confidence"]
    pd.testing.assert_series_equal(
        fact["action_score_base"],
        expected,
        check_names=False,
    )


def test_wave3_top_driver_is_traceable():
    inputs = load_wave3_inputs("project/data/processed")
    fact = build_fact_integrated_risk_base(**inputs)
    allowed = {"capacity_risk", "sourcing_risk", "logistics_risk", "lead_time_risk"}
    assert set(fact["top_driver"].unique()).issubset(allowed)


def test_wave3_materializer_writes_output():
    fact = materialize_wave3_luigi()
    assert not fact.empty
    assert "explainability_note" in fact.columns
