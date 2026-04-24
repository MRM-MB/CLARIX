"""
test_wave1_lara.py
==================
Wave 1 validation tests.

Tests use synthetic DataFrames so they pass without the real Excel file.
Integration markers run against the real dataset when available.

Run:
  pytest project/tests/test_wave1_lara.py -v
  pytest project/tests/test_wave1_lara.py -v -m integration  # real data
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure repo root importable
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave1.capacity_baseline import build_fact_wc_capacity_weekly, validate_capacity
from project.src.wave1.calendar_bridge import (
    _build_fallback,
    validate_calendar_bridge,
)
from project.src.wave1.operational_mapping import (
    summarise_mapping_gaps,
    _assign_reason_code,
    RC_COMPLETE,
    RC_MISSING_WC,
    RC_MISSING_CT,
    RC_MISSING_TOOL,
)
from project.src.wave1.scenario_limits import build_dim_wc_scenario_limits

_XLSX = _REPO_ROOT / "data" / "hackathon_dataset.xlsx"
_HAS_XLSX = _XLSX.exists()


# =============================================================================
# Helpers: synthetic data factories
# =============================================================================

def _make_capacity_df(n_plants=2, n_wc=3, n_weeks=4) -> pd.DataFrame:
    """Synthetic fact_wc_capacity_weekly-shaped dataframe."""
    rows = []
    for plant in [f"NW{i:02d}" for i in range(1, n_plants + 1)]:
        for wc in [f"P01_{plant}_PRESS_{j}" for j in range(1, n_wc + 1)]:
            for week in range(1, n_weeks + 1):
                avail = float(40 + week * 2)
                planned = float(35 + week)
                rows.append({
                    "plant": plant,
                    "work_center": wc,
                    "year": 2026,
                    "week": week,
                    "week_start": pd.Timestamp(f"2026-01-{week * 7 - 6:02d}"),
                    "available_capacity_hours": avail,
                    "planned_load_hours": planned,
                    "remaining_capacity_hours": max(0.0, avail - planned),
                    "missing_capacity_hours": max(0.0, planned - avail),
                })
    return pd.DataFrame(rows)


def _make_bridge_df() -> pd.DataFrame:
    """Synthetic bridge_material_tool_wc."""
    return pd.DataFrame([
        {"plant": "NW01", "material": "MAT001", "revision": "A1",
         "tool_no": "T100", "work_center": "P01_NW01_PRESS_1",
         "cycle_time": 2.5, "mapping_status": "Active", "reason_code": RC_COMPLETE},
        {"plant": "NW01", "material": "MAT002", "revision": "UNKNOWN",
         "tool_no": None, "work_center": None,
         "cycle_time": None, "mapping_status": "Active", "reason_code": RC_MISSING_WC},
        {"plant": "NW01", "material": "MAT001", "revision": "A2",
         "tool_no": "T100", "work_center": "P01_NW01_PRESS_1",
         "cycle_time": 2.5, "mapping_status": "Active", "reason_code": RC_COMPLETE},
    ])


# =============================================================================
# Unit tests: capacity_baseline
# =============================================================================

class TestCapacityBaseline:
    def test_unique_by_plant_wc_week(self):
        """Every row must be unique by (plant, work_center, week)."""
        df = _make_capacity_df()
        result = validate_capacity(df)
        assert result["unique_by_plant_wc_week"] == 1, (
            f"{result['duplicate_rows']} duplicate (plant,wc,week) rows"
        )

    def test_remaining_capacity_non_negative(self):
        df = _make_capacity_df()
        assert (df["remaining_capacity_hours"] >= 0).all()

    def test_missing_capacity_non_negative(self):
        df = _make_capacity_df()
        assert (df["missing_capacity_hours"] >= 0).all()

    def test_derived_columns_consistent(self):
        """remaining + missing should account for available - planned."""
        df = _make_capacity_df()
        # Where available > planned: remaining = avail - planned, missing = 0
        over = df[df["available_capacity_hours"] > df["planned_load_hours"]]
        if not over.empty:
            expected_remaining = over["available_capacity_hours"] - over["planned_load_hours"]
            pd.testing.assert_series_equal(
                over["remaining_capacity_hours"].reset_index(drop=True),
                expected_remaining.reset_index(drop=True),
                check_names=False,
            )

    def test_required_columns_present(self):
        df = _make_capacity_df()
        required = [
            "plant", "work_center", "year", "week",
            "available_capacity_hours", "planned_load_hours",
            "remaining_capacity_hours", "missing_capacity_hours",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"


# =============================================================================
# Unit tests: calendar_bridge
# =============================================================================

class TestCalendarBridge:
    def test_fallback_weights_sum_to_one(self):
        """allocation_weight must sum to ~1.0 per (plant, year, month)."""
        bridge = _build_fallback(start_year=2026, end_year=2026)
        result = validate_calendar_bridge(bridge)
        assert result["valid"], (
            f"Max allocation_weight error: {result['max_allocation_weight_error']}"
        )

    def test_fallback_no_null_weights(self):
        bridge = _build_fallback(start_year=2026, end_year=2026)
        assert bridge["allocation_weight"].notna().all()

    def test_fallback_weights_positive(self):
        bridge = _build_fallback(start_year=2026, end_year=2026)
        assert (bridge["allocation_weight"] > 0).all()

    def test_required_columns_present(self):
        bridge = _build_fallback(start_year=2026, end_year=2026)
        required = ["plant", "year", "month", "week",
                    "allocation_weight", "working_day_weight", "bridge_version"]
        for col in required:
            assert col in bridge.columns, f"Missing column: {col}"

    def test_2026_has_12_months(self):
        bridge = _build_fallback(start_year=2026, end_year=2026)
        months = bridge[bridge["plant"] == "ALL"]["month"].unique()
        assert len(months) == 12, f"Expected 12 months, got {len(months)}"

    def test_week_straddle_jan_feb(self):
        """ISO week straddling Jan/Feb must appear in 2 months, each with a partial weight."""
        bridge = _build_fallback(start_year=2026, end_year=2026)
        # Find a week that appears in two months (in the same iso year)
        multi = bridge.groupby(["plant", "year", "week"])["month"].nunique()
        straddling = multi[multi > 1]
        if not straddling.empty:
            (_, yr, wk) = straddling.index[0]
            rows = bridge[(bridge["year"] == yr) & (bridge["week"] == wk)]
            # Each row is a fraction of its own month — both must be between 0 and 1
            assert len(rows) == 2, f"Expected 2 month rows for straddling week, got {len(rows)}"
            assert (rows["allocation_weight"] > 0).all()
            assert (rows["allocation_weight"] < 1).all()


# =============================================================================
# Unit tests: operational_mapping
# =============================================================================

class TestOperationalMapping:
    def test_reason_code_complete(self):
        row = pd.Series({
            "work_center_raw": "PRESS_1",
            "cycle_time_raw": "2.5",
            "tool_no": "T100",
        })
        assert _assign_reason_code(row) == RC_COMPLETE

    def test_reason_code_missing_wc(self):
        row = pd.Series({
            "work_center_raw": "#N/A",
            "cycle_time_raw": "2.5",
            "tool_no": "T100",
        })
        assert _assign_reason_code(row) == RC_MISSING_WC

    def test_reason_code_missing_ct(self):
        row = pd.Series({
            "work_center_raw": "PRESS_1",
            "cycle_time_raw": "Missing CT",
            "tool_no": "T100",
        })
        assert _assign_reason_code(row) == RC_MISSING_CT

    def test_reason_code_missing_tool(self):
        row = pd.Series({
            "work_center_raw": "PRESS_1",
            "cycle_time_raw": "2.5",
            "tool_no": None,
        })
        assert _assign_reason_code(row) == RC_MISSING_TOOL

    def test_unresolved_mappings_counted(self):
        bridge = _make_bridge_df()
        gap = summarise_mapping_gaps(bridge)
        assert gap["total_rows"] == 3
        assert gap["complete_mappings"] == 2
        assert gap["missing_work_center"] == 1

    def test_revision_mismatch_detected(self):
        """Materials with >1 Rev no at same plant must be counted."""
        bridge = _make_bridge_df()
        gap = summarise_mapping_gaps(bridge)
        # MAT001 appears with A1 and A2 at NW01
        assert gap["materials_with_revision_mismatch"] >= 1

    def test_required_columns_present(self):
        bridge = _make_bridge_df()
        required = ["plant", "material", "revision", "tool_no",
                    "work_center", "cycle_time", "mapping_status", "reason_code"]
        for col in required:
            assert col in bridge.columns, f"Missing: {col}"


# =============================================================================
# Unit tests: scenario_limits
# =============================================================================

class TestScenarioLimits:
    def _make_raw_limits(self) -> pd.DataFrame:
        """Minimal synthetic 2_5 equivalent."""
        rows = []
        limit_labels = [
            "Downside Limit 2 (hrs)", "Downside Limit 1 (hrs)",
            "Available Capacity, hours", "Upside Limit 1 (hrs)", "Upside Limit 2 (hrs)",
        ]
        for plant in ["NW01", "NW02"]:
            for wc_desc in ["PRESS_1", "PRESS_2"]:
                for i, label in enumerate(limit_labels):
                    rows.append({
                        "Plant": plant,
                        "WC-Description": wc_desc,
                        "AP Limit": label,
                        "Weekly available time": 40.0 + i * 8,
                        "OEE (in %)": 0.85,
                        "AP Limit time (in H)": 40.0 + i * 8,
                    })
        return pd.DataFrame(rows)

    def test_five_levels_per_wc(self):
        """Each WC should have all 5 scenario limit levels."""
        # Test using mapping logic directly
        limit_labels = [
            "Downside Limit 2 (hrs)", "Downside Limit 1 (hrs)",
            "Available Capacity, hours", "Upside Limit 1 (hrs)", "Upside Limit 2 (hrs)",
        ]
        from project.src.wave1.scenario_limits import _map_limit_name
        names = [_map_limit_name(lbl, i) for i, lbl in enumerate(limit_labels)]
        assert names == ["downside_2", "downside_1", "baseline", "upside_1", "upside_2"]

    def test_required_columns_present(self):
        required = ["plant", "work_center", "scenario_limit_name",
                    "available_hours_variant", "oee_variant",
                    "weekly_time_variant", "source_level"]
        # Validate column set using empty frame
        from project.src.wave1.scenario_limits import _empty_limits
        empty = _empty_limits()
        for col in required:
            assert col in empty.columns, f"Missing: {col}"

    def test_baseline_level_name(self):
        from project.src.wave1.scenario_limits import _map_limit_name
        assert _map_limit_name("Available Capacity, hours", 2) == "baseline"

    def test_upshift_levels_exist(self):
        from project.src.wave1.scenario_limits import _map_limit_name
        assert _map_limit_name("Upside Limit 1 (hrs)", 3) == "upside_1"
        assert _map_limit_name("Upside Limit 2 (hrs)", 4) == "upside_2"


# =============================================================================
# Integration tests (require real Excel)
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not _HAS_XLSX, reason="hackathon_dataset.xlsx not found")
class TestIntegration:
    def test_bridge_material_tool_wc_rows(self):
        from project.src.wave1.operational_mapping import build_bridge_material_tool_wc
        bridge = build_bridge_material_tool_wc()
        assert len(bridge) > 1000, f"Expected >1000 rows, got {len(bridge)}"

    def test_capacity_unique(self):
        cap = build_fact_wc_capacity_weekly()
        result = validate_capacity(cap)
        assert result["unique_by_plant_wc_week"] == 1, (
            f"{result['duplicate_rows']} duplicate (plant,wc,week) rows"
        )

    def test_calendar_bridge_weights_valid(self):
        from project.src.wave1.calendar_bridge import build_bridge_month_week_calendar
        bridge = build_bridge_month_week_calendar()
        result = validate_calendar_bridge(bridge)
        assert result["valid"], f"Weight error: {result['max_allocation_weight_error']}"

    def test_scenario_limits_five_levels(self):
        limits = build_dim_wc_scenario_limits()
        assert not limits.empty
        counts = limits.groupby(["plant", "work_center"])["scenario_limit_name"].count()
        # Most WCs should have 5 levels
        modal_count = counts.mode().iloc[0]
        assert modal_count == 5, f"Expected 5 levels per WC, got modal={modal_count}"

    def test_revision_mismatches_surfaced(self):
        from project.src.wave1.operational_mapping import build_bridge_material_tool_wc
        bridge = build_bridge_material_tool_wc()
        gap = summarise_mapping_gaps(bridge)
        # Should have explicit counts (may be 0, but must be reported)
        assert "materials_with_revision_mismatch" in gap

    def test_unresolved_mappings_explicit(self):
        from project.src.wave1.operational_mapping import build_bridge_material_tool_wc
        bridge = build_bridge_material_tool_wc()
        # reason_code column must be present and non-null
        assert "reason_code" in bridge.columns
        assert bridge["reason_code"].notna().all()
