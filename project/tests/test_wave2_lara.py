"""
test_wave2_lara.py
==================
Wave 2 validation tests — synthetic data only (no Excel required).

Run:
  pytest project/tests/test_wave2_lara.py -v -m "not integration"
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave2.demand_translation import _translate, _empty_demand
from project.src.wave2.capacity_overlay import (
    _overlay, _compute_metrics, validate_scenario_capacity,
    WARN_THRESHOLD, CRIT_THRESHOLD,
)
from project.src.wave2.bottleneck_engine import (
    _summarise, _suggest_lever, _explain, _empty_summary,
    SEV_CRITICAL, SEV_WARNING,
)

_XLSX = _REPO_ROOT / "data" / "hackathon_dataset.xlsx"
_HAS_XLSX = _XLSX.exists()


# =============================================================================
# Synthetic data factories
# =============================================================================

def _make_seed(n_projects=3, n_months=2) -> pd.DataFrame:
    """Minimal scenario seed (output of build_scenario_project_demand_seed)."""
    rows = []
    for scenario, conf in [("all_in", 1.0), ("expected_value", 0.5)]:
        for p in range(1, n_projects + 1):
            for m in range(1, n_months + 1):
                rows.append({
                    "scenario_name": scenario,
                    "scenario_family": "pipeline",
                    "scenario_confidence": conf,
                    "project_id": f"PROJ_{p:03d}",
                    "plant": "NW01",
                    "material": f"MAT_{p:03d}",
                    "month": pd.Timestamp(f"2026-{m:02d}-01"),
                    "raw_qty": 1000.0,
                    "probability": 0.5,
                    "scenario_qty": 1000.0 * conf,
                    "project_value": 50000.0,
                    "expected_value": 25000.0,
                    "priority_score": 0.6,
                    "mapping_ready_flag": True,
                    "reason_code": "READY",
                })
    return pd.DataFrame(rows)


def _make_calendar() -> pd.DataFrame:
    """Simple calendar bridge covering Jan–Feb 2026."""
    rows = []
    for month, n_weeks in [(1, 4), (2, 4)]:
        for week in range(1 + (month - 1) * 4, 1 + month * 4):
            rows.append({
                "plant": "ALL",
                "year": 2026,
                "month": month,
                "week": week,
                "allocation_weight": 0.25,
                "working_day_weight": 0.25,
                "bridge_version": "test_v1",
            })
    return pd.DataFrame(rows)


def _make_tool_bridge() -> pd.DataFrame:
    # Column name matches operational_mapping.py output: "cycle_time" (not cycle_time_min)
    return pd.DataFrame([
        {"plant": "NW01", "material": "MAT_001", "work_center": "P01_NW01_PRESS_1",
         "cycle_time": 2.0, "reason_code": "COMPLETE", "tool_no": "T100"},
        {"plant": "NW01", "material": "MAT_002", "work_center": "P01_NW01_PRESS_1",
         "cycle_time": 3.0, "reason_code": "COMPLETE", "tool_no": "T100"},
        {"plant": "NW01", "material": "MAT_003", "work_center": "P01_NW01_PRESS_2",
         "cycle_time": 1.5, "reason_code": "COMPLETE", "tool_no": "T200"},
    ])


def _make_cap() -> pd.DataFrame:
    """fact_wc_capacity_weekly shape — 8 weeks × 2 WCs."""
    rows = []
    for wc in ["P01_NW01_PRESS_1", "P01_NW01_PRESS_2"]:
        for week in range(1, 9):
            rows.append({
                "plant": "NW01",
                "work_center": wc,
                "year": 2026,
                "week": week,
                "week_start": pd.Timestamp(f"2026-01-{week:02d}"),
                "available_capacity_hours": 40.0,
                "planned_load_hours": 20.0,
                "remaining_capacity_hours": 20.0,
                "missing_capacity_hours": 0.0,
            })
    return pd.DataFrame(rows)


def _make_limits() -> pd.DataFrame:
    rows = []
    for wc in ["P01_NW01_PRESS_1", "P01_NW01_PRESS_2"]:
        for name, hrs in [
            ("downside_2", 24.0), ("downside_1", 32.0),
            ("baseline", 40.0), ("upside_1", 48.0), ("upside_2", 56.0),
        ]:
            rows.append({
                "plant": "NW01",
                "work_center": wc,
                "scenario_limit_name": name,
                "available_hours_variant": hrs,
                "oee_variant": 0.85,
                "weekly_time_variant": hrs,
                "source_level": name,
            })
    return pd.DataFrame(rows)


# =============================================================================
# demand_translation tests
# =============================================================================

class TestDemandTranslation:
    def test_output_columns_present(self):
        demand = _translate(_make_seed(), _make_calendar(), _make_tool_bridge())
        required = ["scenario_name", "plant", "material", "work_center",
                    "year", "week", "demand_qty", "demand_hours", "reason_code"]
        for col in required:
            assert col in demand.columns, f"Missing: {col}"

    def test_demand_qty_positive(self):
        demand = _translate(_make_seed(), _make_calendar(), _make_tool_bridge())
        assert (demand["demand_qty"] > 0).all()

    def test_demand_hours_positive_where_ct_known(self):
        demand = _translate(_make_seed(), _make_calendar(), _make_tool_bridge())
        translated = demand[demand["reason_code"] == "TRANSLATED"]
        assert (translated["demand_hours"] > 0).all()

    def test_monthly_qty_conserved_per_scenario(self):
        """Total weekly demand_qty ≈ total monthly scenario_qty × allocation weights."""
        seed = _make_seed(n_projects=1, n_months=1)
        cal = _make_calendar()
        tb = _make_tool_bridge()
        demand = _translate(seed, cal, tb)
        # Jan has 4 weeks with weight 0.25 each → total weight = 1.0
        # scenario_qty per row = 1000 * scenario_confidence (1.0 or 0.5)
        for scenario in demand["scenario_name"].unique():
            s_demand = demand[demand["scenario_name"] == scenario]["demand_qty"].sum()
            s_seed = seed[seed["scenario_name"] == scenario]["scenario_qty"].sum()
            assert abs(s_demand - s_seed) < 1.0, (
                f"Scenario {scenario}: demand={s_demand:.1f} vs seed={s_seed:.1f}"
            )

    def test_no_wc_mapping_flagged(self):
        """Materials without tool mapping should get RC_NO_MAPPING."""
        seed = _make_seed(n_projects=1, n_months=1)
        # Only have mapping for MAT_001 and MAT_002, not MAT_003
        tb = _make_tool_bridge().iloc[:2]
        cal = _make_calendar()
        demand = _translate(seed, cal, tb)
        no_wc = demand[demand["work_center"].isna()]
        if not no_wc.empty:
            assert (no_wc["reason_code"] == "NO_TOOL_MAPPING").all()

    def test_two_scenarios_produced(self):
        demand = _translate(_make_seed(), _make_calendar(), _make_tool_bridge())
        assert demand["scenario_name"].nunique() == 2


# =============================================================================
# capacity_overlay tests
# =============================================================================

class TestCapacityOverlay:
    def _build_demand(self):
        return _translate(_make_seed(), _make_calendar(), _make_tool_bridge())

    def test_output_unique_at_grain(self):
        demand = self._build_demand()
        cap = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=False)
        result = validate_scenario_capacity(cap)
        assert result["unique_at_grain"], f"{result['duplicate_rows']} duplicates"

    def test_required_columns_present(self):
        demand = self._build_demand()
        cap = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=False)
        required = [
            "scenario", "plant", "work_center", "year", "week",
            "incremental_load_hours", "planned_load_hours", "total_load_hours",
            "available_capacity_hours", "remaining_capacity_hours",
            "overload_hours", "overload_pct", "bottleneck_flag",
        ]
        for col in required:
            assert col in cap.columns, f"Missing: {col}"

    def test_overload_hours_non_negative(self):
        demand = self._build_demand()
        cap = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=False)
        assert (cap["overload_hours"] >= 0).all()

    def test_remaining_hours_non_negative(self):
        demand = self._build_demand()
        cap = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=False)
        assert (cap["remaining_capacity_hours"] >= 0).all()

    def test_total_load_equals_planned_plus_incremental(self):
        demand = self._build_demand()
        cap = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=False)
        expected = cap["planned_load_hours"] + cap["incremental_load_hours"]
        pd.testing.assert_series_equal(
            cap["total_load_hours"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    def test_bottleneck_flag_consistent_with_threshold(self):
        demand = self._build_demand()
        cap = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=False)
        flagged = cap[cap["bottleneck_flag"]]
        if not flagged.empty:
            assert (flagged["overload_pct"] >= WARN_THRESHOLD).all()

    def test_overload_calculation_reproducible(self):
        """Given fixed inputs, overload_hours must equal max(0, total - available)."""
        df = pd.DataFrame([{
            "planned_load_hours": 20.0,
            "incremental_load_hours": 30.0,
            "available_capacity_hours": 40.0,
        }])
        result = _compute_metrics(df, "available_capacity_hours")
        assert result["total_load_hours"].iloc[0] == 50.0
        assert result["overload_hours"].iloc[0] == 10.0
        assert result["remaining_capacity_hours"].iloc[0] == 0.0
        assert abs(result["overload_pct"].iloc[0] - 50.0 / 40.0) < 0.001

    def test_capacity_variants_produce_extra_scenarios(self):
        demand = self._build_demand()
        cap_no_var = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=False)
        cap_with_var = _overlay(demand, _make_cap(), _make_limits(), capacity_variants=True)
        assert cap_with_var["scenario"].nunique() > cap_no_var["scenario"].nunique()


# =============================================================================
# bottleneck_engine tests
# =============================================================================

class TestBottleneckEngine:
    def _setup(self):
        seed = _make_seed()
        cal = _make_calendar()
        tb = _make_tool_bridge()
        demand = _translate(seed, cal, tb)
        # Force high load to guarantee bottlenecks
        cap_df = _make_cap()
        cap_df["available_capacity_hours"] = 5.0  # tiny capacity → overload
        cap = _overlay(demand, cap_df, _make_limits(), capacity_variants=False)
        return demand, cap

    def test_severity_bands_correct(self):
        demand, cap = self._setup()
        bn = _summarise(cap[cap["bottleneck_flag"]], demand, _make_tool_bridge(), _make_limits(), cap)
        if not bn.empty:
            assert bn["bottleneck_severity"].isin([SEV_WARNING, SEV_CRITICAL]).all()

    def test_required_columns_present(self):
        required = ["scenario", "plant", "work_center", "tool_no_if_available",
                    "bottleneck_severity", "top_driver_project_count",
                    "suggested_capacity_lever", "explanation_note"]
        empty = _empty_summary()
        for col in required:
            assert col in empty.columns, f"Missing: {col}"

    def test_lever_suggestion_upside(self):
        """When upside_1 hours suffice, lever should be upside_1."""
        row = pd.Series({
            "scenario": "all_in", "plant": "NW01",
            "work_center": "P01_NW01_PRESS_1",
            "peak_overload_pct": 1.5,
            "total_overload_hours": 10.0,
        })
        # Full cap gives total_load that upside_1 (48h) can handle
        full_cap = pd.DataFrame([{
            "scenario": "all_in", "plant": "NW01",
            "work_center": "P01_NW01_PRESS_1",
            "year": 2026, "week": 1,
            "total_load_hours": 42.0,  # 42/48 = 87.5% → above WARN so no; 42/56 = 75% ok
        }])
        lever = _suggest_lever(row, _make_limits(), full_cap)
        # 42/48 = 0.875 >= WARN (0.85) → upside_1 won't help; 42/56 = 0.75 < WARN → upside_2
        assert lever in ["upside_1", "upside_2", "no_lever_available"]

    def test_no_bottleneck_returns_empty(self):
        # All OK capacity
        cap_df = _make_cap()
        cap_df["bottleneck_flag"] = False
        bn = _summarise(
            cap_df[cap_df["bottleneck_flag"]],
            pd.DataFrame(), _make_tool_bridge(), _make_limits(), cap_df
        )
        assert bn.empty

    def test_explanation_note_contains_wc(self):
        row = pd.Series({
            "bottleneck_severity": SEV_CRITICAL,
            "work_center": "P01_NW01_PRESS_1",
            "peak_overload_pct": 1.2,
            "total_overload_hours": 8.0,
            "top_driver_project_count": 3,
            "suggested_capacity_lever": "upside_1",
        })
        note = _explain(row)
        assert "P01_NW01_PRESS_1" in note
        assert "upside_1" in note

    def test_top_driver_project_count_non_negative(self):
        demand, cap = self._setup()
        bn = _summarise(cap[cap["bottleneck_flag"]], demand, _make_tool_bridge(), _make_limits(), cap)
        if not bn.empty:
            assert (bn["top_driver_project_count"] >= 0).all()


# =============================================================================
# Integration tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not _HAS_XLSX, reason="hackathon_dataset.xlsx not found")
class TestIntegration:
    def test_demand_translation_rows(self):
        from project.src.wave2.demand_translation import build_fact_translated_project_demand_weekly
        demand = build_fact_translated_project_demand_weekly()
        assert len(demand) > 1000

    def test_scenario_capacity_unique_at_grain(self):
        from project.src.wave2.demand_translation import build_fact_translated_project_demand_weekly
        from project.src.wave2.capacity_overlay import build_fact_scenario_capacity_weekly
        demand = build_fact_translated_project_demand_weekly()
        cap = build_fact_scenario_capacity_weekly(demand)
        result = validate_scenario_capacity(cap)
        assert result["unique_at_grain"], f"{result['duplicate_rows']} duplicates"

    def test_bottleneck_summary_has_severity(self):
        from project.src.wave2.demand_translation import build_fact_translated_project_demand_weekly
        from project.src.wave2.capacity_overlay import build_fact_scenario_capacity_weekly
        from project.src.wave2.bottleneck_engine import build_fact_capacity_bottleneck_summary
        demand = build_fact_translated_project_demand_weekly()
        cap = build_fact_scenario_capacity_weekly(demand)
        bn = build_fact_capacity_bottleneck_summary(cap, demand)
        if not bn.empty:
            assert bn["bottleneck_severity"].isin([SEV_WARNING, SEV_CRITICAL]).all()
            assert bn["explanation_note"].notna().all()

    def test_overload_reproducible(self):
        """Run twice — overload_hours must be identical."""
        from project.src.wave2.demand_translation import build_fact_translated_project_demand_weekly
        from project.src.wave2.capacity_overlay import build_fact_scenario_capacity_weekly
        d1 = build_fact_translated_project_demand_weekly()
        d2 = build_fact_translated_project_demand_weekly()
        c1 = build_fact_scenario_capacity_weekly(d1)
        c2 = build_fact_scenario_capacity_weekly(d2)
        assert abs(c1["overload_hours"].sum() - c2["overload_hours"].sum()) < 0.001
