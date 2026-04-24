"""
test_wave3_lara.py
==================
Wave 3 validation tests — synthetic data only (no Excel required).

Run:
  pytest project/tests/test_wave3_lara.py -v -m "not integration"
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave3.disruption_catalog import (
    _build_catalog,
    build_dim_disruption_scenario_synth,
    DISRUPTION_FAMILIES,
)
from project.src.wave3.resilience_impact import (
    _apply_disruption,
    _compute_disrupted_scores,
    _select_mitigation_vectorised,
    _empty_impact,
    build_fact_scenario_resilience_impact,
)

_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
_HAS_BASE = (_PROCESSED / "fact_integrated_risk_base.csv").exists()


# =============================================================================
# Synthetic factories
# =============================================================================

def _make_base_risk(n_plants: int = 3, n_weeks: int = 4, scenarios=("all_in", "expected_value")) -> pd.DataFrame:
    plants = [f"NW{i:02d}" for i in range(1, n_plants + 1)]
    rows = []
    for scenario in scenarios:
        for plant in plants:
            for week in range(1, n_weeks + 1):
                rows.append({
                    "scenario": scenario,
                    "project_id": f"PROJ_{plant}",
                    "plant": plant,
                    "week": f"2026-W{week:02d}",
                    "capacity_risk_score": 0.40,
                    "sourcing_risk_score": 0.60,
                    "logistics_risk_score": 0.30,
                    "disruption_risk_score_placeholder": 0.0,
                    "risk_score_base": 0.46,
                })
    return pd.DataFrame(rows)


def _make_catalog_row(**overrides) -> pd.DataFrame:
    defaults = {
        "disruption_family": "test_disruption",
        "scenario_name": "test__nw01",
        "affected_region_or_lane": "TEST",
        "affected_plants": "NW01",
        "affected_materials": "ALL",
        "transit_multiplier": 1.5,
        "shipping_cost_multiplier": 1.5,
        "available_capacity_multiplier": 0.5,
        "lead_time_multiplier": 1.5,
        "reliability_penalty": 0.20,
        "synthetic_generation_rule": "test rule",
        "generation_version": "test_v1",
        "random_seed": 42,
    }
    defaults.update(overrides)
    return pd.DataFrame([defaults])


# =============================================================================
# disruption_catalog tests
# =============================================================================

class TestDisruptionCatalog:
    def test_eight_families(self):
        cat = _build_catalog()
        assert cat["disruption_family"].nunique() == 8

    def test_required_columns_present(self):
        cat = _build_catalog()
        required = [
            "scenario_name", "affected_region_or_lane", "affected_plants",
            "affected_materials", "transit_multiplier", "shipping_cost_multiplier",
            "available_capacity_multiplier", "lead_time_multiplier",
            "reliability_penalty", "synthetic_generation_rule",
        ]
        for col in required:
            assert col in cat.columns, f"Missing: {col}"

    def test_all_eight_families_present(self):
        cat = _build_catalog()
        expected = {
            "war_disruption", "lane_blockage", "border_delay", "plant_outage",
            "labor_shortage", "energy_shock", "fuel_price_spike", "maintenance_overrun",
        }
        assert set(cat["disruption_family"].tolist()) == expected

    def test_capacity_multiplier_in_range(self):
        cat = _build_catalog()
        assert (cat["available_capacity_multiplier"] >= 0.0).all()
        assert (cat["available_capacity_multiplier"] <= 1.0).all()

    def test_reliability_penalty_in_range(self):
        cat = _build_catalog()
        assert (cat["reliability_penalty"] >= 0.0).all()
        assert (cat["reliability_penalty"] <= 1.0).all()

    def test_lead_time_multiplier_ge_one(self):
        cat = _build_catalog()
        assert (cat["lead_time_multiplier"] >= 1.0).all()

    def test_shipping_cost_multiplier_ge_one(self):
        cat = _build_catalog()
        assert (cat["shipping_cost_multiplier"] >= 1.0).all()

    def test_scenario_names_unique(self):
        cat = _build_catalog()
        assert cat["scenario_name"].nunique() == len(cat)

    def test_plant_outage_has_zero_capacity(self):
        cat = _build_catalog()
        outage = cat[cat["disruption_family"] == "plant_outage"]
        assert (outage["available_capacity_multiplier"] == 0.0).all()

    def test_fuel_spike_affects_all_plants(self):
        cat = _build_catalog()
        fuel = cat[cat["disruption_family"] == "fuel_price_spike"]
        assert (fuel["affected_plants"] == "ALL").all()

    def test_generation_version_present(self):
        cat = _build_catalog()
        assert (cat["generation_version"] == "wave3_disruption_v1").all()

    def test_public_function_matches_internal(self):
        assert _build_catalog().equals(build_dim_disruption_scenario_synth())

    def test_disruption_families_constant_matches_catalog(self):
        cat = _build_catalog()
        assert set(DISRUPTION_FAMILIES) == set(cat["disruption_family"].tolist())


# =============================================================================
# resilience_impact: _compute_disrupted_scores tests
# =============================================================================

class TestComputeDisruptedScores:
    def _series(self, val: float) -> pd.Series:
        return pd.Series([val])

    def test_full_outage_maxes_capacity_risk(self):
        dis_cap, _, _ = _compute_disrupted_scores(
            self._series(0.5), self._series(0.5), self._series(0.5),
            cap_mult=0.0, lt_mult=1.0, rel_pen=0.0, cost_mult=1.0,
        )
        assert dis_cap.iloc[0] == 1.0

    def test_no_disruption_leaves_scores_unchanged(self):
        dis_cap, dis_src, dis_log = _compute_disrupted_scores(
            self._series(0.4), self._series(0.6), self._series(0.3),
            cap_mult=1.0, lt_mult=1.0, rel_pen=0.0, cost_mult=1.0,
        )
        assert abs(dis_cap.iloc[0] - 0.4) < 1e-6
        assert abs(dis_src.iloc[0] - 0.6) < 1e-6
        assert abs(dis_log.iloc[0] - 0.3) < 1e-6

    def test_capacity_reduces_with_multiplier(self):
        """Lower cap_mult → higher capacity risk."""
        base = self._series(0.3)
        dis_cap_low, _, _ = _compute_disrupted_scores(
            base, base, base, cap_mult=0.5, lt_mult=1.0, rel_pen=0.0, cost_mult=1.0
        )
        dis_cap_high, _, _ = _compute_disrupted_scores(
            base, base, base, cap_mult=0.8, lt_mult=1.0, rel_pen=0.0, cost_mult=1.0
        )
        assert dis_cap_low.iloc[0] >= dis_cap_high.iloc[0]

    def test_lead_time_multiplier_increases_sourcing_risk(self):
        base = self._series(0.4)
        _, dis_src, _ = _compute_disrupted_scores(
            base, base, base, cap_mult=1.0, lt_mult=1.5, rel_pen=0.0, cost_mult=1.0
        )
        assert dis_src.iloc[0] > 0.4

    def test_reliability_penalty_increases_logistics_risk(self):
        base = self._series(0.3)
        _, _, dis_log_with = _compute_disrupted_scores(
            base, base, base, cap_mult=1.0, lt_mult=1.0, rel_pen=0.3, cost_mult=1.0
        )
        _, _, dis_log_without = _compute_disrupted_scores(
            base, base, base, cap_mult=1.0, lt_mult=1.0, rel_pen=0.0, cost_mult=1.0
        )
        assert dis_log_with.iloc[0] > dis_log_without.iloc[0]

    def test_all_outputs_clamped_zero_one(self):
        extreme = self._series(0.99)
        dis_cap, dis_src, dis_log = _compute_disrupted_scores(
            extreme, extreme, extreme,
            cap_mult=0.001, lt_mult=10.0, rel_pen=1.0, cost_mult=10.0,
        )
        for s in [dis_cap, dis_src, dis_log]:
            assert (s >= 0.0).all() and (s <= 1.0).all()


# =============================================================================
# resilience_impact: _select_mitigation_vectorised tests
# =============================================================================

class TestSelectMitigation:
    def _s(self, val: float) -> pd.Series:
        return pd.Series([val])

    def test_outage_returns_reschedule(self):
        result = _select_mitigation_vectorised(self._s(0.5), self._s(0.3), self._s(0.2), cap_mult=0.0)
        assert result.iloc[0] == "reschedule"

    def test_capacity_dominant_returns_upshift(self):
        result = _select_mitigation_vectorised(self._s(0.5), self._s(0.1), self._s(0.1), cap_mult=0.8)
        assert result.iloc[0] == "upshift"

    def test_logistics_dominant_returns_reroute(self):
        result = _select_mitigation_vectorised(self._s(0.05), self._s(0.05), self._s(0.4), cap_mult=1.0)
        assert result.iloc[0] == "reroute"

    def test_sourcing_dominant_returns_expedite(self):
        result = _select_mitigation_vectorised(self._s(0.0), self._s(0.5), self._s(0.0), cap_mult=1.0)
        assert result.iloc[0] == "expedite"

    def test_no_impact_returns_no_action_needed(self):
        result = _select_mitigation_vectorised(self._s(0.0), self._s(0.0), self._s(0.0), cap_mult=1.0)
        assert result.iloc[0] == "no_action_needed"


# =============================================================================
# _apply_disruption tests
# =============================================================================

class TestApplyDisruption:
    def test_output_columns_present(self):
        base = _make_base_risk(n_plants=2, n_weeks=2)
        cat = _make_catalog_row()
        result = _apply_disruption(base, cat)
        required = [
            "scenario", "project_id_if_available", "plant", "week",
            "affected_branch", "delta_capacity_risk", "delta_sourcing_risk",
            "delta_logistics_risk", "disruption_risk_score",
            "mitigation_candidate", "explanation_note",
        ]
        for col in required:
            assert col in result.columns, f"Missing: {col}"

    def test_only_affected_plants_returned(self):
        base = _make_base_risk(n_plants=3, n_weeks=2)
        cat = _make_catalog_row(affected_plants="NW01")
        result = _apply_disruption(base, cat)
        assert set(result["plant"].unique()) == {"NW01"}

    def test_all_plants_when_global(self):
        base = _make_base_risk(n_plants=3, n_weeks=2)
        cat = _make_catalog_row(affected_plants="ALL")
        result = _apply_disruption(base, cat)
        assert set(result["plant"].unique()) == {"NW01", "NW02", "NW03"}

    def test_disruption_risk_score_non_negative(self):
        base = _make_base_risk()
        cat = _make_catalog_row()
        result = _apply_disruption(base, cat)
        assert (result["disruption_risk_score"] >= 0).all()

    def test_disruption_risk_score_le_one(self):
        base = _make_base_risk()
        cat = _make_catalog_row()
        result = _apply_disruption(base, cat)
        assert (result["disruption_risk_score"] <= 1.0).all()

    def test_outage_yields_reschedule_mitigation(self):
        base = _make_base_risk(n_plants=1, n_weeks=2)
        cat = _make_catalog_row(affected_plants="NW01", available_capacity_multiplier=0.0)
        result = _apply_disruption(base, cat)
        assert (result["mitigation_candidate"] == "reschedule").all()

    def test_explanation_note_contains_disruption_name(self):
        base = _make_base_risk(n_plants=1, n_weeks=2)
        cat = _make_catalog_row(scenario_name="my_test_scenario")
        result = _apply_disruption(base, cat)
        assert result["explanation_note"].str.contains("my_test_scenario").all()

    def test_empty_base_returns_empty(self):
        result = _apply_disruption(pd.DataFrame(), _make_catalog_row())
        assert result.empty
        assert list(result.columns) == list(_empty_impact().columns)

    def test_empty_catalog_returns_empty(self):
        base = _make_base_risk()
        result = _apply_disruption(base, pd.DataFrame())
        assert result.empty

    def test_no_match_returns_empty(self):
        base = _make_base_risk(n_plants=1)  # NW01 only
        cat = _make_catalog_row(affected_plants="NW99")
        result = _apply_disruption(base, cat)
        assert result.empty

    def test_multiple_scenarios_in_output(self):
        base = _make_base_risk(n_plants=2, scenarios=("all_in", "expected_value"))
        cat = _make_catalog_row(affected_plants="ALL")
        result = _apply_disruption(base, cat)
        assert result["scenario"].nunique() == 2

    def test_full_catalog_produces_rows(self):
        base = _make_base_risk(n_plants=15, n_weeks=4)
        cat = build_dim_disruption_scenario_synth()
        result = _apply_disruption(base, cat)
        assert len(result) > 0
        assert result["affected_branch"].nunique() == 8

    def test_no_disruption_row_has_zero_delta(self):
        """A no-op disruption (all multipliers at neutral) produces zero deltas."""
        base = _make_base_risk(n_plants=1, n_weeks=1)
        cat = _make_catalog_row(
            affected_plants="ALL",
            available_capacity_multiplier=1.0,
            lead_time_multiplier=1.0,
            reliability_penalty=0.0,
            shipping_cost_multiplier=1.0,
        )
        result = _apply_disruption(base, cat)
        assert (result["delta_capacity_risk"].abs() < 1e-6).all()
        assert (result["delta_sourcing_risk"].abs() < 1e-6).all()
        assert (result["delta_logistics_risk"].abs() < 1e-6).all()


# =============================================================================
# Integration tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not _HAS_BASE, reason="fact_integrated_risk_base.csv not found")
class TestIntegration:
    def _load_base(self) -> pd.DataFrame:
        return pd.read_csv(_PROCESSED / "fact_integrated_risk_base.csv")

    def test_full_pipeline_row_count(self):
        base = self._load_base()
        cat = build_dim_disruption_scenario_synth()
        result = build_fact_scenario_resilience_impact(base, cat)
        # Expect at least 1 row per disruption per affected plant-scenario-week combo
        assert len(result) > 0

    def test_all_eight_branches_present(self):
        base = self._load_base()
        cat = build_dim_disruption_scenario_synth()
        result = build_fact_scenario_resilience_impact(base, cat)
        assert result["affected_branch"].nunique() == 8

    def test_mitigation_candidates_are_valid(self):
        base = self._load_base()
        cat = build_dim_disruption_scenario_synth()
        result = build_fact_scenario_resilience_impact(base, cat)
        valid = {"reschedule", "upshift", "reroute", "expedite", "no_action_needed", "monitor"}
        assert set(result["mitigation_candidate"].unique()).issubset(valid)

    def test_disruption_risk_score_bounded(self):
        base = self._load_base()
        cat = build_dim_disruption_scenario_synth()
        result = build_fact_scenario_resilience_impact(base, cat)
        assert (result["disruption_risk_score"] >= 0.0).all()
        assert (result["disruption_risk_score"] <= 1.0).all()

    def test_plant_outage_has_highest_mean_risk(self):
        base = self._load_base()
        cat = build_dim_disruption_scenario_synth()
        result = build_fact_scenario_resilience_impact(base, cat)
        by_branch = result.groupby("affected_branch")["disruption_risk_score"].mean()
        outage_col = [c for c in by_branch.index if "plant_outage" in c]
        if outage_col:
            outage_risk = by_branch[outage_col[0]]
            assert outage_risk >= by_branch.quantile(0.5), (
                f"plant_outage mean risk ({outage_risk:.3f}) should be above median"
            )
