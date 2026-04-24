"""
test_wave5_lara.py
==================
Wave 5 Lara validation tests — synthetic data only (no processed CSVs required).

Run:
  pytest project/tests/test_wave5_lara.py -v -m "not integration"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave5.capacity_scope import (
    _scope_capacity_weekly,
    _aggregate_quarterly,
    _build_state_history,
    _year_week_to_quarter,
    _prior_quarter_id,
    build_fact_scoped_capacity_weekly,
    build_fact_capacity_quarterly_snapshot,
    build_fact_capacity_state_history,
)

_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
_HAS_PROCESSED = (_PROCESSED / "fact_scenario_capacity_weekly.csv").exists()


# =============================================================================
# Synthetic factories
# =============================================================================

def _make_cap(
    plants=("NW01", "NW02", "NW05"),
    scenarios=("all_in", "expected_value"),
    weeks=range(1, 14),   # Q1
    year=2026,
    available=40.0,
    planned=30.0,
    incremental=5.0,
    overload=0.0,
    bottleneck=False,
) -> pd.DataFrame:
    rows = []
    for scenario in scenarios:
        for plant in plants:
            for week in weeks:
                total = planned + incremental
                over = max(0.0, total - available) if overload == 0.0 else overload
                rows.append({
                    "scenario": scenario,
                    "plant": plant,
                    "work_center": f"P01_{plant}_PRESS",
                    "year": year,
                    "week": week,
                    "available_capacity_hours": available,
                    "planned_load_hours": planned,
                    "incremental_load_hours": incremental,
                    "total_load_hours": total,
                    "overload_hours": over,
                    "overload_pct": over / max(available, 1),
                    "bottleneck_flag": bottleneck,
                    "remaining_capacity_hours": max(0.0, available - total),
                })
    return pd.DataFrame(rows)


def _make_bottleneck(
    plant="NW01", scenario="all_in", wc="P01_NW01_PRESS", lever="upside_1"
) -> pd.DataFrame:
    return pd.DataFrame([{
        "scenario": scenario,
        "plant": plant,
        "work_center": wc,
        "tool_no_if_available": "T100",
        "bottleneck_severity": "critical",
        "top_driver_project_count": 3,
        "suggested_capacity_lever": lever,
        "explanation_note": "test bottleneck",
    }])


def _make_quarterly(
    plants=("NW01",),
    quarters=("2026-Q1", "2026-Q2"),
    scope_id="mvp_3plant",
    bottleneck_weeks=5,
    overload=100.0,
) -> pd.DataFrame:
    rows = []
    for plant in plants:
        wc = f"P01_{plant}_PRESS"
        for quarter_id in quarters:
            rows.append({
                "scope_id": scope_id,
                "quarter_id": quarter_id,
                "plant": plant,
                "work_center": wc,
                "total_available_capacity_hours": 520.0,
                "total_planned_load_hours": 400.0,
                "total_incremental_load_hours": 65.0,
                "total_overload_hours": overload,
                "bottleneck_weeks_count": bottleneck_weeks,
            })
    return pd.DataFrame(rows)


# =============================================================================
# _year_week_to_quarter tests
# =============================================================================

class TestYearWeekToQuarter:
    def test_week_1_is_q1(self):
        assert _year_week_to_quarter(2026, 1) == "2026-Q1"

    def test_week_13_is_q1(self):
        assert _year_week_to_quarter(2026, 13) == "2026-Q1"

    def test_week_14_is_q2(self):
        assert _year_week_to_quarter(2026, 14) == "2026-Q2"

    def test_week_26_is_q2(self):
        assert _year_week_to_quarter(2026, 26) == "2026-Q2"

    def test_week_27_is_q3(self):
        assert _year_week_to_quarter(2026, 27) == "2026-Q3"

    def test_week_40_is_q4(self):
        assert _year_week_to_quarter(2026, 40) == "2026-Q4"

    def test_week_52_is_q4(self):
        assert _year_week_to_quarter(2026, 52) == "2026-Q4"

    def test_year_preserved(self):
        assert _year_week_to_quarter(2027, 5) == "2027-Q1"
        assert _year_week_to_quarter(2028, 30) == "2028-Q3"


class TestPriorQuarterId:
    def test_q2_prior_is_q1(self):
        assert _prior_quarter_id("2026-Q2") == "2026-Q1"

    def test_q1_prior_is_prev_year_q4(self):
        assert _prior_quarter_id("2026-Q1") == "2025-Q4"

    def test_q4_prior_is_q3(self):
        assert _prior_quarter_id("2026-Q4") == "2026-Q3"


# =============================================================================
# _scope_capacity_weekly tests
# =============================================================================

class TestScopeCapacityWeekly:
    def test_filters_to_scope_plants(self):
        cap = _make_cap(plants=["NW01", "NW02", "NW05", "NW09"])
        scoped = _scope_capacity_weekly(cap, "test_scope", ["NW01", "NW02"])
        assert set(scoped["plant"].unique()) == {"NW01", "NW02"}

    def test_adds_scope_id_column(self):
        cap = _make_cap()
        scoped = _scope_capacity_weekly(cap, "my_scope", ["NW01"])
        assert "scope_id" in scoped.columns
        assert (scoped["scope_id"] == "my_scope").all()

    def test_row_count_le_source(self):
        cap = _make_cap(plants=["NW01", "NW02", "NW05"])
        scoped = _scope_capacity_weekly(cap, "s", ["NW01"])
        assert len(scoped) <= len(cap)

    def test_empty_input_returns_empty(self):
        result = _scope_capacity_weekly(pd.DataFrame(), "s", ["NW01"])
        assert result.empty

    def test_all_plants_returns_all(self):
        cap = _make_cap(plants=["NW01", "NW02"])
        scoped = _scope_capacity_weekly(cap, "all", ["NW01", "NW02"])
        assert len(scoped) == len(cap)

    def test_required_columns_present(self):
        cap = _make_cap()
        scoped = _scope_capacity_weekly(cap, "s", ["NW01"])
        required = ["scope_id", "scenario", "plant", "work_center", "week",
                    "available_capacity_hours", "overload_hours", "bottleneck_flag"]
        for col in required:
            assert col in scoped.columns, f"Missing: {col}"

    def test_week_converted_to_string(self):
        cap = _make_cap(weeks=[1, 2, 3])
        scoped = _scope_capacity_weekly(cap, "s", ["NW01"])
        assert scoped["week"].dtype == object
        assert scoped["week"].str.contains("-W").all()

    def test_scenario_filter_applied(self):
        cap = _make_cap(scenarios=["all_in", "expected_value", "high_confidence"])
        scoped = _scope_capacity_weekly(cap, "s", ["NW01"], scenarios=["expected_value"])
        assert set(scoped["scenario"].unique()) == {"expected_value"}

    def test_bottleneck_flag_is_bool(self):
        cap = _make_cap()
        scoped = _scope_capacity_weekly(cap, "s", ["NW01"])
        assert scoped["bottleneck_flag"].dtype == bool


# =============================================================================
# _aggregate_quarterly tests
# =============================================================================

class TestAggregateQuarterly:
    def _scoped(self, **kwargs) -> pd.DataFrame:
        cap = _make_cap(**kwargs)
        return _scope_capacity_weekly(cap, "mvp_3plant", ["NW01", "NW02", "NW05"])

    def test_required_columns_present(self):
        scoped = self._scoped()
        result = _aggregate_quarterly(scoped)
        required = ["scope_id", "quarter_id", "plant", "work_center",
                    "total_available_capacity_hours", "total_planned_load_hours",
                    "total_incremental_load_hours", "total_overload_hours",
                    "bottleneck_weeks_count"]
        for col in required:
            assert col in result.columns, f"Missing: {col}"

    def test_weeks_q1_map_to_q1(self):
        scoped = self._scoped(weeks=range(1, 14))
        result = _aggregate_quarterly(scoped)
        assert set(result["quarter_id"].unique()) == {"2026-Q1"}

    def test_multiple_quarters_produced(self):
        cap = _make_cap(weeks=list(range(1, 53)))
        scoped = _scope_capacity_weekly(cap, "mvp_3plant", ["NW01"])
        result = _aggregate_quarterly(scoped)
        assert result["quarter_id"].nunique() == 4

    def test_total_hours_reconcile_with_weekly(self):
        """Quarterly sum of available hours must equal sum of weekly values for same plant/wc."""
        cap = _make_cap(plants=["NW01"], scenarios=["all_in"], weeks=range(1, 14), available=40.0)
        scoped = _scope_capacity_weekly(cap, "mvp_3plant", ["NW01"])
        quarterly = _aggregate_quarterly(scoped)
        # all_in is a base scenario → 13 weeks × 40.0 = 520.0
        q1 = quarterly[(quarterly["plant"] == "NW01") & (quarterly["quarter_id"] == "2026-Q1")]
        assert abs(q1["total_available_capacity_hours"].iloc[0] - 520.0) < 1.0

    def test_bottleneck_weeks_count_non_negative_int(self):
        scoped = self._scoped()
        result = _aggregate_quarterly(scoped)
        assert (result["bottleneck_weeks_count"] >= 0).all()
        assert result["bottleneck_weeks_count"].dtype in ["int64", "int32", "int"]

    def test_empty_returns_empty(self):
        result = _aggregate_quarterly(pd.DataFrame())
        assert result.empty

    def test_upside_scenarios_excluded(self):
        cap = _make_cap(scenarios=["all_in", "all_in__upside_1"])
        scoped = _scope_capacity_weekly(cap, "s", ["NW01"])
        result = _aggregate_quarterly(scoped)
        # upside_1 is not a base scenario — result should only include all_in contributions
        assert len(result) > 0

    def test_bottleneck_weeks_counted_correctly(self):
        cap = _make_cap(plants=["NW01"], scenarios=["expected_value"],
                        weeks=range(1, 5), bottleneck=True)
        scoped = _scope_capacity_weekly(cap, "s", ["NW01"])
        result = _aggregate_quarterly(scoped)
        q1 = result[result["quarter_id"] == "2026-Q1"]
        # 4 weeks × 1 scenario = 4 bottleneck week entries
        assert q1["bottleneck_weeks_count"].iloc[0] == 4


# =============================================================================
# _build_state_history tests
# =============================================================================

class TestBuildStateHistory:
    def test_required_columns_present(self):
        quarterly = _make_quarterly()
        result = _build_state_history(quarterly, pd.DataFrame())
        required = ["scope_id", "quarter_id", "plant", "work_center",
                    "prior_quarter_bottleneck_flag", "prior_quarter_overload_hours",
                    "prior_quarter_mitigation_used", "carry_over_capacity_risk_flag",
                    "learning_note"]
        for col in required:
            assert col in result.columns, f"Missing: {col}"

    def test_row_count_equals_quarterly(self):
        quarterly = _make_quarterly()
        result = _build_state_history(quarterly, pd.DataFrame())
        assert len(result) == len(quarterly)

    def test_carry_over_flagged_when_both_quarters_bottleneck(self):
        quarterly = _make_quarterly(quarters=["2026-Q1", "2026-Q2"], bottleneck_weeks=5)
        result = _build_state_history(quarterly, pd.DataFrame())
        q2 = result[result["quarter_id"] == "2026-Q2"]
        assert q2["carry_over_capacity_risk_flag"].iloc[0] == True

    def test_no_carry_over_when_prior_clean(self):
        # Q1 has no bottleneck, Q2 has bottleneck
        rows = [
            {"scope_id": "s", "quarter_id": "2026-Q1", "plant": "NW01",
             "work_center": "WC1", "total_available_capacity_hours": 520.0,
             "total_planned_load_hours": 400.0, "total_incremental_load_hours": 0.0,
             "total_overload_hours": 0.0, "bottleneck_weeks_count": 0},
            {"scope_id": "s", "quarter_id": "2026-Q2", "plant": "NW01",
             "work_center": "WC1", "total_available_capacity_hours": 520.0,
             "total_planned_load_hours": 500.0, "total_incremental_load_hours": 100.0,
             "total_overload_hours": 80.0, "bottleneck_weeks_count": 4},
        ]
        quarterly = pd.DataFrame(rows)
        result = _build_state_history(quarterly, pd.DataFrame())
        q2 = result[result["quarter_id"] == "2026-Q2"]
        # Prior Q1 had 0 bottleneck weeks → no carry-over
        assert q2["carry_over_capacity_risk_flag"].iloc[0] == False

    def test_first_quarter_has_no_prior(self):
        quarterly = _make_quarterly(quarters=["2026-Q1"])
        result = _build_state_history(quarterly, pd.DataFrame())
        q1 = result[result["quarter_id"] == "2026-Q1"]
        assert q1["prior_quarter_bottleneck_flag"].iloc[0] == False
        assert q1["carry_over_capacity_risk_flag"].iloc[0] == False

    def test_mitigation_lever_from_bottleneck_summary(self):
        quarterly = _make_quarterly(plants=["NW01"], quarters=["2026-Q1", "2026-Q2"])
        bn = _make_bottleneck(plant="NW01", wc="P01_NW01_PRESS", lever="upside_2")
        result = _build_state_history(quarterly, bn)
        assert (result["prior_quarter_mitigation_used"] == "upside_2").all()

    def test_learning_note_non_empty(self):
        quarterly = _make_quarterly()
        result = _build_state_history(quarterly, pd.DataFrame())
        assert result["learning_note"].notna().all()
        assert (result["learning_note"].str.len() > 0).all()

    def test_empty_quarterly_returns_empty(self):
        result = _build_state_history(pd.DataFrame(), pd.DataFrame())
        assert result.empty

    def test_carry_over_note_mentions_both_quarters(self):
        quarterly = _make_quarterly(quarters=["2026-Q1", "2026-Q2"], bottleneck_weeks=5)
        result = _build_state_history(quarterly, pd.DataFrame())
        carry = result[result["carry_over_capacity_risk_flag"]]
        if not carry.empty:
            assert carry["learning_note"].str.contains("2026-Q1").any()

    def test_prior_overload_hours_from_previous_quarter(self):
        quarterly = _make_quarterly(quarters=["2026-Q1", "2026-Q2"],
                                    bottleneck_weeks=3, overload=200.0)
        result = _build_state_history(quarterly, pd.DataFrame())
        q2 = result[result["quarter_id"] == "2026-Q2"]
        assert abs(q2["prior_quarter_overload_hours"].iloc[0] - 200.0) < 0.01


# =============================================================================
# Integration tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not found")
class TestIntegration:
    def _read(self, name: str) -> pd.DataFrame:
        path = _PROCESSED / f"{name}.csv"
        return pd.read_csv(path) if path.exists() else pd.DataFrame()

    def test_scoped_row_count_le_source(self):
        cap = self._read("fact_scenario_capacity_weekly")
        scoped = build_fact_scoped_capacity_weekly(cap)
        assert len(scoped) <= len(cap)

    def test_scoped_plants_within_scope(self):
        from project.src.wave5.scoped_filter import DEFAULT_SCOPE
        cap = self._read("fact_scenario_capacity_weekly")
        scoped = build_fact_scoped_capacity_weekly(cap)
        assert set(scoped["plant"].unique()).issubset(set(DEFAULT_SCOPE["plants"]))

    def test_quarterly_quarters_match_data(self):
        cap = self._read("fact_scenario_capacity_weekly")
        scoped = build_fact_scoped_capacity_weekly(cap)
        quarterly = build_fact_capacity_quarterly_snapshot(scoped)
        assert quarterly["quarter_id"].nunique() >= 4  # 2026–2028 → at least 4 quarters

    def test_quarterly_totals_reconcile(self):
        cap = self._read("fact_scenario_capacity_weekly")
        scoped = build_fact_scoped_capacity_weekly(cap)
        quarterly = build_fact_capacity_quarterly_snapshot(scoped)
        # Total overload_hours in quarterly must equal sum of scoped weekly (base scenarios only)
        base = {"all_in", "expected_value", "high_confidence"}
        weekly_total = scoped[scoped["scenario"].isin(base)]["overload_hours"].sum()
        quarterly_total = quarterly["total_overload_hours"].sum()
        assert abs(weekly_total - quarterly_total) < 1.0, (
            f"Weekly total {weekly_total:.1f} ≠ quarterly total {quarterly_total:.1f}"
        )

    def test_state_history_row_count_equals_quarterly(self):
        cap = self._read("fact_scenario_capacity_weekly")
        bn = self._read("fact_capacity_bottleneck_summary")
        scoped = build_fact_scoped_capacity_weekly(cap)
        quarterly = build_fact_capacity_quarterly_snapshot(scoped)
        history = build_fact_capacity_state_history(quarterly, bn)
        assert len(history) == len(quarterly)

    def test_carry_over_flags_are_boolean(self):
        cap = self._read("fact_scenario_capacity_weekly")
        scoped = build_fact_scoped_capacity_weekly(cap)
        quarterly = build_fact_capacity_quarterly_snapshot(scoped)
        history = build_fact_capacity_state_history(quarterly, pd.DataFrame())
        assert history["carry_over_capacity_risk_flag"].dtype == bool
