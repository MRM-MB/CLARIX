import pandas as pd

from project.src.loaders.materialize_wave7_luigi import materialize_wave7_luigi
from project.src.risk.integrated_risk_v2 import build_fact_integrated_risk_v2, load_wave7_inputs


def test_wave7_fact_has_required_columns():
    inputs = load_wave7_inputs("project/data/processed")
    fact = build_fact_integrated_risk_v2(**inputs)
    required = {
        "scope_id",
        "scenario",
        "quarter_id",
        "project_id",
        "plant",
        "week",
        "priority_score",
        "capacity_risk_score",
        "sourcing_risk_score",
        "logistics_risk_score",
        "disruption_risk_score",
        "delivery_risk_score",
        "maintenance_risk_score",
        "quarter_learning_penalty_or_boost",
        "risk_score_v2",
        "action_score_v2",
        "top_driver",
        "explainability_note",
    }
    assert required.issubset(fact.columns)


def test_wave7_fact_has_unique_grain():
    inputs = load_wave7_inputs("project/data/processed")
    fact = build_fact_integrated_risk_v2(**inputs)
    assert not fact.duplicated(["scope_id", "scenario", "quarter_id", "project_id", "plant", "week"]).any()


def test_wave7_new_components_are_explicit_and_visible():
    inputs = load_wave7_inputs("project/data/processed")
    fact = build_fact_integrated_risk_v2(**inputs)
    assert (fact["delivery_risk_score"] > 0).any()
    assert (fact["maintenance_risk_score"] > 0).any()
    assert (fact["quarter_learning_penalty_or_boost"] != 0).any()


def test_wave7_v2_remains_comparable_with_v1():
    inputs = load_wave7_inputs("project/data/processed")
    fact = build_fact_integrated_risk_v2(**inputs)
    merged = fact.merge(
        inputs["fact_integrated_risk"][["scenario", "project_id", "plant", "week", "risk_score"]],
        on=["scenario", "project_id", "plant", "week"],
        how="left",
    )
    mean_abs_diff = (merged["risk_score_v2"] - merged["risk_score"]).abs().mean()
    assert mean_abs_diff < 0.1


def test_wave7_top_driver_is_traceable():
    inputs = load_wave7_inputs("project/data/processed")
    fact = build_fact_integrated_risk_v2(**inputs)
    allowed = {
        "capacity_risk",
        "sourcing_risk",
        "logistics_risk",
        "disruption_risk",
        "delivery_risk",
        "maintenance_risk",
        "quarter_learning",
    }
    assert set(fact["top_driver"].unique()).issubset(allowed)


def test_wave7_materializer_writes_output():
    fact = materialize_wave7_luigi()
    assert not fact.empty
    assert "explainability_note" in fact.columns
