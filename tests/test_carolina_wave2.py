"""
tests/test_carolina_wave2.py — pytest suite for Carolina Wave 2 modules.

Run with:
    pytest tests/test_carolina_wave2.py -v

Tests use the actual processed/ CSVs as input; they are skipped if the
required files are missing.
"""

import os
import sys

import pandas as pd
import pytest

# Ensure src is on the path when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.carolina.sourcing_engine import run_sourcing_engine
from src.carolina.logistics_engine import run_logistics_engine


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(REPO_ROOT, "processed")

REQUIRED_SOURCING_FILES = [
    "fact_finished_to_component.csv",
    "fact_inventory_snapshot.csv",
    "dim_procurement_logic.csv",
]

REQUIRED_LOGISTICS_FILES = [
    "dim_shipping_lane_synth.csv",
    "dim_country_cost_index_synth.csv",
    "dim_service_level_policy_synth.csv",
    "fact_finished_to_component.csv",  # needed for stub generation
]


def _files_present(filenames: list) -> bool:
    return all(os.path.exists(os.path.join(PROCESSED_DIR, f)) for f in filenames)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sourcing_df():
    if not _files_present(REQUIRED_SOURCING_FILES):
        pytest.skip("Required sourcing input files not present in processed/")
    return run_sourcing_engine(processed_dir=PROCESSED_DIR)


@pytest.fixture(scope="module")
def logistics_df():
    if not _files_present(REQUIRED_LOGISTICS_FILES):
        pytest.skip("Required logistics input files not present in processed/")
    return run_logistics_engine(processed_dir=PROCESSED_DIR)


# ---------------------------------------------------------------------------
# Sourcing engine tests
# ---------------------------------------------------------------------------

class TestSourcingEngine:

    def test_unique_on_scenario_plant_component_week(self, sourcing_df):
        """fact_scenario_sourcing_weekly must be unique on (scenario, plant, component_material, week)."""
        key_cols = ["scenario", "plant", "component_material", "week"]
        dupes = sourcing_df.duplicated(subset=key_cols)
        assert not dupes.any(), (
            f"Found {dupes.sum()} duplicate rows on {key_cols}"
        )

    def test_shortage_flag_is_boolean(self, sourcing_df):
        """shortage_flag must contain only boolean values."""
        assert sourcing_df["shortage_flag"].dtype == bool or set(sourcing_df["shortage_flag"].unique()).issubset(
            {True, False}
        ), "shortage_flag contains non-boolean values"

    def test_sourcing_risk_score_between_0_and_1(self, sourcing_df):
        """sourcing_risk_score must be in [0, 1]."""
        assert sourcing_df["sourcing_risk_score"].between(0.0, 1.0).all(), (
            "sourcing_risk_score out of [0, 1] range: "
            f"min={sourcing_df['sourcing_risk_score'].min()}, "
            f"max={sourcing_df['sourcing_risk_score'].max()}"
        )

    def test_all_three_scenarios_present(self, sourcing_df):
        """All three scenarios must be present in the sourcing output."""
        expected_scenarios = {"all_in", "expected_value", "high_confidence"}
        actual_scenarios = set(sourcing_df["scenario"].unique())
        assert expected_scenarios.issubset(actual_scenarios), (
            f"Missing scenarios: {expected_scenarios - actual_scenarios}"
        )

    def test_required_output_columns_present(self, sourcing_df):
        """All required output columns must be present."""
        required = {
            "scenario", "plant", "component_material", "week",
            "component_demand_qty", "available_qty", "shortage_qty",
            "coverage_days_or_weeks", "recommended_order_date",
            "shortage_flag", "sourcing_risk_score",
        }
        missing = required - set(sourcing_df.columns)
        assert not missing, f"Missing output columns: {missing}"

    def test_no_negative_shortage_qty(self, sourcing_df):
        """shortage_qty must never be negative."""
        assert (sourcing_df["shortage_qty"] >= 0).all(), "Found negative shortage_qty values"

    def test_shortage_flag_consistent_with_shortage_qty(self, sourcing_df):
        """shortage_flag should be True iff shortage_qty > 0."""
        flag_true = sourcing_df["shortage_flag"]
        qty_pos = sourcing_df["shortage_qty"] > 0
        assert (flag_true == qty_pos).all(), (
            "shortage_flag is inconsistent with shortage_qty > 0"
        )


# ---------------------------------------------------------------------------
# Logistics engine tests
# ---------------------------------------------------------------------------

class TestLogisticsEngine:

    def test_unique_on_scenario_project_plant_dest_week(self, logistics_df):
        """fact_scenario_logistics_weekly must be unique on (scenario, project_id, plant, destination_country, week)."""
        key_cols = ["scenario", "project_id", "plant", "destination_country", "week"]
        dupes = logistics_df.duplicated(subset=key_cols)
        assert not dupes.any(), (
            f"Found {dupes.sum()} duplicate rows on {key_cols}"
        )

    def test_logistics_risk_score_between_0_and_1(self, logistics_df):
        """logistics_risk_score must be in [0, 1]."""
        assert logistics_df["logistics_risk_score"].between(0.0, 1.0).all(), (
            "logistics_risk_score out of [0, 1] range: "
            f"min={logistics_df['logistics_risk_score'].min()}, "
            f"max={logistics_df['logistics_risk_score'].max()}"
        )

    def test_synthetic_dependency_flag_always_true(self, logistics_df):
        """synthetic_dependency_flag must be True for every row."""
        assert logistics_df["synthetic_dependency_flag"].all(), (
            "synthetic_dependency_flag contains False values — unexpected"
        )

    def test_required_output_columns_present(self, logistics_df):
        """All required output columns must be present."""
        required = {
            "scenario", "project_id", "plant", "destination_country", "week",
            "transit_time_days", "shipping_cost", "landed_cost_proxy",
            "on_time_feasible_flag", "expedite_option_flag",
            "logistics_risk_score", "synthetic_dependency_flag",
        }
        missing = required - set(logistics_df.columns)
        assert not missing, f"Missing output columns: {missing}"

    def test_shipping_cost_non_negative(self, logistics_df):
        """shipping_cost must be non-negative."""
        assert (logistics_df["shipping_cost"] >= 0).all(), "Found negative shipping_cost values"

    def test_landed_cost_proxy_gte_shipping_cost(self, logistics_df):
        """landed_cost_proxy must be >= shipping_cost (cost index multiplier >= 1)."""
        assert (logistics_df["landed_cost_proxy"] >= logistics_df["shipping_cost"] * 0.99).all(), (
            "landed_cost_proxy is less than shipping_cost — cost index logic error"
        )
