"""Tests for Wave 3 Carolina: Action Policy & QA Guardrails."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

# Paths
REAL_PROCESSED = Path(__file__).parent.parent / "data" / "processed"
SYNTH_PROCESSED = Path(__file__).parent.parent.parent / "processed"

SOURCING_PATH = REAL_PROCESSED / "fact_scenario_sourcing_weekly.csv"
LOGISTICS_PATH = REAL_PROCESSED / "fact_scenario_logistics_weekly.csv"
BOTTLENECK_PATH = REAL_PROCESSED / "fact_capacity_bottleneck_summary.csv"
RISK_PATH = REAL_PROCESSED / "fact_integrated_risk_base.csv"

_PROCESSED_FILES_PRESENT = all(
    p.exists()
    for p in [SOURCING_PATH, LOGISTICS_PATH, BOTTLENECK_PATH, RISK_PATH]
)

skip_if_no_data = pytest.mark.skipif(
    not _PROCESSED_FILES_PRESENT,
    reason="Processed Wave 2 files not found — skipping data-dependent tests.",
)

# ---------------------------------------------------------------------------
# dim_action_policy tests (no data dependency)
# ---------------------------------------------------------------------------

from project.src.actions.action_policy import build_dim_action_policy


def test_policy_has_nine_rows():
    df = build_dim_action_policy()
    assert len(df) == 9, f"Expected 9 rows, got {len(df)}"


def test_policy_required_columns_present():
    df = build_dim_action_policy()
    required = [
        "action_type",
        "trigger_condition",
        "minimum_priority_threshold",
        "minimum_risk_threshold",
        "requires_alt_plant_flag",
        "allows_expedite_flag",
        "allows_upshift_flag",
        "expected_effect_type",
        "policy_version",
    ]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"


def test_policy_version_is_v1():
    df = build_dim_action_policy()
    assert (df["policy_version"] == "v1").all(), "All policy_version values must be 'v1'"


def test_policy_priority_threshold_range():
    df = build_dim_action_policy()
    assert (
        (df["minimum_priority_threshold"] >= 0) & (df["minimum_priority_threshold"] <= 1)
    ).all(), "minimum_priority_threshold must be in [0, 1]"


def test_policy_risk_threshold_range():
    df = build_dim_action_policy()
    assert (
        (df["minimum_risk_threshold"] >= 0) & (df["minimum_risk_threshold"] <= 1)
    ).all(), "minimum_risk_threshold must be in [0, 1]"


def test_policy_action_types_unique():
    df = build_dim_action_policy()
    assert df["action_type"].nunique() == len(df), "action_type values must be unique"


def test_policy_expected_effect_type_valid():
    df = build_dim_action_policy()
    valid = {
        "reduce_shortage",
        "reduce_delay",
        "reduce_overload",
        "reduce_cost",
        "escalate_decision",
        "hedge_uncertainty",
    }
    invalid = set(df["expected_effect_type"].unique()) - valid
    assert not invalid, f"Invalid expected_effect_type values: {invalid}"


# ---------------------------------------------------------------------------
# fact_data_quality_flags tests (require processed files)
# ---------------------------------------------------------------------------

from project.src.actions.qa_guardrails import build_fact_data_quality_flags


@skip_if_no_data
def test_flags_required_columns():
    df = build_fact_data_quality_flags(REAL_PROCESSED, SYNTH_PROCESSED)
    required = [
        "entity_type",
        "entity_key",
        "issue_type",
        "severity",
        "penalty_score",
        "reason_code",
        "recommended_handling",
    ]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"


@skip_if_no_data
def test_flags_penalty_score_range():
    df = build_fact_data_quality_flags(REAL_PROCESSED, SYNTH_PROCESSED)
    assert (
        (df["penalty_score"] >= 0) & (df["penalty_score"] <= 1)
    ).all(), "penalty_score must be in [0, 1]"


@skip_if_no_data
def test_flags_severity_valid_values():
    df = build_fact_data_quality_flags(REAL_PROCESSED, SYNTH_PROCESSED)
    valid = {"critical", "warning", "info"}
    found = set(df["severity"].unique())
    invalid = found - valid
    assert not invalid, f"Invalid severity values: {invalid}"


@skip_if_no_data
def test_flags_recommended_handling_valid_values():
    df = build_fact_data_quality_flags(REAL_PROCESSED, SYNTH_PROCESSED)
    valid = {"block", "weaken", "flag_only"}
    found = set(df["recommended_handling"].unique())
    invalid = found - valid
    assert not invalid, f"Invalid recommended_handling values: {invalid}"


@skip_if_no_data
def test_flags_no_duplicate_keys():
    df = build_fact_data_quality_flags(REAL_PROCESSED, SYNTH_PROCESSED)
    dupes = df.duplicated(subset=["entity_type", "entity_key", "issue_type"])
    assert not dupes.any(), f"Found {dupes.sum()} duplicate (entity_type, entity_key, issue_type) rows"


@skip_if_no_data
def test_flags_entity_type_valid_values():
    df = build_fact_data_quality_flags(REAL_PROCESSED, SYNTH_PROCESSED)
    valid = {"sourcing_row", "logistics_row", "bottleneck_row", "risk_row"}
    found = set(df["entity_type"].unique())
    invalid = found - valid
    assert not invalid, f"Invalid entity_type values: {invalid}"


@skip_if_no_data
def test_flags_returns_dataframe():
    result = build_fact_data_quality_flags(REAL_PROCESSED, SYNTH_PROCESSED)
    assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# wave3_runner integration test
# ---------------------------------------------------------------------------

@skip_if_no_data
def test_runner_returns_both_tables(tmp_path):
    from project.src.actions.wave3_runner import run_carolina_wave3
    result = run_carolina_wave3(
        real_processed_dir=REAL_PROCESSED,
        synth_processed_dir=SYNTH_PROCESSED,
    )
    assert "dim_action_policy" in result
    assert "fact_data_quality_flags" in result
    assert isinstance(result["dim_action_policy"], pd.DataFrame)
    assert isinstance(result["fact_data_quality_flags"], pd.DataFrame)
    assert len(result["dim_action_policy"]) == 9
