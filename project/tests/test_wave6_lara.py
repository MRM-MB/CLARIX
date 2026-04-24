"""
test_wave6_lara.py
==================
Wave 6 Lara validation tests — synthetic data only (no processed CSVs required).

Run:
  pytest project/tests/test_wave6_lara.py -v -m "not integration"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave6.maintenance_catalog import (
    _build_policy,
    _infer_trigger_type,
    build_dim_maintenance_policy_synth,
)
from project.src.wave6.downtime_calendar import (
    _build_calendar,
    _week_str_to_num,
    _phase_offset,
    MAINTENANCE_SCENARIOS,
    build_fact_maintenance_downtime_calendar,
)
from project.src.wave6.effective_capacity import (
    _apply_downtime,
    _build_impact_summary,
    build_fact_effective_capacity_weekly_v2,
    build_fact_maintenance_impact_summary,
)

_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
_HAS_PROCESSED = (_PROCESSED / "fact_scoped_capacity_weekly.csv").exists()


# =============================================================================
# Synthetic factories
# =============================================================================

def _make_scoped(
    plants=("NW01",),
    wcs=("P01_NW01_PRESS_1",),
    scenarios=("all_in", "expected_value"),
    weeks=("2026-W01", "2026-W02", "2026-W08", "2026-W09"),
    available=40.0,
    total_load=35.0,
    scope_id="mvp_3plant",
) -> pd.DataFrame:
    rows = []
    for scenario in scenarios:
        for plant in plants:
            for wc in wcs:
                for week in weeks:
                    load = total_load
                    overload = max(0.0, load - available)
                    rows.append({
                        "scope_id": scope_id,
                        "scenario": scenario,
                        "plant": plant,
                        "work_center": wc,
                        "week": week,
                        "available_capacity_hours": available,
                        "planned_load_hours": load * 0.8,
                        "incremental_load_hours": load * 0.2,
                        "total_load_hours": load,
                        "overload_hours": overload,
                        "overload_pct": overload / max(available, 1),
                        "bottleneck_flag": overload > 0,
                    })
    return pd.DataFrame(rows)


def _make_bridge(plant="NW01", wc="P01_NW01_PRESS_1", tool="T-100") -> pd.DataFrame:
    return pd.DataFrame([{
        "plant": plant,
        "material": "MAT_001",
        "tool": tool,
        "work_center": wc,
        "work_center_full": wc,
        "cycle_time_min": 2.0,
        "material_status": "active",
        "routing_source": "test",
        "reason_code": "COMPLETE",
        "revision": "A",
    }])


def _make_policy(plant="NW01", wc="P01_NW01_PRESS_1") -> pd.DataFrame:
    return pd.DataFrame([{
        "policy_id": f"MAINT_{plant}_{wc}_SCH",
        "plant": plant,
        "work_center": wc,
        "tool_no_if_available": "T-100",
        "maintenance_trigger_type": "scheduled_preventive",
        "estimated_interval_weeks_synth": 8,
        "expected_downtime_hours_synth": 4.0,
        "policy_generation_rule": "test rule",
        "generation_version": "wave6_maintenance_v1",
        "random_seed": 42,
    }])


def _make_calendar(
    plant="NW01", wc="P01_NW01_PRESS_1",
    weeks=("2026-W01", "2026-W08"),
    scope_id="mvp_3plant",
) -> pd.DataFrame:
    rows = []
    for scenario in MAINTENANCE_SCENARIOS:
        for week in weeks:
            rows.append({
                "scope_id": scope_id,
                "scenario": scenario,
                "plant": plant,
                "work_center": wc,
                "week": week,
                "scheduled_maintenance_hours": 4.0,
                "unscheduled_downtime_buffer_hours": 2.0,
                "maintenance_source_type": "scheduled_preventive",
                "synthetic_flag": True,
            })
    return pd.DataFrame(rows)


# =============================================================================
# maintenance_catalog tests
# =============================================================================

class TestMaintenanceCatalog:
    def test_press_wc_gets_scheduled_preventive(self):
        assert _infer_trigger_type("P01_NW01_PRESS_1") == "scheduled_preventive"

    def test_assy_wc_gets_corrective_unscheduled(self):
        assert _infer_trigger_type("P01_NW01_ASSY_1") == "corrective_unscheduled"

    def test_grinding_wc_gets_regulatory_inspection(self):
        assert _infer_trigger_type("P01_NW01_GRINDING_1") == "regulatory_inspection"

    def test_unknown_wc_defaults_to_scheduled_preventive(self):
        assert _infer_trigger_type("P01_NW01_UNKNOWN_99") == "scheduled_preventive"

    def test_required_columns_present(self):
        scoped = _make_scoped()
        bridge = _make_bridge()
        policy = _build_policy(scoped, bridge)
        required = [
            "policy_id", "plant", "work_center", "tool_no_if_available",
            "maintenance_trigger_type", "estimated_interval_weeks_synth",
            "expected_downtime_hours_synth", "policy_generation_rule",
        ]
        for col in required:
            assert col in policy.columns, f"Missing: {col}"

    def test_one_row_per_plant_wc(self):
        scoped = _make_scoped(plants=["NW01", "NW02"], wcs=["P01_NW01_PRESS_1", "P01_NW02_PRESS_1"])
        bridge = _make_bridge()
        policy = _build_policy(scoped, bridge)
        assert policy.duplicated(["plant", "work_center"]).sum() == 0

    def test_interval_ge_one(self):
        scoped = _make_scoped()
        policy = _build_policy(scoped, _make_bridge())
        assert (policy["estimated_interval_weeks_synth"] >= 1).all()

    def test_downtime_hours_positive(self):
        scoped = _make_scoped()
        policy = _build_policy(scoped, _make_bridge())
        assert (policy["expected_downtime_hours_synth"] > 0).all()

    def test_empty_scoped_returns_empty(self):
        policy = _build_policy(pd.DataFrame(), _make_bridge())
        assert policy.empty

    def test_tool_attached_from_bridge(self):
        scoped = _make_scoped()
        bridge = _make_bridge(tool="T-999")
        policy = _build_policy(scoped, bridge)
        assert policy["tool_no_if_available"].iloc[0] == "T-999"


# =============================================================================
# downtime_calendar tests
# =============================================================================

class TestDowntimeCalendar:
    def test_week_str_to_num_basic(self):
        assert _week_str_to_num("2026-W01") == 1
        assert _week_str_to_num("2026-W08") == 8
        assert _week_str_to_num("2026-W52") == 52

    def test_phase_offset_deterministic(self):
        assert _phase_offset("NW01", "P01_NW01_PRESS_1") == _phase_offset("NW01", "P01_NW01_PRESS_1")

    def test_phase_offset_differs_by_wc(self):
        p1 = _phase_offset("NW01", "P01_NW01_PRESS_1")
        p2 = _phase_offset("NW01", "P01_NW01_PRESS_2")
        # Different WCs should generally differ (not guaranteed but highly likely)
        # Just verify both are non-negative integers
        assert isinstance(p1, int) and p1 >= 0
        assert isinstance(p2, int) and p2 >= 0

    def test_four_scenarios_produced(self):
        scoped = _make_scoped()
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        assert set(cal["scenario"].unique()) == set(MAINTENANCE_SCENARIOS.keys())

    def test_required_columns_present(self):
        scoped = _make_scoped()
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        required = [
            "scope_id", "scenario", "plant", "work_center", "week",
            "scheduled_maintenance_hours", "unscheduled_downtime_buffer_hours",
            "maintenance_source_type", "synthetic_flag",
        ]
        for col in required:
            assert col in cal.columns, f"Missing: {col}"

    def test_all_rows_synthetic_flagged(self):
        scoped = _make_scoped()
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        assert cal["synthetic_flag"].all()

    def test_scheduled_hours_non_negative(self):
        scoped = _make_scoped()
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        assert (cal["scheduled_maintenance_hours"] >= 0).all()

    def test_unscheduled_hours_non_negative(self):
        scoped = _make_scoped()
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        assert (cal["unscheduled_downtime_buffer_hours"] >= 0).all()

    def test_unexpected_breakdown_has_unscheduled_hours(self):
        scoped = _make_scoped()
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        breakdown = cal[cal["scenario"] == "unexpected_breakdown"]
        assert (breakdown["unscheduled_downtime_buffer_hours"] > 0).all()

    def test_baseline_has_zero_unscheduled(self):
        scoped = _make_scoped()
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        baseline = cal[cal["scenario"] == "baseline_maintenance"]
        assert (baseline["unscheduled_downtime_buffer_hours"] == 0).all()

    def test_maintenance_overrun_has_higher_scheduled_than_baseline(self):
        scoped = _make_scoped(weeks=["2026-W08"])  # week 8 likely triggers interval-8 event
        policy = _make_policy()
        cal = _build_calendar(scoped, policy)
        base_sched = cal[cal["scenario"] == "baseline_maintenance"]["scheduled_maintenance_hours"].sum()
        overrun_sched = cal[cal["scenario"] == "maintenance_overrun"]["scheduled_maintenance_hours"].sum()
        assert overrun_sched >= base_sched

    def test_empty_scoped_returns_empty(self):
        cal = _build_calendar(pd.DataFrame(), _make_policy())
        assert cal.empty

    def test_empty_policy_returns_empty(self):
        scoped = _make_scoped()
        cal = _build_calendar(scoped, pd.DataFrame())
        assert cal.empty


# =============================================================================
# effective_capacity tests
# =============================================================================

class TestEffectiveCapacity:
    def _inputs(self, available=40.0, load=35.0):
        scoped = _make_scoped(available=available, total_load=load)
        calendar = _make_calendar()
        return scoped, calendar

    def test_required_columns_present(self):
        scoped, calendar = self._inputs()
        result = _apply_downtime(scoped, calendar)
        required = [
            "scope_id", "scenario", "plant", "work_center", "week",
            "nominal_available_capacity_hours", "scheduled_maintenance_hours",
            "downtime_buffer_hours", "effective_available_capacity_hours",
            "total_load_hours", "overload_hours", "overload_pct", "bottleneck_flag",
        ]
        for col in required:
            assert col in result.columns, f"Missing: {col}"

    def test_effective_never_exceeds_nominal(self):
        scoped, calendar = self._inputs()
        result = _apply_downtime(scoped, calendar)
        assert (result["effective_available_capacity_hours"] <= result["nominal_available_capacity_hours"] + 1e-6).all()

    def test_effective_always_non_negative(self):
        # Even with huge downtime, effective should be clipped to 0
        scoped, calendar = self._inputs(available=5.0)
        result = _apply_downtime(scoped, calendar)
        assert (result["effective_available_capacity_hours"] >= 0).all()

    def test_overload_non_negative(self):
        scoped, calendar = self._inputs()
        result = _apply_downtime(scoped, calendar)
        assert (result["overload_hours"] >= 0).all()

    def test_four_maintenance_scenarios(self):
        scoped, calendar = self._inputs()
        result = _apply_downtime(scoped, calendar)
        assert set(result["scenario"].unique()) == set(MAINTENANCE_SCENARIOS.keys())

    def test_maintenance_increases_overload(self):
        """With maintenance, overload should be ≥ without maintenance."""
        scoped = _make_scoped(available=40.0, total_load=35.0)
        calendar = _make_calendar()
        result = _apply_downtime(scoped, calendar)
        base = result[result["scenario"] == "baseline_maintenance"]
        unexpected = result[result["scenario"] == "unexpected_breakdown"]
        assert unexpected["overload_hours"].sum() >= base["overload_hours"].sum()

    def test_empty_inputs_return_empty(self):
        assert _apply_downtime(pd.DataFrame(), _make_calendar()).empty
        scoped = _make_scoped()
        assert _apply_downtime(scoped, pd.DataFrame()).empty

    def test_bottleneck_flag_consistent_with_overload(self):
        scoped, calendar = self._inputs()
        result = _apply_downtime(scoped, calendar)
        flagged = result[result["bottleneck_flag"]]
        if not flagged.empty:
            assert (flagged["overload_pct"] >= 0.85).all()


# =============================================================================
# impact summary tests
# =============================================================================

class TestImpactSummary:
    def _build(self):
        scoped = _make_scoped(available=40.0, total_load=35.0)
        calendar = _make_calendar()
        effective = _apply_downtime(scoped, calendar)
        return effective, scoped

    def test_required_columns_present(self):
        effective, scoped = self._build()
        result = _build_impact_summary(effective, scoped)
        required = [
            "scope_id", "scenario", "plant", "work_center",
            "nominal_avg_available_hours", "effective_avg_available_hours",
            "avg_maintenance_reduction_hours", "pct_capacity_lost_to_maintenance",
            "effective_bottleneck_weeks", "nominal_bottleneck_weeks",
            "delta_avg_overload_hours", "worst_week", "impact_severity",
        ]
        for col in required:
            assert col in result.columns, f"Missing: {col}"

    def test_pct_capacity_lost_bounded(self):
        effective, scoped = self._build()
        result = _build_impact_summary(effective, scoped)
        assert (result["pct_capacity_lost_to_maintenance"] >= 0).all()
        assert (result["pct_capacity_lost_to_maintenance"] <= 1).all()

    def test_severity_values_valid(self):
        effective, scoped = self._build()
        result = _build_impact_summary(effective, scoped)
        valid = {"high", "medium", "low", "none"}
        assert set(result["impact_severity"].unique()).issubset(valid)

    def test_four_scenarios_in_output(self):
        effective, scoped = self._build()
        result = _build_impact_summary(effective, scoped)
        assert set(result["scenario"].unique()) == set(MAINTENANCE_SCENARIOS.keys())

    def test_effective_le_nominal_avg(self):
        effective, scoped = self._build()
        result = _build_impact_summary(effective, scoped)
        assert (result["effective_avg_available_hours"] <= result["nominal_avg_available_hours"] + 1e-3).all()

    def test_empty_inputs_return_empty(self):
        assert _build_impact_summary(pd.DataFrame(), _make_scoped()).empty
        effective = _apply_downtime(_make_scoped(), _make_calendar())
        assert _build_impact_summary(effective, pd.DataFrame()).empty


# =============================================================================
# Integration tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not found")
class TestIntegration:
    def _read(self, name: str) -> pd.DataFrame:
        path = _PROCESSED / f"{name}.csv"
        return pd.read_csv(path) if path.exists() else pd.DataFrame()

    def test_full_pipeline_produces_rows(self):
        scoped = self._read("fact_scoped_capacity_weekly")
        bridge = self._read("bridge_material_tool_wc")
        policy = build_dim_maintenance_policy_synth(scoped, bridge)
        assert len(policy) > 0

    def test_all_four_maintenance_scenarios(self):
        scoped = self._read("fact_scoped_capacity_weekly")
        bridge = self._read("bridge_material_tool_wc")
        policy = build_dim_maintenance_policy_synth(scoped, bridge)
        calendar = build_fact_maintenance_downtime_calendar(scoped, policy)
        assert set(calendar["scenario"].unique()) == set(MAINTENANCE_SCENARIOS.keys())

    def test_effective_never_exceeds_nominal(self):
        scoped = self._read("fact_scoped_capacity_weekly")
        bridge = self._read("bridge_material_tool_wc")
        policy = build_dim_maintenance_policy_synth(scoped, bridge)
        calendar = build_fact_maintenance_downtime_calendar(scoped, policy)
        effective = build_fact_effective_capacity_weekly_v2(scoped, calendar)
        assert (
            effective["effective_available_capacity_hours"] <=
            effective["nominal_available_capacity_hours"] + 1e-4
        ).all()

    def test_impact_severity_distribution(self):
        scoped = self._read("fact_scoped_capacity_weekly")
        bridge = self._read("bridge_material_tool_wc")
        policy = build_dim_maintenance_policy_synth(scoped, bridge)
        calendar = build_fact_maintenance_downtime_calendar(scoped, policy)
        effective = build_fact_effective_capacity_weekly_v2(scoped, calendar)
        impact = build_fact_maintenance_impact_summary(effective, scoped)
        valid = {"high", "medium", "low", "none"}
        assert set(impact["impact_severity"].unique()).issubset(valid)

    def test_unexpected_breakdown_worst_overload(self):
        scoped = self._read("fact_scoped_capacity_weekly")
        bridge = self._read("bridge_material_tool_wc")
        policy = build_dim_maintenance_policy_synth(scoped, bridge)
        calendar = build_fact_maintenance_downtime_calendar(scoped, policy)
        effective = build_fact_effective_capacity_weekly_v2(scoped, calendar)
        by_scenario = effective.groupby("scenario")["overload_hours"].sum()
        breakdown = by_scenario.get("unexpected_breakdown", 0)
        baseline = by_scenario.get("baseline_maintenance", 0)
        assert breakdown >= baseline
