"""Demo layer for Wave 4 — loads processed outputs and derives planner actions."""
from __future__ import annotations

import os
import warnings
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent  # <repo>/project/src/app
_REPO_ROOT = _HERE.parents[2]  # parents[0]=src, parents[1]=project, parents[2]=repo root


_DEFAULT_REAL = _REPO_ROOT / "project" / "data" / "processed"
_DEFAULT_SYNTH = _REPO_ROOT / "processed"


# ---------------------------------------------------------------------------
# File manifest
# ---------------------------------------------------------------------------
_REAL_FILES = {
    # Wave 3-5 outputs
    "risk_base":        "fact_integrated_risk_base.csv",
    "sourcing":         "fact_scenario_sourcing_weekly.csv",
    "logistics":        "fact_scenario_logistics_weekly.csv",
    "bottlenecks":      "fact_capacity_bottleneck_summary.csv",
    "action_policy":    "dim_action_policy.csv",
    "quality_flags":    "fact_data_quality_flags.csv",
    "project_priority": "dim_project_priority.csv",
    # Wave 6-7 outputs
    "region_scope":           "dim_region_scope.csv",
    "pipeline_quarterly":     "fact_pipeline_quarterly.csv",
    "effective_capacity_v2":  "fact_effective_capacity_weekly_v2.csv",
    "delivery_commitment":    "fact_delivery_commitment_weekly.csv",
    "service_memory":         "fact_quarter_service_memory.csv",
    "delivery_rollforward":   "fact_delivery_risk_rollforward.csv",
    "maintenance_impact":     "fact_maintenance_impact_summary.csv",
    "learning_signals":       "fact_quarter_learning_signals.csv",
    "rollforward_inputs":     "fact_quarter_rollforward_inputs.csv",
    "planner_actions_v2":     "fact_planner_actions_v2.csv",
    "integrated_risk_v2":    "fact_integrated_risk_v2.csv",
}

_SYNTH_FILES = {
    "service_level_policy": "dim_service_level_policy_synth.csv",
}

