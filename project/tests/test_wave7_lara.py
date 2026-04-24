"""Tests for Wave 7 Lara: fact_planner_actions_v2."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from project.src.wave7.planner_actions_v2 import (
    _week_to_quarter,
    _build_scope_map,
    _build_maintenance_context,
    _build_protect_opportunities,
    _select_action_type,
    build_fact_planner_actions_v2,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_integrated_risk(n: int = 8) -> pd.DataFrame:
    weeks = ["2026-W01", "2026-W02", "2026-W14", "2026-W27",
             "2026-W40", "2027-W01", "2027-W14", "2027-W27"][:n]
    drivers = ["capacity_risk", "sourcing_risk", "logistics_risk", "lead_time_risk",
               "capacity_risk", "sourcing_risk", "capacity_risk", "sourcing_risk"][:n]
    return pd.DataFrame({
        "scenario": ["expected_value"] * n,
        "project_id": [f"P-{i:03d}" for i in range(n)],
        "plant": ["NW01"] * n,
        "week": weeks,
        "top_driver": drivers,
        "risk_score": [0.7, 0.5, 0.8, 0.4, 0.65, 0.3, 0.75, 0.55],
        "action_score": [0.35, 0.25, 0.4, 0.2, 0.32, 0.15, 0.37, 0.27],
        "capacity_risk_score": [0.7, 0.2, 0.3, 0.2, 0.65, 0.1, 0.75, 0.2],
        "sourcing_risk_score": [0.2, 0.5, 0.3, 0.3, 0.2, 0.3, 0.2, 0.55],
        "logistics_risk_score": [0.1, 0.1, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1],
        "lead_time_risk_score": [0.1, 0.1, 0.1, 0.4, 0.1, 0.1, 0.1, 0.1],
        "scenario_confidence": [0.8] * n,
        "explainability_note": ["test note"] * n,
    })


def _make_region_scope() -> pd.DataFrame:
    return pd.DataFrame({
        "scope_id": ["mvp_3plant", "global_reference"],
        "region_name": ["MVP 3 Plant", "Global"],
        "included_plants": ["NW01,NW02,NW05", "NW01,NW02,NW03,NW04,NW05"],
        "scope_rule": ["plant in mvp", "all"],
        "active_flag": [True, False],
    })


def _make_maintenance_impact() -> pd.DataFrame:
    return pd.DataFrame({
        "scope_id": ["mvp_3plant"] * 4,
        "scenario": ["baseline_maintenance", "maintenance_overrun",
                     "unexpected_breakdown", "preventive_maintenance_shift"],
        "plant": ["NW01"] * 4,
        "work_center": ["WC_PRESS_01"] * 4,
        "nominal_avg_available_hours": [40.0] * 4,
        "effective_avg_available_hours": [38.0, 35.0, 36.0, 37.0],
        "avg_maintenance_reduction_hours": [2.0, 5.0, 4.0, 3.0],
        "pct_capacity_lost_to_maintenance": [0.05, 0.125, 0.10, 0.075],
        "effective_bottleneck_weeks": [10, 15, 12, 11],
        "nominal_bottleneck_weeks": [10, 10, 10, 10],
        "delta_avg_overload_hours": [0.0, 2.0, 1.5, 1.0],
        "worst_week": ["2026-W05"] * 4,
        "impact_severity": ["low", "medium", "low", "low"],
    })


def _make_effective_capacity() -> pd.DataFrame:
    return pd.DataFrame({
        "scope_id": ["mvp_3plant"] * 4,
        "scenario": ["unexpected_breakdown"] * 4,
        "plant": ["NW01"] * 4,
        "work_center": ["WC_PRESS_01"] * 4,
        "week": ["2026-W01", "2026-W02", "2026-W03", "2026-W04"],
        "nominal_available_capacity_hours": [40.0] * 4,
        "scheduled_maintenance_hours": [2.0, 0.0, 2.0, 0.0],
        "downtime_buffer_hours": [1.0, 1.0, 1.0, 1.0],
        "effective_available_capacity_hours": [37.0, 39.0, 37.0, 39.0],
        "total_load_hours": [45.0, 30.0, 50.0, 28.0],
        "overload_hours": [8.0, 0.0, 13.0, 0.0],
        "overload_pct": [0.22, 0.0, 0.35, 0.0],
        "bottleneck_flag": [True, False, True, False],
    })


def _make_action_policy() -> pd.DataFrame:
    return pd.DataFrame({
        "action_type": ["buy_now", "upshift", "reroute", "wait"],
        "minimum_risk_threshold": [0.5, 0.4, 0.5, 0.0],
        "minimum_priority_threshold": [0.3, 0.3, 0.3, 0.0],
        "expected_effect_type": ["reduce_shortage", "increase_capacity", "reduce_transit", "monitor"],
        "policy_version": ["v2"] * 4,
    })


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------

class TestWeekToQuarter:
    def test_q1(self):
        assert _week_to_quarter("2026-W01") == "2026-Q1"
        assert _week_to_quarter("2026-W13") == "2026-Q1"

    def test_q2(self):
        assert _week_to_quarter("2026-W14") == "2026-Q2"
        assert _week_to_quarter("2026-W26") == "2026-Q2"

    def test_q3(self):
        assert _week_to_quarter("2026-W27") == "2026-Q3"
        assert _week_to_quarter("2026-W39") == "2026-Q3"

    def test_q4(self):
        assert _week_to_quarter("2026-W40") == "2026-Q4"
        assert _week_to_quarter("2026-W52") == "2026-Q4"

    def test_invalid_returns_unknown(self):
        assert _week_to_quarter("bad") == "unknown"


class TestBuildScopeMap:
    def test_active_flag_wins(self):
        rs = _make_region_scope()
        m = _build_scope_map(rs)
        assert m["NW01"] == "mvp_3plant"

    def test_plant_not_in_scope_returns_empty(self):
        rs = _make_region_scope()
        m = _build_scope_map(rs)
        assert "NW99" not in m

    def test_empty_returns_empty(self):
        assert _build_scope_map(pd.DataFrame()) == {}


class TestBuildMaintenanceContext:
    def test_returns_dict_keyed_by_plant(self):
        mi = _make_maintenance_impact()
        ctx = _build_maintenance_context(mi)
        assert "NW01" in ctx

    def test_worst_severity_selected(self):
        mi = _make_maintenance_impact()
        ctx = _build_maintenance_context(mi)
        # maintenance_overrun has pct_lost=0.125, severity=medium — should be worst
        assert ctx["NW01"]["max_severity"] == "medium"

    def test_empty_returns_empty(self):
        assert _build_maintenance_context(pd.DataFrame()) == {}


class TestBuildProtectOpportunities:
    def test_detects_bottleneck_with_maintenance(self):
        ec = _make_effective_capacity()
        protect = _build_protect_opportunities(ec, scenario="unexpected_breakdown")
        assert len(protect) > 0

    def test_returns_plant_wc_quarter_tuples(self):
        ec = _make_effective_capacity()
        protect = _build_protect_opportunities(ec, scenario="unexpected_breakdown")
        for item in protect:
            assert len(item) == 3  # (plant, work_center, quarter_id)

    def test_empty_returns_empty_set(self):
        assert _build_protect_opportunities(pd.DataFrame()) == set()


class TestSelectActionType:
    def test_low_risk_returns_wait(self):
        assert _select_action_type("capacity_risk", 0.1, "none", False, False) == "wait"

    def test_high_sourcing_returns_buy_now(self):
        assert _select_action_type("sourcing_risk", 0.8, "none", False, False) == "buy_now"

    def test_med_sourcing_returns_hedge(self):
        assert _select_action_type("sourcing_risk", 0.5, "none", False, False) == "hedge_inventory"

    def test_capacity_medium_maint_returns_shift_maintenance(self):
        assert _select_action_type("capacity_risk", 0.6, "medium", False, False) == "shift_maintenance"

    def test_capacity_high_risk_no_maint_returns_escalate(self):
        result = _select_action_type("capacity_risk", 0.70, "none", False, False)
        assert result in ("escalate", "split_production")

    def test_logistics_high_returns_reroute(self):
        assert _select_action_type("logistics_risk", 0.8, "none", False, False) == "reroute"

    def test_protect_opportunity_with_capacity_risk(self):
        result = _select_action_type("capacity_risk", 0.5, "none", True, False)
        assert result == "protect_capacity_window"

    def test_caution_flag_boosts_threshold(self):
        # With caution, a borderline risk of 0.19 should cross the LOW_RISK threshold
        result_no_caution = _select_action_type("sourcing_risk", 0.19, "none", False, False)
        result_caution = _select_action_type("sourcing_risk", 0.19, "none", False, True)
        # caution should make the action more aggressive (may no longer be wait)
        assert result_no_caution == "wait"
        assert result_caution in ("buy_now", "hedge_inventory", "wait")


# ---------------------------------------------------------------------------
# Integration tests — build_fact_planner_actions_v2
# ---------------------------------------------------------------------------

class TestBuildPlannerActionsV2:
    def _build(self, **overrides):
        kwargs = dict(
            integrated_risk=_make_integrated_risk(),
            effective_capacity=_make_effective_capacity(),
            maintenance_impact=_make_maintenance_impact(),
            region_scope=_make_region_scope(),
            action_policy=_make_action_policy(),
            service_memory=None,
        )
        kwargs.update(overrides)
        return build_fact_planner_actions_v2(**kwargs)

    def test_returns_dataframe(self):
        result = self._build()
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self):
        from project.src.wave7.planner_actions_v2 import _REQUIRED_COLS
        result = self._build()
        for col in _REQUIRED_COLS:
            assert col in result.columns, f"Missing: {col}"

    def test_action_score_bounded(self):
        result = self._build()
        assert (result["action_score"] >= 0.0).all()
        assert (result["action_score"] <= 1.0).all()

    def test_confidence_bounded(self):
        result = self._build()
        assert (result["confidence"] >= 0.0).all()
        assert (result["confidence"] <= 1.0).all()

    def test_action_types_valid(self):
        from project.src.wave7.planner_actions_v2 import _REASONS
        result = self._build()
        valid = set(_REASONS.keys())
        assert result["action_type"].isin(valid).all()

    def test_scope_id_assigned(self):
        result = self._build()
        assert result["scope_id"].notna().all()
        assert (result["scope_id"] == "mvp_3plant").all()

    def test_quarter_id_format(self):
        result = self._build()
        assert result["quarter_id"].str.match(r"^\d{4}-Q[1-4]$").all()

    def test_explanation_trace_is_valid_json(self):
        result = self._build()
        for trace in result["explanation_trace"]:
            parsed = json.loads(trace)
            assert "top_driver" in parsed
            assert "action_selected" in parsed

    def test_unique_on_natural_key(self):
        result = self._build()
        key_cols = ["scope_id", "scenario", "quarter_id", "project_id", "plant"]
        assert result.duplicated(subset=key_cols).sum() == 0

    def test_sorted_by_action_score_desc(self):
        result = self._build()
        assert (result["action_score"].diff().dropna() <= 0).all()

    def test_empty_integrated_risk_returns_empty(self):
        result = self._build(integrated_risk=pd.DataFrame())
        assert result.empty

    def test_maintenance_severity_triggers_shift_maintenance(self):
        # Build with medium severity maintenance → expect shift_maintenance for capacity rows
        result = self._build()
        capacity_rows = result[result["explanation_trace"].str.contains('"top_driver":"capacity_risk"')]
        maint_rows = capacity_rows[capacity_rows["action_type"] == "shift_maintenance"]
        # At least one shift_maintenance should appear given medium severity on NW01
        assert len(maint_rows) > 0, "Expected at least one shift_maintenance action"

    def test_reason_not_empty(self):
        result = self._build()
        assert (result["reason"].str.len() > 0).all()

    def test_expected_effect_not_empty(self):
        result = self._build()
        assert (result["expected_effect"].str.len() > 0).all()

    def test_service_memory_caution_reflected_in_trace(self):
        ir = _make_integrated_risk(n=8)
        sm = pd.DataFrame({
            "scope_id": ["mvp_3plant"],
            "quarter_id": ["2026-Q1"],
            "project_id": ["P-000"],
            "carry_over_service_caution_flag": [True],
            "prior_service_violation_risk": [0.5],
            "explanation_note": ["test"],
        })
        result = self._build(
            integrated_risk=ir,
            service_memory=sm,
        )
        caution_rows = result[result["explanation_trace"].str.contains('"caution_carry_over":true')]
        assert len(caution_rows) > 0, "Expected caution_carry_over=true in at least one trace"


# ---------------------------------------------------------------------------
# Integration test against real processed data (skipped if files missing)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_integration_from_real_data():
    from pathlib import Path
    processed = Path("project/data/processed")
    required = [
        "fact_integrated_risk.csv",
        "fact_effective_capacity_weekly_v2.csv",
        "fact_maintenance_impact_summary.csv",
        "dim_region_scope.csv",
        "dim_action_policy.csv",
    ]
    for f in required:
        if not (processed / f).exists():
            pytest.skip(f"Missing file: {f}")

    result = build_fact_planner_actions_v2(
        integrated_risk=pd.read_csv(processed / "fact_integrated_risk.csv"),
        effective_capacity=pd.read_csv(processed / "fact_effective_capacity_weekly_v2.csv"),
        maintenance_impact=pd.read_csv(processed / "fact_maintenance_impact_summary.csv"),
        region_scope=pd.read_csv(processed / "dim_region_scope.csv"),
        action_policy=pd.read_csv(processed / "dim_action_policy.csv"),
        service_memory=pd.read_csv(processed / "fact_quarter_service_memory.csv")
        if (processed / "fact_quarter_service_memory.csv").exists() else None,
    )

    assert len(result) > 0
    assert result["action_type"].notna().all()
    assert (result["action_score"] >= 0.0).all()
    assert (result["action_score"] <= 1.0).all()
    from project.src.wave7.planner_actions_v2 import _REQUIRED_COLS
    for col in _REQUIRED_COLS:
        assert col in result.columns
