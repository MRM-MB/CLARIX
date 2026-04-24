import pandas as pd

from project.src.canonical.quarter_learning import (
    build_fact_quarter_learning_signals,
    build_fact_quarter_rollforward_inputs,
    load_wave6_inputs,
)
from project.src.loaders.materialize_wave6_luigi import materialize_wave6_luigi


def test_wave6_learning_has_unique_grain():
    inputs = load_wave6_inputs("project/data/processed")
    learning = build_fact_quarter_learning_signals(**inputs)
    assert not learning.duplicated(["scope_id", "quarter_id", "project_id"]).any()


def test_wave6_learning_signal_is_bounded_and_non_positive():
    inputs = load_wave6_inputs("project/data/processed")
    learning = build_fact_quarter_learning_signals(**inputs)
    assert ((learning["confidence_adjustment_signal"] >= -0.25) & (learning["confidence_adjustment_signal"] <= 0.0)).all()


def test_wave6_rollforward_has_unique_transition_grain():
    inputs = load_wave6_inputs("project/data/processed")
    learning = build_fact_quarter_learning_signals(**inputs)
    roll = build_fact_quarter_rollforward_inputs(
        inputs["fact_decision_history"],
        inputs["dim_project_priority"],
        learning,
    )
    assert not roll.duplicated(["scope_id", "from_quarter", "to_quarter", "project_id"]).any()


def test_wave6_rollforward_is_deterministic():
    inputs = load_wave6_inputs("project/data/processed")
    learning_a = build_fact_quarter_learning_signals(**inputs)
    learning_b = build_fact_quarter_learning_signals(**inputs)
    pd.testing.assert_frame_equal(learning_a, learning_b)
    roll_a = build_fact_quarter_rollforward_inputs(
        inputs["fact_decision_history"],
        inputs["dim_project_priority"],
        learning_a,
    )
    roll_b = build_fact_quarter_rollforward_inputs(
        inputs["fact_decision_history"],
        inputs["dim_project_priority"],
        learning_b,
    )
    pd.testing.assert_frame_equal(roll_a, roll_b)


def test_wave6_repeated_flags_and_penalties_are_visible():
    inputs = load_wave6_inputs("project/data/processed")
    learning = build_fact_quarter_learning_signals(**inputs)
    roll = build_fact_quarter_rollforward_inputs(
        inputs["fact_decision_history"],
        inputs["dim_project_priority"],
        learning,
    )
    assert learning["repeated_action_flag"].any()
    assert learning["repeated_risk_flag"].any()
    assert (roll["unresolved_action_penalty"] > 0).any()


def test_wave6_materializer_writes_outputs():
    result = materialize_wave6_luigi()
    assert set(result) == {
        "fact_quarter_rollforward_inputs",
        "fact_quarter_learning_signals",
    }
    assert not result["fact_quarter_learning_signals"].empty
