"""
test_wave5_carolina.py
======================
Wave 5 Carolina validation tests — synthetic data only (no Excel required).

Run:
  pytest project/tests/test_wave5_carolina.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave5.scoped_filter import filter_sourcing, filter_logistics, DEFAULT_SCOPE
from project.src.wave5.quarterly_snapshot import (
    week_to_quarter,
    build_sourcing_quarterly_snapshot,
    build_logistics_quarterly_snapshot,
)
from project.src.wave5.decision_history import build_material_decision_history

_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
_HAS_PROCESSED = (
    (_PROCESSED / "fact_scenario_sourcing_weekly.csv").exists()
    and (_PROCESSED / "fact_scenario_logistics_weekly.csv").exists()
)

# =============================================================================
# Synthetic factories
# =============================================================================

def _make_sourcing(plants=("NW01", "NW02", "NW05", "NW09"), n_weeks=4) -> pd.DataFrame:
    rows = []
    for plant in plants:
        for w in range(1, n_weeks + 1):
            for scenario in ("all_in", "expected_value"):
                rows.append({
                    "scenario": scenario,
                    "plant": plant,
                    "component_material": f"RM-{plant}-001",
                    "week": f"2026-W{w:02d}",
                    "component_demand_qty": 100.0,
                    "available_qty": 50.0 if w <= 2 else 100.0,
                    "shortage_qty": 50.0 if w <= 2 else 0.0,
                    "coverage_days_or_weeks": 7.0,
                    "recommended_order_date": f"2026-01-{w * 7:02d}",
                    "shortage_flag": w <= 2,
                    "sourcing_risk_score": 0.8 if w <= 2 else 0.2,
                })
    return pd.DataFrame(rows)


def _make_logistics(plants=("NW01", "NW02", "NW05", "NW09"), n_weeks=4) -> pd.DataFrame:
    rows = []
    for plant in plants:
        for w in range(1, n_weeks + 1):
            for scenario in ("all_in", "expected_value"):
                rows.append({
                    "scenario": scenario,
                    "project_id": f"SF-{plant}-{w}",
                    "plant": plant,
                    "destination_country": "US",
                    "week": f"2026-W{w:02d}",
                    "transit_time_days": 5,
                    "shipping_cost": 1000.0,
                    "landed_cost_proxy": 1200.0,
                    "on_time_feasible_flag": True,
                    "expedite_option_flag": w == 1,
                    "logistics_risk_score": 0.5,
                    "synthetic_dependency_flag": True,
                })
    return pd.DataFrame(rows)


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
# scoped_filter
# =============================================================================

def test_scoped_sourcing_plants_subset():
    df = _make_sourcing()
    scoped = filter_sourcing(df)
    assert set(scoped["plant"].unique()).issubset(set(DEFAULT_SCOPE["plants"]))


def test_scoped_logistics_plants_subset():
    df = _make_logistics()
    scoped = filter_logistics(df)
    assert set(scoped["plant"].unique()).issubset(set(DEFAULT_SCOPE["plants"]))


def test_scoped_sourcing_row_count_lte_base():
    df = _make_sourcing()
    scoped = filter_sourcing(df)
    assert len(scoped) <= len(df)


def test_scoped_logistics_row_count_lte_base():
    df = _make_logistics()
    scoped = filter_logistics(df)
    assert len(scoped) <= len(df)


def test_scoped_sourcing_has_scope_id():
    df = _make_sourcing()
    scoped = filter_sourcing(df)
    assert "scope_id" in scoped.columns
    assert (scoped["scope_id"] == DEFAULT_SCOPE["scope_id"]).all()


def test_scoped_logistics_has_scope_id():
    df = _make_logistics()
    scoped = filter_logistics(df)
    assert "scope_id" in scoped.columns
    assert (scoped["scope_id"] == DEFAULT_SCOPE["scope_id"]).all()


# =============================================================================
# quarterly snapshots
# =============================================================================

def test_sourcing_snapshot_quarter_id_format():
    df = _make_sourcing()
    scoped = filter_sourcing(df)
    snap = build_sourcing_quarterly_snapshot(scoped)
    assert not snap.empty
    valid = snap["quarter_id"].str.match(r"^\d{4}-Q[1-4]$")
    assert valid.all(), f"Invalid quarter_ids: {snap[~valid]['quarter_id'].unique()}"


def test_logistics_snapshot_quarter_id_format():
    df = _make_logistics()
    scoped = filter_logistics(df)
    snap = build_logistics_quarterly_snapshot(scoped)
    assert not snap.empty
    valid = snap["quarter_id"].str.match(r"^\d{4}-Q[1-4]$")
    assert valid.all(), f"Invalid quarter_ids: {snap[~valid]['quarter_id'].unique()}"


def test_sourcing_snapshot_unique_on_natural_key():
    df = _make_sourcing()
    scoped = filter_sourcing(df)
    snap = build_sourcing_quarterly_snapshot(scoped)
    key = ["scope_id", "scenario", "plant", "component_material", "quarter_id"]
    dups = snap.duplicated(subset=key)
    assert not dups.any(), f"{dups.sum()} duplicate rows found in sourcing snapshot"


def test_logistics_snapshot_unique_on_natural_key():
    df = _make_logistics()
    scoped = filter_logistics(df)
    snap = build_logistics_quarterly_snapshot(scoped)
    key = ["scope_id", "scenario", "plant", "destination_country", "quarter_id"]
    dups = snap.duplicated(subset=key)
    assert not dups.any(), f"{dups.sum()} duplicate rows found in logistics snapshot"


def test_sourcing_snapshot_synthetic_flag_false():
    df = _make_sourcing()
    scoped = filter_sourcing(df)
    snap = build_sourcing_quarterly_snapshot(scoped)
    assert (snap["synthetic_dependency_flag"] == False).all()


def test_logistics_snapshot_synthetic_flag_true():
    df = _make_logistics()
    scoped = filter_logistics(df)
    snap = build_logistics_quarterly_snapshot(scoped)
    assert (snap["synthetic_dependency_flag"] == True).all()


# =============================================================================
# decision_history
# =============================================================================

def _make_snapshots():
    sourcing_df = _make_sourcing(plants=("NW01", "NW02", "NW05"))
    logistics_df = _make_logistics(plants=("NW01", "NW02", "NW05"))
    scoped_s = filter_sourcing(sourcing_df)
    scoped_l = filter_logistics(logistics_df)
    sourcing_snap = build_sourcing_quarterly_snapshot(scoped_s)
    logistics_snap = build_logistics_quarterly_snapshot(scoped_l)
    return sourcing_snap, logistics_snap


def test_decision_history_required_columns():
    s_snap, l_snap = _make_snapshots()
    hist = build_material_decision_history(s_snap, l_snap)
    required = [
        "scope_id", "quarter_id", "plant", "component_material",
        "prior_order_recommendation", "prior_shortage_flag", "prior_expedite_flag",
        "prior_on_time_feasible_flag", "carry_over_material_risk_flag", "learning_note",
    ]
    for col in required:
        assert col in hist.columns, f"Missing column: {col}"


def test_decision_history_carry_over_flag_is_bool():
    s_snap, l_snap = _make_snapshots()
    hist = build_material_decision_history(s_snap, l_snap)
    assert hist["carry_over_material_risk_flag"].dtype == bool or \
           hist["carry_over_material_risk_flag"].map(lambda x: isinstance(x, bool)).all()


def test_decision_history_learning_note_never_null():
    s_snap, l_snap = _make_snapshots()
    hist = build_material_decision_history(s_snap, l_snap)
    assert not hist.empty
    null_mask = hist["learning_note"].isna() | (hist["learning_note"].astype(str).str.strip() == "")
    assert not null_mask.any(), f"{null_mask.sum()} rows have null/empty learning_note"


def test_decision_history_unique_on_natural_key():
    s_snap, l_snap = _make_snapshots()
    hist = build_material_decision_history(s_snap, l_snap)
    key = ["scope_id", "quarter_id", "plant", "component_material"]
    dups = hist.duplicated(subset=key)
    assert not dups.any(), f"{dups.sum()} duplicate rows in decision history"


def test_decision_history_quarter_id_is_q1():
    s_snap, l_snap = _make_snapshots()
    hist = build_material_decision_history(s_snap, l_snap)
    assert not hist.empty
    assert (hist["quarter_id"].str.endswith("Q1")).all(), \
        "decision_history should contain only Q1 source rows"


# =============================================================================
# Integration tests (skip if processed files missing)
# =============================================================================

@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not available")
def test_integration_scoped_sourcing_from_real_data():
    df = pd.read_csv(_PROCESSED / "fact_scenario_sourcing_weekly.csv")
    scoped = filter_sourcing(df)
    assert set(scoped["plant"].unique()).issubset(set(DEFAULT_SCOPE["plants"]))
    assert len(scoped) <= len(df)


@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not available")
def test_integration_scoped_logistics_from_real_data():
    df = pd.read_csv(_PROCESSED / "fact_scenario_logistics_weekly.csv")
    scoped = filter_logistics(df)
    assert set(scoped["plant"].unique()).issubset(set(DEFAULT_SCOPE["plants"]))
    assert len(scoped) <= len(df)


@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not available")
def test_integration_quarterly_snapshots_from_real_data():
    s_df = pd.read_csv(_PROCESSED / "fact_scenario_sourcing_weekly.csv")
    l_df = pd.read_csv(_PROCESSED / "fact_scenario_logistics_weekly.csv")
    scoped_s = filter_sourcing(s_df)
    scoped_l = filter_logistics(l_df)
    s_snap = build_sourcing_quarterly_snapshot(scoped_s)
    l_snap = build_logistics_quarterly_snapshot(scoped_l)
    # Quarter IDs valid
    if not s_snap.empty:
        assert s_snap["quarter_id"].str.match(r"^\d{4}-Q[1-4]$").all()
    if not l_snap.empty:
        assert l_snap["quarter_id"].str.match(r"^\d{4}-Q[1-4]$").all()
