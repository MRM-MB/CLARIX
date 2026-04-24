"""
planner_actions_v2.py
=====================
Wave 7 Lara: Build fact_planner_actions_v2 — maintenance-aware, region-scoped,
quarter-aware planner action engine.

Action families:
  buy_now, wait, reroute, upshift, expedite_shipping, reschedule, escalate,
  hedge_inventory, split_production, shift_maintenance, protect_capacity_window

Usage:
  from project.src.wave7.planner_actions_v2 import build_fact_planner_actions_v2
"""

from __future__ import annotations

import json

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_COLS = [
    "scope_id",
    "scenario",
    "quarter_id",
    "action_type",
    "action_score",
    "project_id",
    "plant",
    "material_or_wc",
    "recommended_target_plant",
    "reason",
    "expected_effect",
    "confidence",
    "explanation_trace",
]

_HIGH_RISK: float = 0.65
_MED_RISK: float = 0.40
_LOW_RISK: float = 0.20

_MAINT_PROTECT_SCENARIO = "unexpected_breakdown"

_REASONS: dict[str, str] = {
    "buy_now": "Sourcing risk is elevated — order now to beat lead time",
    "hedge_inventory": "Moderate sourcing risk — add safety stock buffer",
    "upshift": "Capacity risk detected — increase shift to absorb demand",
    "reschedule": "Risk present but manageable — defer or spread production",
    "split_production": "Very high capacity risk — split load across plants or weeks",
    "escalate": "Critical risk level — escalate to planning management",
    "reroute": "High logistics risk — switch to alternative shipping lane",
    "expedite_shipping": "Logistics pressure — use expedite option if available",
    "shift_maintenance": "Maintenance window conflicts with high-load quarter — shift timing",
    "protect_capacity_window": "Bottleneck WC has scheduled maintenance — protect capacity before event",
    "wait": "Risk within acceptable range — no action required",
}

