import pandas as pd

from project.src.canonical.quarter_business_state import (
    build_dim_region_scope,
    build_fact_decision_history,
    build_fact_pipeline_quarterly,
    build_fact_quarter_business_snapshot,
    load_wave5_inputs,
)
from project.src.loaders.materialize_wave5_luigi import materialize_wave5_luigi


def test_wave5_scope_is_explicit_and_reproducible():
    inputs = load_wave5_inputs("project/data/processed")
    scope = build_dim_region_scope(inputs["fact_pipeline_monthly"])
    denmark = scope[scope["scope_id"] == "denmark_demo"].iloc[0]
    assert denmark["included_plants"] == "NW08,NW09,NW10"
    assert bool(denmark["active_flag"]) is True


def test_wave5_quarterly_reconciles_monthly_expected_value():
    inputs = load_wave5_inputs("project/data/processed")
    scope = build_dim_region_scope(inputs["fact_pipeline_monthly"])
    quarterly = build_fact_pipeline_quarterly(inputs["fact_pipeline_monthly"], scope)
    global_total = quarterly[quarterly["scope_id"] == "global_reference"]["expected_value_quarter"].sum()
    monthly_total = inputs["fact_pipeline_monthly"]["expected_value"].sum()
    assert round(global_total, 6) == round(monthly_total, 6)


def test_wave5_snapshot_has_unique_scope_quarter():
    inputs = load_wave5_inputs("project/data/processed")
    scope = build_dim_region_scope(inputs["fact_pipeline_monthly"])
    snapshot = build_fact_quarter_business_snapshot(
        inputs["fact_pipeline_monthly"],
        inputs["dim_project_priority"],
        scope,
    )
    assert not snapshot.duplicated(["scope_id", "quarter_id"]).any()


def test_wave5_decision_history_unique_and_labeled():
    inputs = load_wave5_inputs("project/data/processed")
    scope = build_dim_region_scope(inputs["fact_pipeline_monthly"])
    history = build_fact_decision_history(
        inputs["fact_pipeline_monthly"],
        inputs["fact_integrated_risk"],
        inputs["fact_planner_actions"],
        scope,
    )
    assert not history.duplicated(["scope_id", "quarter_id", "project_id"]).any()
    labeled = history["action_outcome_status"].dropna().astype(str)
    assert labeled.str.contains("synth|no_prior", case=False, regex=True).all()


def test_wave5_carry_over_exists_for_consecutive_quarters():
    inputs = load_wave5_inputs("project/data/processed")
    scope = build_dim_region_scope(inputs["fact_pipeline_monthly"])
    history = build_fact_decision_history(
        inputs["fact_pipeline_monthly"],
        inputs["fact_integrated_risk"],
        inputs["fact_planner_actions"],
        scope,
    )
    assert history["carry_over_flag"].any()


def test_wave5_materializer_writes_outputs():
    result = materialize_wave5_luigi()
    assert set(result) == {
        "dim_region_scope",
        "fact_pipeline_quarterly",
        "fact_quarter_business_snapshot",
        "fact_decision_history",
    }
    assert not result["fact_pipeline_quarterly"].empty