# Driver → preferred action types (ordered by preference)
_DRIVER_ACTION_MAP: dict[str, list[str]] = {
    "sourcing_risk":  ["buy_now", "hedge_inventory"],
    "capacity_risk":  ["upshift", "reschedule", "split_production"],
    "logistics_risk": ["reroute", "expedite_shipping"],
    "lead_time_risk": ["buy_now", "reschedule"],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_all_processed(
    real_processed_dir: str | Path = _DEFAULT_REAL,
    synth_processed_dir: str | Path = _DEFAULT_SYNTH,
) -> dict[str, pd.DataFrame]:
    """Load all available processed CSVs.

    Returns a dict with keys:
        risk_base, sourcing, logistics, bottlenecks, action_policy,
        quality_flags, project_priority, service_level_policy

    Missing files produce an empty DataFrame + a printed warning.
    """
    real_dir = Path(real_processed_dir)
    synth_dir = Path(synth_processed_dir)

    result: dict[str, pd.DataFrame] = {}

    for key, filename in _REAL_FILES.items():
        path = real_dir / filename
        if path.exists():
            try:
                result[key] = pd.read_csv(path, low_memory=False)
            except Exception as exc:  # noqa: BLE001
                warnings.warn(f"[demo_layer] Failed to load {path}: {exc}")
                result[key] = pd.DataFrame()
        else:
            warnings.warn(f"[demo_layer] Missing file: {path}")
            result[key] = pd.DataFrame()

    for key, filename in _SYNTH_FILES.items():
        path = synth_dir / filename
        if path.exists():
            try:
                result[key] = pd.read_csv(path, low_memory=False)
            except Exception as exc:  # noqa: BLE001
                warnings.warn(f"[demo_layer] Failed to load {path}: {exc}")
                result[key] = pd.DataFrame()
        else:
            # Synth files are optional — quiet warning
            warnings.warn(f"[demo_layer] Synth file not found (optional): {path}")
            result[key] = pd.DataFrame()

    return result


def derive_planner_actions(
    risk_base: pd.DataFrame,
    action_policy: pd.DataFrame,
    quality_flags: pd.DataFrame,
) -> pd.DataFrame:
    """Derive one planner action per (scenario, project_id, plant, week).

    Matches applicable action policies based on priority/risk thresholds and
    top_driver alignment, then adjusts action scores by QA penalties.

    Output columns:
        scenario, project_id, plant, week, action_type,
        action_score_base, total_penalty, adjusted_action_score,
        recommended_handling, top_driver, explainability_note,
        priority_score, risk_score_base
    """
    if risk_base.empty:
        return pd.DataFrame()

    rb = risk_base.copy()

    # --- Build penalty lookup from quality_flags (vectorised) -------------
    # entity_key format for risk rows: "scenario|project_id|plant|week"
    penalty_map: dict[str, float] = {}
    recommended_map: dict[str, str] = {}

    if not quality_flags.empty and "entity_key" in quality_flags.columns:
        qf = quality_flags.copy()
        # Only keep 4-part keys (risk row keys)
        key_parts = qf["entity_key"].astype(str).str.split("|", expand=True)
        mask_4 = key_parts.shape[1] >= 4
        if mask_4:
            four_part = key_parts.iloc[:, :4].notna().all(axis=1)
            qf = qf[four_part].copy()
            qf["_key"] = qf["entity_key"].astype(str)
            qf["penalty_score"] = pd.to_numeric(qf["penalty_score"], errors="coerce").fillna(0.0)
            # Sum penalties per key
            pen_series = qf.groupby("_key")["penalty_score"].sum()
            penalty_map = pen_series.to_dict()
            # Last recommended_handling per key
            if "recommended_handling" in qf.columns:
                rec_series = qf.groupby("_key")["recommended_handling"].last()
                recommended_map = rec_series.astype(str).to_dict()

    # --- Match policies per risk row --------------------------------------
    if action_policy.empty:
        # Fallback: no policy → assign "wait" to everything
        rb["action_type"] = "wait"
        rb["total_penalty"] = 0.0
        rb["adjusted_action_score"] = rb["action_score_base"].clip(lower=0)
        rb["recommended_handling"] = ""
        out_cols = [
            "scenario", "project_id", "plant", "week",
            "action_type", "action_score_base", "total_penalty",
            "adjusted_action_score", "recommended_handling",
            "top_driver", "explainability_note", "priority_score", "risk_score_base",
        ]
        return rb[[c for c in out_cols if c in rb.columns]].reset_index(drop=True)

    ap = action_policy.copy()
    ap["minimum_priority_threshold"] = ap["minimum_priority_threshold"].fillna(0).astype(float)
    ap["minimum_risk_threshold"] = ap["minimum_risk_threshold"].fillna(0).astype(float)

    # --- Build driver → best action lookup (priority-ordered) ---------------
    # For each (driver, priority_thresh, risk_thresh) combination we want the
    # top preferred action that exists in the policy table.
    driver_action_lookup: dict[str, tuple[str, str]] = {}
    for driver, preferred in _DRIVER_ACTION_MAP.items():
        for pref in preferred:
            hit = ap[ap["action_type"] == pref]
            if not hit.empty:
                effect = str(hit.iloc[0].get("expected_effect_type", ""))
                driver_action_lookup[driver] = (pref, effect)
                break
        if driver not in driver_action_lookup:
            # fallback: highest-threshold row
            fallback = ap.sort_values("minimum_risk_threshold", ascending=False)
            if not fallback.empty:
                driver_action_lookup[driver] = (
                    str(fallback.iloc[0]["action_type"]),
                    str(fallback.iloc[0].get("expected_effect_type", "")),
                )

    # Global min thresholds in the policy (used for vectorised eligibility check)
    min_priority_global = float(ap["minimum_priority_threshold"].min())
    min_risk_global     = float(ap["minimum_risk_threshold"].min())

    # --- Vectorised action assignment ----------------------------------------
    result = rb[["scenario", "project_id", "plant", "week",
                 "action_score_base", "top_driver", "explainability_note",
                 "priority_score", "risk_score_base"]].copy()

    # Coerce numeric columns
    result["priority_score"]   = result["priority_score"].fillna(0).astype(float)
    result["risk_score_base"]  = result["risk_score_base"].fillna(0).astype(float)
    result["action_score_base"] = result["action_score_base"].fillna(0).astype(float)

    # Eligible = meets global minimum thresholds
    eligible_mask = (
        (result["priority_score"] >= min_priority_global) &
        (result["risk_score_base"] >= min_risk_global)
    )

    # Map top_driver to (action_type, recommended_handling)
    result["action_type"] = result["top_driver"].map(
        lambda d: driver_action_lookup.get(d, ("wait", ""))[0]
    )
    result["recommended_handling"] = result["top_driver"].map(
        lambda d: driver_action_lookup.get(d, ("wait", ""))[1]
    )
    # Non-eligible rows get "wait"
    result.loc[~eligible_mask, "action_type"] = "wait"
    result.loc[~eligible_mask, "recommended_handling"] = ""

    # --- Penalties (vectorised via entity_key lookup) -----------------------
    result["_key"] = (
        result["scenario"].astype(str) + "|" +
        result["project_id"].astype(str) + "|" +
        result["plant"].astype(str) + "|" +
        result["week"].astype(str)
    )
    result["total_penalty"] = result["_key"].map(penalty_map).fillna(0.0).clip(upper=0.8)
    result["adjusted_action_score"] = (result["action_score_base"] - result["total_penalty"]).clip(lower=0.0)

    # Override recommended_handling from QA flags where available
    result["_qf_handling"] = result["_key"].map(recommended_map).fillna("")
    mask_qf = result["_qf_handling"] != ""
    result.loc[mask_qf, "recommended_handling"] = result.loc[mask_qf, "_qf_handling"]

    result = result.drop(columns=["_key", "_qf_handling"])

    out_cols = [
        "scenario", "project_id", "plant", "week",
        "action_type", "action_score_base", "total_penalty",
        "adjusted_action_score", "recommended_handling",
        "top_driver", "explainability_note", "priority_score", "risk_score_base",
    ]
    return result[[c for c in out_cols if c in result.columns]].reset_index(drop=True)


def get_demo_summary(data: dict[str, pd.DataFrame]) -> dict:
    """Return a KPI dict for the demo summary panel."""
    risk_base    = data.get("risk_base", pd.DataFrame())
    sourcing     = data.get("sourcing", pd.DataFrame())
    bottlenecks  = data.get("bottlenecks", pd.DataFrame())

    total_projects = int(risk_base["project_id"].nunique()) if not risk_base.empty and "project_id" in risk_base.columns else 0
    total_plants   = int(risk_base["plant"].nunique())      if not risk_base.empty and "plant"      in risk_base.columns else 0
    scenarios_available = (
        sorted(risk_base["scenario"].dropna().unique().tolist())
        if not risk_base.empty and "scenario" in risk_base.columns
        else []
    )
    shortage_rows = int(
        (sourcing["shortage_flag"] == True).sum()  # noqa: E712
        if not sourcing.empty and "shortage_flag" in sourcing.columns
        else 0
    )
    bottleneck_count = int(len(bottlenecks)) if not bottlenecks.empty else 0
    avg_risk_score = float(
        risk_base["risk_score_base"].mean()
        if not risk_base.empty and "risk_score_base" in risk_base.columns
        else 0.0
    )

    # High-priority actions: action_score_base > 0.6
    high_priority_actions = int(
        (risk_base["action_score_base"] > 0.6).sum()
        if not risk_base.empty and "action_score_base" in risk_base.columns
        else 0
    )

    return {
        "total_projects":       total_projects,
        "total_plants":         total_plants,
        "scenarios_available":  scenarios_available,
        "shortage_rows":        shortage_rows,
        "bottleneck_count":     bottleneck_count,
        "avg_risk_score":       round(avg_risk_score, 4),
        "high_priority_actions": high_priority_actions,
    }
