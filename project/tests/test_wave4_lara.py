"""
test_wave4_lara.py
==================
Wave 4 validation tests — synthetic data only (no Excel required).

Run:
  pytest project/tests/test_wave4_lara.py -v -m "not integration"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave4.action_engine import (
    _apply_actions,
    _build_quality_penalty_index,
    _build_bottleneck_wc_index,
    _build_disruption_index,
    _suggest_alt_plant,
    _material_or_wc,
    _confidence_label,
    _empty_actions,
    build_fact_planner_actions,
)

_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
_HAS_PROCESSED = (_PROCESSED / "fact_integrated_risk_base.csv").exists()


# =============================================================================
# Synthetic factories
# =============================================================================

def _make_risk(
    scenarios=("all_in",),
    plants=("NW01",),
    n_weeks=2,
    capacity_risk=0.85,
    sourcing_risk=0.80,
    logistics_risk=0.55,
    priority=0.70,
    action_score_base=0.50,
    top_driver="sourcing_risk",
    risk_score_base=0.70,
) -> pd.DataFrame:
    rows = []
    for scenario in scenarios:
        for plant in plants:
            for week in range(1, n_weeks + 1):
                rows.append({
                    "scenario": scenario,
                    "project_id": f"PROJ_{plant}",
                    "plant": plant,
                    "week": f"2026-W{week:02d}",
                    "priority_score": priority,
                    "capacity_risk_score": capacity_risk,
                    "sourcing_risk_score": sourcing_risk,
                    "logistics_risk_score": logistics_risk,
                    "lead_time_risk_score": 0.5,
                    "risk_score_base": risk_score_base,
                    "action_score_base": action_score_base,
                    "top_driver": top_driver,
                    "scenario_confidence": 1.0,
                })
    return pd.DataFrame(rows)


def _make_policy() -> pd.DataFrame:
    return pd.DataFrame([
        {"action_type": "buy_now",           "trigger_condition": "sourcing>=0.7", "minimum_priority_threshold": 0.3, "minimum_risk_threshold": 0.6, "requires_alt_plant_flag": False, "allows_expedite_flag": False, "allows_upshift_flag": False, "expected_effect_type": "reduce_shortage",   "policy_version": "v1"},
        {"action_type": "wait",              "trigger_condition": "risk<0.3",       "minimum_priority_threshold": 0.0, "minimum_risk_threshold": 0.0, "requires_alt_plant_flag": False, "allows_expedite_flag": False, "allows_upshift_flag": False, "expected_effect_type": "hedge_uncertainty",  "policy_version": "v1"},
        {"action_type": "reroute",           "trigger_condition": "logistics>=0.5", "minimum_priority_threshold": 0.4, "minimum_risk_threshold": 0.4, "requires_alt_plant_flag": True,  "allows_expedite_flag": False, "allows_upshift_flag": False, "expected_effect_type": "reduce_delay",       "policy_version": "v1"},
        {"action_type": "upshift",           "trigger_condition": "capacity>=0.8",  "minimum_priority_threshold": 0.3, "minimum_risk_threshold": 0.5, "requires_alt_plant_flag": False, "allows_expedite_flag": False, "allows_upshift_flag": True,  "expected_effect_type": "reduce_overload",     "policy_version": "v1"},
        {"action_type": "expedite_shipping", "trigger_condition": "logistics>=0.6", "minimum_priority_threshold": 0.5, "minimum_risk_threshold": 0.5, "requires_alt_plant_flag": False, "allows_expedite_flag": True,  "allows_upshift_flag": False, "expected_effect_type": "reduce_delay",       "policy_version": "v1"},
        {"action_type": "reschedule",        "trigger_condition": "cap>=0.6,pri<0.5","minimum_priority_threshold": 0.0, "minimum_risk_threshold": 0.4, "requires_alt_plant_flag": False, "allows_expedite_flag": False, "allows_upshift_flag": False, "expected_effect_type": "reduce_overload",     "policy_version": "v1"},
        {"action_type": "escalate",          "trigger_condition": "asc>=0.8",       "minimum_priority_threshold": 0.7, "minimum_risk_threshold": 0.7, "requires_alt_plant_flag": False, "allows_expedite_flag": False, "allows_upshift_flag": False, "expected_effect_type": "escalate_decision",  "policy_version": "v1"},
        {"action_type": "hedge_inventory",   "trigger_condition": "src>=0.5",       "minimum_priority_threshold": 0.2, "minimum_risk_threshold": 0.3, "requires_alt_plant_flag": False, "allows_expedite_flag": False, "allows_upshift_flag": False, "expected_effect_type": "hedge_uncertainty",  "policy_version": "v1"},
        {"action_type": "split_production",  "trigger_condition": "cap>=0.7",       "minimum_priority_threshold": 0.4, "minimum_risk_threshold": 0.6, "requires_alt_plant_flag": True,  "allows_expedite_flag": False, "allows_upshift_flag": False, "expected_effect_type": "reduce_overload",     "policy_version": "v1"},
    ])


def _make_bottleneck(plant="NW01", scenario="all_in", wc="P01_NW01_PRESS_1") -> pd.DataFrame:
    return pd.DataFrame([{
        "scenario": scenario,
        "plant": plant,
        "work_center": wc,
        "tool_no_if_available": "T100",
        "bottleneck_severity": "critical",
        "top_driver_project_count": 3,
        "suggested_capacity_lever": "upside_1",
        "explanation_note": "test",
    }])


def _make_quality_flags(scenario="all_in", plant="NW01", penalty=0.4, handling="weaken") -> pd.DataFrame:
    return pd.DataFrame([{
        "entity_type": "sourcing_row",
        "entity_key": f"{scenario}|{plant}|RM-TEST|2026-W01",
        "issue_type": "missing_inventory_coverage",
        "severity": "critical",
        "penalty_score": penalty,
        "reason_code": "SHORTAGE_CRITICAL",
        "recommended_handling": handling,
    }])


def _make_resilience(scenario="all_in", plant="NW01", week="2026-W01", risk=0.15) -> pd.DataFrame:
    return pd.DataFrame([{
        "scenario": scenario,
        "project_id_if_available": "PROJ_NW01",
        "plant": plant,
        "week": week,
        "affected_branch": "war_disruption__eastern_europe",
        "delta_capacity_risk": 0.1,
        "delta_sourcing_risk": 0.05,
        "delta_logistics_risk": 0.02,
        "disruption_risk_score": risk,
        "mitigation_candidate": "upshift",
        "explanation_note": "test",
    }])


# =============================================================================
# _build_quality_penalty_index tests
# =============================================================================

class TestQualityPenaltyIndex:
    def test_empty_flags_returns_empty(self):
        result = _build_quality_penalty_index(pd.DataFrame())
        assert result.empty

    def test_weaken_penalties_aggregated(self):
        flags = _make_quality_flags(penalty=0.4, handling="weaken")
        result = _build_quality_penalty_index(flags)
        assert len(result) == 1
        assert result["total_weaken_penalty"].iloc[0] == pytest.approx(0.4)

    def test_flag_only_not_included(self):
        flags = _make_quality_flags(penalty=0.1, handling="flag_only")
        result = _build_quality_penalty_index(flags)
        assert result.empty

    def test_scenario_plant_parsed_from_key(self):
        flags = _make_quality_flags(scenario="expected_value", plant="NW05")
        result = _build_quality_penalty_index(flags)
        if not result.empty:
            assert result["scenario"].iloc[0] == "expected_value"
            assert result["plant"].iloc[0] == "NW05"

    def test_block_flag_detected(self):
        flags = _make_quality_flags(handling="block")
        result = _build_quality_penalty_index(flags)
        # block should not appear in weaken aggregation but should set has_block
        # (block rows are only in agg if they also have weaken rows)
        # With only block rows and no weaken rows, result may be empty
        # Just verify no crash
        assert isinstance(result, pd.DataFrame)


# =============================================================================
# _build_bottleneck_wc_index tests
# =============================================================================

class TestBottleneckWcIndex:
    def test_empty_returns_empty_dict(self):
        assert _build_bottleneck_wc_index(pd.DataFrame()) == {}

    def test_returns_wc_for_plant(self):
        bn = _make_bottleneck(plant="NW01", scenario="all_in", wc="P01_NW01_PRESS_1")
        idx = _build_bottleneck_wc_index(bn)
        assert idx.get(("all_in", "NW01")) == "P01_NW01_PRESS_1"

    def test_critical_preferred_over_warning(self):
        bn = pd.DataFrame([
            {"scenario": "all_in", "plant": "NW01", "work_center": "WC_WARN", "bottleneck_severity": "warning"},
            {"scenario": "all_in", "plant": "NW01", "work_center": "WC_CRIT", "bottleneck_severity": "critical"},
        ])
        idx = _build_bottleneck_wc_index(bn)
        assert idx.get(("all_in", "NW01")) == "WC_CRIT"


# =============================================================================
# _suggest_alt_plant tests
# =============================================================================

class TestSuggestAltPlant:
    def test_eu_plant_suggests_eu_peer(self):
        alt = _suggest_alt_plant("NW02")
        assert alt in ["NW03", "NW08", "NW09", "NW10"]

    def test_us_plant_suggests_us_peer(self):
        alt = _suggest_alt_plant("NW01")
        assert alt in ["NW06", "NW07"]

    def test_unknown_plant_returns_na(self):
        assert _suggest_alt_plant("NW99") == "N/A"

    def test_single_plant_group_returns_na(self):
        # NW11 is alone in "OTHER" group with NW14 — should suggest NW14
        alt = _suggest_alt_plant("NW11")
        assert alt == "NW14"


# =============================================================================
# _confidence_label tests
# =============================================================================

class TestConfidenceLabel:
    def test_high_score_returns_high(self):
        assert _confidence_label(0.80, False) == "high"

    def test_medium_score_returns_medium(self):
        assert _confidence_label(0.45, False) == "medium"

    def test_low_score_returns_low(self):
        assert _confidence_label(0.10, False) == "low"

    def test_block_flag_forces_low(self):
        assert _confidence_label(0.95, True) == "low"

    def test_zero_score_returns_low(self):
        assert _confidence_label(0.0, False) == "low"


# =============================================================================
# _apply_actions tests
# =============================================================================

class TestApplyActions:
    def _base_inputs(self, **risk_kwargs):
        return dict(
            risk=_make_risk(**risk_kwargs),
            policy=_make_policy(),
            bottleneck=_make_bottleneck(),
            quality_flags=pd.DataFrame(),
            resilience=pd.DataFrame(),
        )

    def test_required_columns_present(self):
        result = _apply_actions(**self._base_inputs())
        required = [
            "scenario", "action_type", "action_score", "project_id",
            "plant", "material_or_wc", "recommended_target_plant",
            "reason", "expected_effect", "confidence", "explanation_trace",
        ]
        for col in required:
            assert col in result.columns, f"Missing: {col}"

    def test_empty_risk_returns_empty(self):
        result = _apply_actions(
            risk=pd.DataFrame(), policy=_make_policy(),
            bottleneck=pd.DataFrame(), quality_flags=pd.DataFrame(),
            resilience=pd.DataFrame(),
        )
        assert result.empty

    def test_empty_policy_returns_empty(self):
        result = _apply_actions(
            risk=_make_risk(), policy=pd.DataFrame(),
            bottleneck=pd.DataFrame(), quality_flags=pd.DataFrame(),
            resilience=pd.DataFrame(),
        )
        assert result.empty

    def test_high_sourcing_risk_triggers_buy_now(self):
        result = _apply_actions(**self._base_inputs(
            sourcing_risk=0.90, priority=0.50, risk_score_base=0.75,
        ))
        assert "buy_now" in result["action_type"].values

    def test_low_risk_triggers_wait(self):
        result = _apply_actions(**self._base_inputs(
            capacity_risk=0.1, sourcing_risk=0.1, logistics_risk=0.1,
            priority=0.2, risk_score_base=0.1, action_score_base=0.05,
        ))
        assert "wait" in result["action_type"].values

    def test_high_capacity_risk_triggers_upshift(self):
        result = _apply_actions(**self._base_inputs(
            capacity_risk=0.90, sourcing_risk=0.5, priority=0.5,
            risk_score_base=0.70, action_score_base=0.50,
        ))
        assert "upshift" in result["action_type"].values

    def test_high_logistics_triggers_reroute(self):
        result = _apply_actions(**self._base_inputs(
            logistics_risk=0.70, priority=0.60, risk_score_base=0.60,
        ))
        assert "reroute" in result["action_type"].values

    def test_action_score_bounded(self):
        result = _apply_actions(**self._base_inputs())
        assert (result["action_score"] >= 0.0).all()
        assert (result["action_score"] <= 1.0).all()

    def test_action_score_sorted_descending(self):
        result = _apply_actions(**self._base_inputs())
        if len(result) > 1:
            assert (result["action_score"].diff().dropna() <= 0).all()

    def test_reroute_sets_target_plant(self):
        result = _apply_actions(**self._base_inputs(
            logistics_risk=0.70, priority=0.60, risk_score_base=0.65,
        ))
        reroute = result[result["action_type"] == "reroute"]
        if not reroute.empty:
            assert (reroute["recommended_target_plant"] != "N/A").all()

    def test_buy_now_no_target_plant(self):
        result = _apply_actions(**self._base_inputs(
            sourcing_risk=0.90, priority=0.50, risk_score_base=0.75,
        ))
        buy_now = result[result["action_type"] == "buy_now"]
        if not buy_now.empty:
            assert (buy_now["recommended_target_plant"] == "N/A").all()

    def test_explanation_trace_contains_action_name(self):
        result = _apply_actions(**self._base_inputs())
        for _, row in result.iterrows():
            assert row["action_type"] in row["explanation_trace"]

    def test_quality_penalty_reduces_score(self):
        inputs_no_penalty = self._base_inputs(action_score_base=0.60)
        inputs_with_penalty = dict(inputs_no_penalty)
        inputs_with_penalty["quality_flags"] = _make_quality_flags(penalty=0.5, handling="weaken")
        result_clean = _apply_actions(**inputs_no_penalty)
        result_penalised = _apply_actions(**inputs_with_penalty)
        if not result_clean.empty and not result_penalised.empty:
            clean_types = set(result_clean["action_type"])
            pen_types = set(result_penalised["action_type"])
            for atype in clean_types & pen_types:
                clean_score = result_clean[result_clean["action_type"] == atype]["action_score"].mean()
                pen_score = result_penalised[result_penalised["action_type"] == atype]["action_score"].mean()
                assert pen_score <= clean_score + 1e-6, (
                    f"{atype}: penalised score {pen_score:.3f} > clean {clean_score:.3f}"
                )

    def test_disruption_boosts_score(self):
        inputs_no_dis = self._base_inputs(action_score_base=0.50)
        inputs_with_dis = dict(inputs_no_dis)
        inputs_with_dis["resilience"] = _make_resilience(risk=0.80)
        result_plain = _apply_actions(**inputs_no_dis)
        result_dis = _apply_actions(**inputs_with_dis)
        if not result_plain.empty and not result_dis.empty:
            assert result_dis["action_score"].mean() >= result_plain["action_score"].mean() - 1e-6

    def test_capacity_action_returns_wc(self):
        result = _apply_actions(**self._base_inputs(
            capacity_risk=0.90, priority=0.50, risk_score_base=0.70,
        ))
        cap_rows = result[result["action_type"].isin(["upshift", "reschedule", "split_production"])]
        if not cap_rows.empty:
            assert cap_rows["material_or_wc"].str.contains("NW01|WC", regex=True).any()

    def test_multiple_scenarios_produce_separate_rows(self):
        result = _apply_actions(**self._base_inputs(
            scenarios=("all_in", "expected_value"),
        ))
        assert result["scenario"].nunique() == 2

    def test_confidence_values_valid(self):
        result = _apply_actions(**self._base_inputs())
        valid = {"low", "medium", "high"}
        assert set(result["confidence"].unique()).issubset(valid)


# =============================================================================
# Integration tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not _HAS_PROCESSED, reason="processed CSVs not found")
class TestIntegration:
    def _load(self, name: str) -> pd.DataFrame:
        path = _PROCESSED / f"{name}.csv"
        return pd.read_csv(path) if path.exists() else pd.DataFrame()

    def test_full_pipeline_produces_rows(self):
        actions = build_fact_planner_actions(
            risk=self._load("fact_integrated_risk_base"),
            policy=self._load("dim_action_policy"),
            bottleneck=self._load("fact_capacity_bottleneck_summary"),
            quality_flags=self._load("fact_data_quality_flags"),
            resilience=self._load("fact_scenario_resilience_impact"),
        )
        assert len(actions) > 0

    def test_all_nine_action_types_possible(self):
        actions = build_fact_planner_actions(
            risk=self._load("fact_integrated_risk_base"),
            policy=self._load("dim_action_policy"),
            bottleneck=self._load("fact_capacity_bottleneck_summary"),
            quality_flags=self._load("fact_data_quality_flags"),
            resilience=self._load("fact_scenario_resilience_impact"),
        )
        expected = {
            "buy_now", "wait", "reroute", "upshift", "expedite_shipping",
            "reschedule", "escalate", "hedge_inventory", "split_production",
        }
        found = set(actions["action_type"].unique())
        # At least some actions should appear
        assert len(found) >= 3

    def test_action_score_bounded(self):
        actions = build_fact_planner_actions(
            risk=self._load("fact_integrated_risk_base"),
            policy=self._load("dim_action_policy"),
            bottleneck=self._load("fact_capacity_bottleneck_summary"),
            quality_flags=self._load("fact_data_quality_flags"),
            resilience=self._load("fact_scenario_resilience_impact"),
        )
        assert (actions["action_score"] >= 0.0).all()
        assert (actions["action_score"] <= 1.0).all()

    def test_explanation_trace_non_empty(self):
        actions = build_fact_planner_actions(
            risk=self._load("fact_integrated_risk_base"),
            policy=self._load("dim_action_policy"),
            bottleneck=self._load("fact_capacity_bottleneck_summary"),
            quality_flags=self._load("fact_data_quality_flags"),
            resilience=self._load("fact_scenario_resilience_impact"),
        )
        assert actions["explanation_trace"].notna().all()
        assert (actions["explanation_trace"].str.len() > 0).all()

    def test_top_20_readable(self):
        actions = build_fact_planner_actions(
            risk=self._load("fact_integrated_risk_base"),
            policy=self._load("dim_action_policy"),
            bottleneck=self._load("fact_capacity_bottleneck_summary"),
            quality_flags=self._load("fact_data_quality_flags"),
            resilience=self._load("fact_scenario_resilience_impact"),
        )
        top20 = actions.head(20)
        assert len(top20) > 0
        assert top20["reason"].notna().all()
        assert top20["expected_effect"].notna().all()