_EXPECTED_EFFECTS: dict[str, str] = {
    "buy_now": "Reduced shortage risk; earlier inventory build-up",
    "hedge_inventory": "Lower stockout probability; slight inventory carrying cost",
    "upshift": "Increased available capacity hours; potential overtime cost",
    "reschedule": "Smoothed load profile; possible minor delay to non-critical projects",
    "split_production": "Reduced bottleneck pressure; higher logistics complexity",
    "escalate": "Management visibility; expedited resource allocation",
    "reroute": "Reduced transit risk; potentially higher shipping cost",
    "expedite_shipping": "Faster delivery; premium freight cost",
    "shift_maintenance": "Maintenance rescheduled to lower-load period; minor schedule disruption",
    "protect_capacity_window": "Capacity preserved for high-priority production; maintenance deferred",
    "wait": "No cost; monitor for risk escalation",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _week_to_quarter(week_str: str) -> str:
    """Map YYYY-Www to YYYY-Qq.

    W01-W13 → Q1, W14-W26 → Q2, W27-W39 → Q3, W40-W53 → Q4
    """
    try:
        year, w = week_str.split("-W")
        w_num = int(w)
        if w_num <= 13:
            q = 1
        elif w_num <= 26:
            q = 2
        elif w_num <= 39:
            q = 3
        else:
            q = 4
        return f"{year}-Q{q}"
    except Exception:
        return "unknown"


def _build_scope_map(region_scope: pd.DataFrame) -> dict[str, str]:
    """Return {plant: scope_id} from dim_region_scope.

    Active regions take precedence; inactive used as fallback.
    """
    scope_map: dict[str, str] = {}
    if region_scope.empty or "included_plants" not in region_scope.columns:
        return scope_map

    # Process inactive first so active overwrites
    for active in [False, True]:
        sub = region_scope[region_scope.get("active_flag", pd.Series(True, index=region_scope.index)) == active] \
            if "active_flag" in region_scope.columns else region_scope
        for _, row in sub.iterrows():
            sid = str(row.get("scope_id", "unknown"))
            plants_raw = str(row.get("included_plants", ""))
            for p in plants_raw.split(","):
                p = p.strip()
                if p:
                    scope_map[p] = sid
    return scope_map


def _build_maintenance_context(
    maintenance_impact: pd.DataFrame,
) -> dict[str, dict]:
    """Build {plant: {worst_wc, max_severity, max_pct_lost}} from maintenance_impact."""
    ctx: dict[str, dict] = {}
    if maintenance_impact.empty:
        return ctx

    for plant, grp in maintenance_impact.groupby("plant"):
        worst_idx = grp["pct_capacity_lost_to_maintenance"].idxmax()
        worst = grp.loc[worst_idx]
        ctx[str(plant)] = {
            "worst_wc": str(worst.get("work_center", "")),
            "max_severity": str(worst.get("impact_severity", "none")),
            "max_pct_lost": float(worst.get("pct_capacity_lost_to_maintenance", 0.0)),
            "maintenance_scenario": str(worst.get("scenario", "")),
        }
    return ctx


def _build_protect_opportunities(
    effective_capacity: pd.DataFrame,
    scenario: str = _MAINT_PROTECT_SCENARIO,
) -> set[tuple[str, str, str]]:
    """Return set of (plant, work_center, quarter_id) tuples where a bottleneck
    coincides with scheduled maintenance — indicating a protect_capacity_window need."""
    if effective_capacity.empty:
        return set()

    eff = effective_capacity[effective_capacity["scenario"] == scenario].copy() \
        if "scenario" in effective_capacity.columns else effective_capacity.copy()

    if eff.empty:
        return set()

    protect_rows = eff[
        (eff["bottleneck_flag"] == True) &  # noqa: E712
        (eff["scheduled_maintenance_hours"] > 0)
    ].copy()

    if protect_rows.empty:
        return set()

    protect_rows["quarter_id"] = protect_rows["week"].apply(_week_to_quarter)
    return set(
        zip(protect_rows["plant"].astype(str),
            protect_rows["work_center"].astype(str),
            protect_rows["quarter_id"].astype(str))
    )


def _select_action_type(
    top_driver: str,
    avg_risk: float,
    maint_severity: str,
    has_protect: bool,
    caution_flag: bool,
) -> str:
    """Select primary action type from risk signals."""
    # Caution carry-over boosts threshold sensitivity
    eff_risk = min(1.0, avg_risk * (1.1 if caution_flag else 1.0))

    if eff_risk < _LOW_RISK:
        return "wait"

    if top_driver == "sourcing_risk":
        return "buy_now" if eff_risk >= _HIGH_RISK else "hedge_inventory"

    if top_driver == "capacity_risk":
        if maint_severity in ("medium", "high"):
            return "shift_maintenance"
        if has_protect:
            return "protect_capacity_window"
        if eff_risk >= 0.80:
            return "split_production"
        if eff_risk >= _HIGH_RISK:
            return "escalate"
        if eff_risk >= _MED_RISK:
            return "upshift"
        return "reschedule"

    if top_driver == "logistics_risk":
        return "reroute" if eff_risk >= _HIGH_RISK else "expedite_shipping"

    if top_driver == "lead_time_risk":
        return "buy_now" if eff_risk >= _MED_RISK else "reschedule"

    return "wait"


def _build_reroute_map(
    aggregated: pd.DataFrame,
) -> dict[tuple[str, str, str, str], str]:
    """For reroute actions: map (scope_id, scenario, quarter_id, source_plant) → best_alt_plant.

    Best alt = plant with lowest avg capacity_risk in same scope+scenario+quarter,
    excluding the source plant itself.
    """
    rmap: dict[tuple[str, str, str, str], str] = {}
    if aggregated.empty or "avg_capacity_risk" not in aggregated.columns:
        return rmap

    for (scope, sc, qtr), grp in aggregated.groupby(["scope_id", "scenario", "quarter_id"]):
        sorted_plants = grp.sort_values("avg_capacity_risk")["plant"].astype(str).tolist()
        for source_plant in sorted_plants:
            alts = [p for p in sorted_plants if p != source_plant]
            rmap[(str(scope), str(sc), str(qtr), source_plant)] = alts[0] if alts else ""
    return rmap


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_fact_planner_actions_v2(
    integrated_risk: pd.DataFrame,
    effective_capacity: pd.DataFrame,
    maintenance_impact: pd.DataFrame,
    region_scope: pd.DataFrame,
    action_policy: pd.DataFrame,
    service_memory: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build fact_planner_actions_v2 — maintenance-aware, region-scoped, quarter-aware.

    Parameters
    ----------
    integrated_risk:
        fact_integrated_risk — (scenario, project_id, plant, week, top_driver, risk_score, ...)
    effective_capacity:
        fact_effective_capacity_weekly_v2 — (scope_id, scenario, plant, work_center, week, ...)
    maintenance_impact:
        fact_maintenance_impact_summary — (scope_id, scenario, plant, work_center, ...)
    region_scope:
        dim_region_scope — (scope_id, region_name, included_plants, active_flag)
    action_policy:
        dim_action_policy — (action_type, minimum_risk_threshold, ...)
    service_memory:
        fact_quarter_service_memory (optional) — (scope_id, quarter_id, project_id,
        carry_over_service_caution_flag, ...)

    Returns
    -------
    DataFrame with _REQUIRED_COLS, grain: (scope_id, scenario, quarter_id, project_id, plant).
    """
    if integrated_risk.empty:
        return pd.DataFrame(columns=_REQUIRED_COLS)

    ir = integrated_risk.copy()

    # --- 1. Map weeks to quarters ---
    ir["quarter_id"] = ir["week"].apply(_week_to_quarter)

    # --- 2. Build scope map and assign scope_id ---
    scope_map = _build_scope_map(region_scope)
    ir["scope_id"] = ir["plant"].astype(str).map(scope_map).fillna("global_reference")

    # --- 3. Aggregate to (scope_id, scenario, quarter_id, project_id, plant) ---
    risk_cols = [c for c in ["risk_score", "action_score", "capacity_risk_score",
                              "sourcing_risk_score", "logistics_risk_score",
                              "lead_time_risk_score", "scenario_confidence"]
                 if c in ir.columns]

    agg_dict: dict = {c: "mean" for c in risk_cols}
    agg_dict["top_driver"] = lambda x: x.mode().iloc[0] if not x.empty else "unknown"
    if "explainability_note" in ir.columns:
        agg_dict["explainability_note"] = "first"

    agg = ir.groupby(
        ["scope_id", "scenario", "quarter_id", "project_id", "plant"],
        as_index=False,
    ).agg(agg_dict)

    # Rename aggregated risk columns
    rename_map = {
        "risk_score": "avg_risk_score",
        "action_score": "avg_action_score",
        "capacity_risk_score": "avg_capacity_risk",
        "sourcing_risk_score": "avg_sourcing_risk",
        "logistics_risk_score": "avg_logistics_risk",
        "lead_time_risk_score": "avg_lead_time_risk",
        "scenario_confidence": "avg_confidence",
    }
    agg = agg.rename(columns={k: v for k, v in rename_map.items() if k in agg.columns})

    # --- 4. Build maintenance context ---
    maint_ctx = _build_maintenance_context(maintenance_impact)
    protect_set = _build_protect_opportunities(effective_capacity)

    agg["_maint_severity"] = agg["plant"].astype(str).map(
        lambda p: maint_ctx.get(p, {}).get("max_severity", "none")
    )
    agg["_worst_wc"] = agg["plant"].astype(str).map(
        lambda p: maint_ctx.get(p, {}).get("worst_wc", "")
    )
    # Precompute (plant, quarter_id) pairs that have at least one protect opportunity,
    # regardless of which specific WC it is on.
    protect_plant_qtrs: set[tuple[str, str]] = {(p, q) for (p, _wc, q) in protect_set}
    agg["_has_protect"] = agg.apply(
        lambda r: (str(r["plant"]), str(r["quarter_id"])) in protect_plant_qtrs,
        axis=1,
    )

    # --- 5. Build service-memory caution map ---
    caution_map: dict[tuple[str, str], bool] = {}
    if service_memory is not None and not service_memory.empty:
        sm_cols_needed = {"project_id", "quarter_id", "carry_over_service_caution_flag"}
        if sm_cols_needed.issubset(set(service_memory.columns)):
            for _, row in service_memory.iterrows():
                key = (str(row["project_id"]), str(row["quarter_id"]))
                caution_map[key] = bool(row["carry_over_service_caution_flag"])

    agg["_caution"] = agg.apply(
        lambda r: caution_map.get((str(r["project_id"]), str(r["quarter_id"])), False),
        axis=1,
    )

    # --- 6. Build reroute target map and action_policy threshold lookup ---
    reroute_map = _build_reroute_map(agg)

    policy_thresholds: dict[str, float] = {}
    if not action_policy.empty and "action_type" in action_policy.columns and "minimum_risk_threshold" in action_policy.columns:
        policy_thresholds = {
            str(r["action_type"]): float(r["minimum_risk_threshold"])
            for _, r in action_policy.iterrows()
        }

    # --- 7. Select action per row ---
    avg_risk_col = "avg_risk_score" if "avg_risk_score" in agg.columns else \
        next((c for c in agg.columns if "risk" in c), None)
    conf_col = "avg_confidence" if "avg_confidence" in agg.columns else None

    def _make_row(r) -> dict:
        avg_risk = float(r.get(avg_risk_col, 0.0)) if avg_risk_col else 0.0
        top_driver = str(r.get("top_driver", "unknown"))
        maint_sev = str(r.get("_maint_severity", "none"))
        has_protect = bool(r.get("_has_protect", False))
        caution = bool(r.get("_caution", False))
        worst_wc = str(r.get("_worst_wc", ""))
        conf = float(r.get(conf_col, 0.5)) if conf_col else 0.5

        action_type = _select_action_type(top_driver, avg_risk, maint_sev, has_protect, caution)

        # Enforce action_policy minimum_risk_threshold — downgrade to wait if below threshold
        min_thresh = policy_thresholds.get(action_type, 0.0)
        if avg_risk < min_thresh:
            action_type = "wait"

        # action_score: blend avg_action_score with risk level
        base_score = float(r.get("avg_action_score", avg_risk))
        action_score = round(min(1.0, base_score * (1.05 if caution else 1.0)), 6)

        # recommended_target_plant: only for reroute, per-source-plant lookup
        reroute_key = (str(r["scope_id"]), str(r["scenario"]), str(r["quarter_id"]), str(r["plant"]))
        rec_target = reroute_map.get(reroute_key, "") if action_type == "reroute" else ""

        # material_or_wc: use worst WC for capacity/maintenance actions
        # (rec_target is already guaranteed ≠ source plant by _build_reroute_map)
        material_or_wc = worst_wc if action_type in (
            "shift_maintenance", "protect_capacity_window", "upshift",
            "split_production", "escalate", "reschedule",
        ) else ""

        reason = _REASONS.get(action_type, "")
        if caution and action_type not in ("wait",):
            reason += " (carry-over service caution from prior quarter)"

        expected_effect = _EXPECTED_EFFECTS.get(action_type, "")

        trace = json.dumps({
            "top_driver": top_driver,
            "avg_risk": round(avg_risk, 4),
            "maint_severity": maint_sev,
            "has_protect_opportunity": has_protect,
            "caution_carry_over": caution,
            "action_selected": action_type,
        }, separators=(",", ":"))

        return {
            "scope_id": r["scope_id"],
            "scenario": r["scenario"],
            "quarter_id": r["quarter_id"],
            "action_type": action_type,
            "action_score": action_score,
            "project_id": r["project_id"],
            "plant": r["plant"],
            "material_or_wc": material_or_wc,
            "recommended_target_plant": rec_target,
            "reason": reason,
            "expected_effect": expected_effect,
            "confidence": round(conf, 6),
            "explanation_trace": trace,
        }

    records = [_make_row(r) for _, r in agg.iterrows()]
    result = pd.DataFrame(records, columns=_REQUIRED_COLS)

    # --- 8. Deduplicate on natural key ---
    key_cols = ["scope_id", "scenario", "quarter_id", "project_id", "plant"]
    result = result.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)

    # --- 9. Sort for demo-readiness (high action_score first) ---
    result = result.sort_values("action_score", ascending=False).reset_index(drop=True)

    return result
