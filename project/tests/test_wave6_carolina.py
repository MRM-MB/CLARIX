"""
test_wave6_carolina.py
======================
Wave 6 Carolina validation tests — synthetic data only (no Excel required).

Run:
  pytest project/tests/test_wave6_carolina.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave6.delivery_commitment import (
    week_to_date,
    build_fact_delivery_commitment_weekly,
)
from project.src.wave6.service_memory import (
    week_to_quarter,
    build_fact_quarter_service_memory,
)
from project.src.wave6.risk_rollforward import build_fact_delivery_risk_rollforward

_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
_SYNTH = _REPO_ROOT / "processed"

_HAS_PROCESSED = (
    (_PROCESSED / "fact_scoped_logistics_weekly.csv").exists()
    and (_SYNTH / "dim_service_level_policy_synth.csv").exists()
)

# =============================================================================
# Synthetic factories
# =============================================================================

def _make_scoped_logistics(
    plants=("NW01", "NW02"),
    n_weeks=8,
    scenarios=("all_in", "expected_value"),
) -> pd.DataFrame:
    rows = []
    projects = ["SF-100001", "SF-100002"]
    for plant in plants:
        for proj in projects:
            for w in range(1, n_weeks + 1):
                for scenario in scenarios:
                    rows.append({
                        "scope_id": "mvp_3plant",
                        "scenario": scenario,
                        "project_id": proj,
                        "plant": plant,
                        "destination_country": "US",
                        "week": f"2026-W{w:02d}",
                        "transit_time_days": 5 + (w % 3),
                        "shipping_cost": 1000.0,
                        "landed_cost_proxy": 1200.0,
                        "on_time_feasible_flag": w % 3 != 0,
                        "expedite_option_flag": w % 4 == 0,
                        "logistics_risk_score": 0.1 + 0.05 * (w % 10),
                        "synthetic_dependency_flag": True,
                    })
    return pd.DataFrame(rows)


def _make_service_policy() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "revenue_tier": "Small",
            "max_allowed_late_days": 14,
            "expedite_allowed_flag": False,
            "reroute_allowed_flag": False,
            "premium_shipping_allowed_flag": False,
            "service_penalty_weight": 0.05,
            "synthetic_generation_rule": "business_rule_revenue_tier_hardcoded",
        },
        {
            "revenue_tier": "Medium",
            "max_allowed_late_days": 7,
            "expedite_allowed_flag": True,
            "reroute_allowed_flag": False,
            "premium_shipping_allowed_flag": False,
            "service_penalty_weight": 0.15,
            "synthetic_generation_rule": "business_rule_revenue_tier_hardcoded",
        },
        {
            "revenue_tier": "Large",
            "max_allowed_late_days": 3,
            "expedite_allowed_flag": True,
            "reroute_allowed_flag": True,
            "premium_shipping_allowed_flag": False,
            "service_penalty_weight": 0.30,
            "synthetic_generation_rule": "business_rule_revenue_tier_hardcoded",
        },
        {
            "revenue_tier": "Strategic",
            "max_allowed_late_days": 0,
            "expedite_allowed_flag": True,
            "reroute_allowed_flag": True,
            "premium_shipping_allowed_flag": True,
            "service_penalty_weight": 0.50,
            "synthetic_generation_rule": "business_rule_revenue_tier_hardcoded",
        },
    ])


def _make_logistics_snapshot() -> pd.DataFrame:
    rows = []
    for plant in ("NW01", "NW02"):
        for qtr in ("2026-Q1", "2026-Q2"):
            rows.append({
                "scope_id": "mvp_3plant",
                "scenario": "expected_value",
                "plant": plant,
                "destination_country": "US",
                "quarter_id": qtr,
                "route_count": 10,
                "avg_transit_time_days": 5.0,
                "avg_shipping_cost": 1000.0,
                "avg_landed_cost_proxy": 1200.0,
                "pct_on_time_feasible": 0.8,
                "pct_expedite_option": 0.2,
                "avg_logistics_risk_score": 0.3,
                "synthetic_dependency_flag": True,
            })
    return pd.DataFrame(rows)


# =============================================================================
# Helper builders
# =============================================================================

def _build_commitment() -> pd.DataFrame:
    logistics = _make_scoped_logistics()
    policy = _make_service_policy()
    return build_fact_delivery_commitment_weekly(logistics, policy)


def _build_service_memory() -> pd.DataFrame:
    logistics = _make_scoped_logistics()
    commitment = _build_commitment()
    return build_fact_quarter_service_memory(logistics, commitment)


def _build_rollforward() -> pd.DataFrame:
    memory = _build_service_memory()
    snapshot = _make_logistics_snapshot()
    return build_fact_delivery_risk_rollforward(memory, snapshot)


# =============================================================================
# week_to_date
# =============================================================================

def test_week_to_date_returns_monday():
    ts = week_to_date("2026-W01")
    assert ts.day_of_week == 0, "week_to_date should return Monday (day_of_week=0)"


def test_week_to_date_specific_value():
    ts = week_to_date("2026-W01")
    assert ts == pd.Timestamp("2025-12-29"), f"Expected 2025-12-29, got {ts}"


# =============================================================================
# week_to_quarter
# =============================================================================

@pytest.mark.parametrize("week,expected", [
    ("2026-W01", "2026-Q1"),
    ("2026-W13", "2026-Q1"),
    ("2026-W14", "2026-Q2"),
    ("2026-W26", "2026-Q2"),
    ("2026-W27", "2026-Q3"),
    ("2026-W39", "2026-Q3"),
    ("2026-W40", "2026-Q4"),
    ("2026-W52", "2026-Q4"),
    ("2026-W53", "2026-Q4"),
])
def test_week_to_quarter_mapping(week, expected):
    assert week_to_quarter(week) == expected


# =============================================================================
# fact_delivery_commitment_weekly
# =============================================================================

_COMMITMENT_REQUIRED_COLS = [
    "scope_id", "scenario", "project_id", "plant", "week",
    "requested_delivery_date", "transit_time_days", "production_time_proxy_days",
    "total_commitment_time_days", "on_time_feasible_flag", "expedite_option_flag",
    "service_violation_risk",
]


def test_delivery_commitment_has_required_columns():
    df = _build_commitment()
    for col in _COMMITMENT_REQUIRED_COLS:
        assert col in df.columns, f"Missing column: {col}"


def test_delivery_commitment_service_violation_risk_range():
    df = _build_commitment()
    assert not df.empty
    assert (df["service_violation_risk"] >= 0).all(), "service_violation_risk must be >= 0"
    assert (df["service_violation_risk"] <= 1).all(), "service_violation_risk must be <= 1"


def test_delivery_commitment_total_time_positive():
    df = _build_commitment()
    assert not df.empty
    assert (df["total_commitment_time_days"] > 0).all(), (
        "total_commitment_time_days must be > 0 for all rows"
    )


def test_delivery_commitment_unique_on_key():
    df = _build_commitment()
    key = ["scope_id", "scenario", "project_id", "plant", "week"]
    dups = df.duplicated(subset=key)
    assert not dups.any(), f"{dups.sum()} duplicate rows on natural key"


def test_delivery_commitment_synthetic_flag_true():
    df = _build_commitment()
    assert "synthetic_delivery_assumption" in df.columns
    assert (df["synthetic_delivery_assumption"] == True).all()


def test_delivery_commitment_production_proxy_is_14():
    df = _build_commitment()
    assert (df["production_time_proxy_days"] == 14).all(), (
        "production_time_proxy_days should be the synthetic constant 14"
    )


# =============================================================================
# fact_quarter_service_memory
# =============================================================================

_MEMORY_REQUIRED_COLS = [
    "scope_id", "quarter_id", "project_id",
    "prior_on_time_feasible_flag", "prior_expedite_flag",
    "prior_service_violation_risk", "carry_over_service_caution_flag",
    "explanation_note",
]


def test_service_memory_has_required_columns():
    df = _build_service_memory()
    for col in _MEMORY_REQUIRED_COLS:
        assert col in df.columns, f"Missing column: {col}"


def test_service_memory_carry_over_flag_is_boolean():
    df = _build_service_memory()
    assert not df.empty
    assert df["carry_over_service_caution_flag"].dtype == bool or \
           df["carry_over_service_caution_flag"].map(lambda x: isinstance(x, bool)).all(), \
           "carry_over_service_caution_flag must be boolean"


def test_service_memory_explanation_note_never_null():
    df = _build_service_memory()
    assert not df.empty
    null_mask = df["explanation_note"].isna() | (
        df["explanation_note"].astype(str).str.strip() == ""
    )
    assert not null_mask.any(), f"{null_mask.sum()} rows have null/empty explanation_note"


def test_service_memory_unique_on_key():
    df = _build_service_memory()
    key = ["scope_id", "quarter_id", "project_id"]
    dups = df.duplicated(subset=key)
    assert not dups.any(), f"{dups.sum()} duplicate rows on (scope_id, quarter_id, project_id)"


def test_service_memory_violation_risk_range():
    df = _build_service_memory()
    assert not df.empty
    assert (df["prior_service_violation_risk"] >= 0).all()
    assert (df["prior_service_violation_risk"] <= 1).all()


# =============================================================================
# fact_delivery_risk_rollforward
# =============================================================================

_ROLLFORWARD_REQUIRED_COLS = [
    "scope_id", "source_quarter_id", "carry_forward_quarter_id", "project_id",
    "prior_service_violation_risk", "carry_over_service_caution_flag",
    "recommended_caution_level", "caution_explanation", "synthetic_dependency_flag",
]


def test_risk_rollforward_has_required_columns():
    df = _build_rollforward()
    for col in _ROLLFORWARD_REQUIRED_COLS:
        assert col in df.columns, f"Missing column: {col}"


def test_risk_rollforward_caution_level_values():
    df = _build_rollforward()
    if df.empty:
        pytest.skip("No rollforward rows — skipping caution level check")
    valid = {"high", "medium", "low"}
    actual = set(df["recommended_caution_level"].unique())
    assert actual.issubset(valid), f"Unexpected caution levels: {actual - valid}"


def test_risk_rollforward_carry_forward_ends_in_q2():
    df = _build_rollforward()
    if df.empty:
        pytest.skip("No rollforward rows — skipping carry_forward_quarter_id check")
    assert (df["carry_forward_quarter_id"].str.endswith("Q2")).all(), (
        "carry_forward_quarter_id must always end in Q2 when source is Q1"
    )


def test_risk_rollforward_unique_on_key():
    df = _build_rollforward()
    key = ["scope_id", "source_quarter_id", "project_id"]
    dups = df.duplicated(subset=key)
    assert not dups.any(), f"{dups.sum()} duplicate rows on natural key"


def test_risk_rollforward_source_is_q1():
    df = _build_rollforward()
    if df.empty:
        pytest.skip("No rollforward rows")
    assert (df["source_quarter_id"].str.endswith("Q1")).all(), (
        "source_quarter_id must always end in Q1"
    )


def test_risk_rollforward_synthetic_flag_true():
    df = _build_rollforward()
    if df.empty:
        pytest.skip("No rollforward rows")
    assert (df["synthetic_dependency_flag"] == True).all()


# =============================================================================
# Integration tests (skip if processed files missing)
# =============================================================================

@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not available")
def test_integration_delivery_commitment_from_real_data():
    logistics = pd.read_csv(_PROCESSED / "fact_scoped_logistics_weekly.csv")
    policy = pd.read_csv(_SYNTH / "dim_service_level_policy_synth.csv")
    df = build_fact_delivery_commitment_weekly(logistics, policy)
    assert not df.empty
    key = ["scope_id", "scenario", "project_id", "plant", "week"]
    assert not df.duplicated(subset=key).any()
    assert (df["service_violation_risk"] >= 0).all()
    assert (df["service_violation_risk"] <= 1).all()


@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not available")
def test_integration_service_memory_from_real_data():
    logistics = pd.read_csv(_PROCESSED / "fact_scoped_logistics_weekly.csv")
    policy = pd.read_csv(_SYNTH / "dim_service_level_policy_synth.csv")
    commitment = build_fact_delivery_commitment_weekly(logistics, policy)
    memory = build_fact_quarter_service_memory(logistics, commitment)
    if not memory.empty:
        key = ["scope_id", "quarter_id", "project_id"]
        assert not memory.duplicated(subset=key).any()
        null_mask = memory["explanation_note"].isna()
        assert not null_mask.any()


@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not available")
def test_integration_risk_rollforward_from_real_data():
    logistics = pd.read_csv(_PROCESSED / "fact_scoped_logistics_weekly.csv")
    policy = pd.read_csv(_SYNTH / "dim_service_level_policy_synth.csv")
    snapshot = pd.read_csv(_PROCESSED / "fact_logistics_quarterly_snapshot.csv")
    commitment = build_fact_delivery_commitment_weekly(logistics, policy)
    memory = build_fact_quarter_service_memory(logistics, commitment)
    rollforward = build_fact_delivery_risk_rollforward(memory, snapshot)
    if not rollforward.empty:
        key = ["scope_id", "source_quarter_id", "project_id"]
        assert not rollforward.duplicated(subset=key).any()
        valid_levels = {"high", "medium", "low"}
        assert set(rollforward["recommended_caution_level"].unique()).issubset(valid_levels)
