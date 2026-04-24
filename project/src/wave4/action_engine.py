"""
action_engine.py
================
Wave 4 Lara: Planner Action Engine.

One concern: evaluate action policy triggers against integrated risk and
produce fact_planner_actions with explainable, traceable recommendations.

Inner function _apply_actions() is I/O-free and fully testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

GENERATION_VERSION = "wave4_actions_v1"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Plant peer groups for recommended_target_plant (reroute / split_production)
_PLANT_GROUPS: dict[str, list[str]] = {
    "EU": ["NW02", "NW03", "NW08", "NW09", "NW10"],
    "US": ["NW01", "NW06", "NW07"],
    "APAC": ["NW04", "NW05", "NW15"],
    "LATAM": ["NW12", "NW13"],
    "OTHER": ["NW11", "NW14"],
}

_CAPACITY_ACTIONS = {"upshift", "reschedule", "split_production", "escalate"}
_SOURCING_ACTIONS = {"buy_now", "hedge_inventory"}
_LOGISTICS_ACTIONS = {"reroute", "expedite_shipping"}
_ALT_PLANT_ACTIONS = {"reroute", "split_production"}

_OUTPUT_COLUMNS = [
    "scenario",
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

# ---------------------------------------------------------------------------
# Trigger definitions — explicit boolean conditions per action type
# Each maps to a function(risk_df) -> pd.Series[bool]
# ---------------------------------------------------------------------------

_TRIGGERS: dict[str, object] = {
    "buy_now": lambda r: (
        (r["sourcing_risk_score"] >= 0.70)
        & (r["priority_score"] >= 0.30)
        & (r["risk_score_base"] >= 0.60)
    ),
    "wait": lambda r: (
        (r["risk_score_base"] < 0.30)
        & (r["priority_score"] < 0.40)
    ),
    "reroute": lambda r: (
        (r["logistics_risk_score"] >= 0.50)
        & (r["priority_score"] >= 0.40)
        & (r["risk_score_base"] >= 0.40)
    ),
    "upshift": lambda r: (
        (r["capacity_risk_score"] >= 0.80)
        & (r["priority_score"] >= 0.30)
        & (r["risk_score_base"] >= 0.50)
    ),
    "expedite_shipping": lambda r: (
        (r["logistics_risk_score"] >= 0.60)
        & (r["priority_score"] >= 0.50)
        & (r["risk_score_base"] >= 0.50)
    ),
    "reschedule": lambda r: (
        (r["capacity_risk_score"] >= 0.60)
        & (r["priority_score"] < 0.50)
        & (r["risk_score_base"] >= 0.40)
    ),
    "escalate": lambda r: (
        (r["action_score_base"] >= 0.80)
        & (r["top_driver"].isin(["capacity_risk", "sourcing_risk"]))
        & (r["priority_score"] >= 0.70)
    ),
    "hedge_inventory": lambda r: (
        (r["sourcing_risk_score"] >= 0.50)
        & (r["priority_score"] >= 0.20)
        & (r["risk_score_base"] >= 0.30)
    ),
    "split_production": lambda r: (
        (r["capacity_risk_score"] >= 0.70)
        & (r["priority_score"] >= 0.40)
        & (r["risk_score_base"] >= 0.60)
    ),
}

# Human-readable reason template per action
_REASON_TEMPLATES: dict[str, str] = {
    "buy_now":          "sourcing_risk={src:.2f}≥0.70; priority={pri:.2f}≥0.30; risk_base={rsk:.2f}≥0.60",
    "wait":             "risk_base={rsk:.2f}<0.30; priority={pri:.2f}<0.40 — low urgency",
    "reroute":          "logistics_risk={log:.2f}≥0.50; priority={pri:.2f}≥0.40 — reroute eligible",
    "upshift":          "capacity_risk={cap:.2f}≥0.80; priority={pri:.2f}≥0.30 — shift lever available",
    "expedite_shipping": "logistics_risk={log:.2f}≥0.60; priority={pri:.2f}≥0.50 — expedite eligible",
    "reschedule":       "capacity_risk={cap:.2f}≥0.60; priority={pri:.2f}<0.50 — defer to relieve load",
    "escalate":         "action_score={asc:.2f}≥0.80; top_driver={drv}; priority={pri:.2f}≥0.70",
    "hedge_inventory":  "sourcing_risk={src:.2f}≥0.50; priority={pri:.2f}≥0.20 — buffer stock advised",
    "split_production": "capacity_risk={cap:.2f}≥0.70; priority={pri:.2f}≥0.40 — split across plants",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_quality_penalty_index(quality_flags: pd.DataFrame) -> pd.DataFrame:
    """Aggregate weaken-severity quality penalties by (scenario, plant).

    Returns a DataFrame with columns: scenario, plant, total_weaken_penalty, has_block.
    block-severity flags force confidence to 0.
    """
    if quality_flags.empty:
        return pd.DataFrame(columns=["scenario", "plant", "total_weaken_penalty", "has_block"])

    def _parse_key(key: str) -> tuple[str, str]:
        parts = str(key).split("|")
        return parts[0], parts[1] if len(parts) > 1 else "UNKNOWN"

    parsed = quality_flags["entity_key"].apply(_parse_key)
    qf = quality_flags.copy()
    qf["_scenario"] = [p[0] for p in parsed]
    qf["_plant"] = [p[1] for p in parsed]

    weaken = qf[qf["recommended_handling"] == "weaken"].copy()
    block = qf[qf["recommended_handling"] == "block"].copy()

    agg_weaken = (
        weaken.groupby(["_scenario", "_plant"], as_index=False)["penalty_score"]
        .sum()
        .rename(columns={"_scenario": "scenario", "_plant": "plant", "penalty_score": "total_weaken_penalty"})
    ) if not weaken.empty else pd.DataFrame(columns=["scenario", "plant", "total_weaken_penalty"])

    block_plants = set()
    if not block.empty:
        block_plants = set(zip(block["_scenario"], block["_plant"]))

    if not agg_weaken.empty:
        agg_weaken["has_block"] = agg_weaken.apply(
            lambda r: (r["scenario"], r["plant"]) in block_plants, axis=1
        )
    else:
        agg_weaken = pd.DataFrame(columns=["scenario", "plant", "total_weaken_penalty", "has_block"])

    return agg_weaken


def _build_bottleneck_wc_index(bottleneck: pd.DataFrame) -> dict[tuple, str]:
    """Return (scenario, plant) → worst work_center string."""
    if bottleneck.empty or "work_center" not in bottleneck.columns:
        return {}
    # Prefer critical severity, then warning; take first occurrence
    sev_order = {"critical": 0, "warning": 1}
    bn = bottleneck.copy()
    bn["_sev_rank"] = bn.get("bottleneck_severity", pd.Series("warning", index=bn.index)).map(
        lambda x: sev_order.get(str(x).lower(), 2)
    )
    bn = bn.sort_values("_sev_rank")
    return {
        (row["scenario"], row["plant"]): row["work_center"]
        for _, row in bn.drop_duplicates(["scenario", "plant"], keep="first").iterrows()
    }


def _build_disruption_index(resilience: pd.DataFrame) -> pd.DataFrame:
    """Aggregate max disruption_risk_score per (scenario, plant, week)."""
    if resilience.empty:
        return pd.DataFrame(columns=["scenario", "plant", "week", "max_disruption_risk"])
    return (
        resilience.groupby(["scenario", "plant", "week"], as_index=False)["disruption_risk_score"]
        .max()
        .rename(columns={"disruption_risk_score": "max_disruption_risk"})
    )


def _suggest_alt_plant(plant: str) -> str:
    """Suggest a peer plant from the same geographic group."""
    for plants in _PLANT_GROUPS.values():
        if plant in plants:
            alts = [p for p in plants if p != plant]
            return alts[0] if alts else "N/A"
    return "N/A"


def _material_or_wc(action_type: str, plant: str, scenario: str, wc_index: dict) -> str:
    if action_type in _CAPACITY_ACTIONS:
        return wc_index.get((scenario, plant), "WC_NOT_SPECIFIED")
    if action_type in _SOURCING_ACTIONS:
        return "ALL_MATERIALS_AT_PLANT"
    if action_type in _LOGISTICS_ACTIONS:
        return "LOGISTICS_LANE"
    return "N/A"


def _confidence_label(score: float, has_block: bool) -> str:
    if has_block or score <= 0.0:
        return "low"
    if score >= 0.60:
        return "high"
    if score >= 0.30:
        return "medium"
    return "low"


def _build_reason(action_type: str, row: "pd.Series") -> str:
    tmpl = _REASON_TEMPLATES.get(action_type, "triggered by policy {action}")
    try:
        return tmpl.format(
            src=float(row.get("sourcing_risk_score", 0)),
            pri=float(row.get("priority_score", 0)),
            rsk=float(row.get("risk_score_base", 0)),
            log=float(row.get("logistics_risk_score", 0)),
            cap=float(row.get("capacity_risk_score", 0)),
            asc=float(row.get("action_score_base", 0)),
            drv=str(row.get("top_driver", "unknown")),
            action=action_type,
        )
    except Exception:
        return f"triggered_by={action_type}"


def _build_trace(
    action_type: str,
    row: "pd.Series",
    raw_score: float,
    penalty: float,
    final_score: float,
    max_disruption: float,
) -> str:
    return (
        f"action={action_type}; "
        f"triggered_by=top_driver={row.get('top_driver','?')}; "
        f"capacity={row.get('capacity_risk_score',0):.3f}; "
        f"sourcing={row.get('sourcing_risk_score',0):.3f}; "
        f"logistics={row.get('logistics_risk_score',0):.3f}; "
        f"priority={row.get('priority_score',0):.3f}; "
        f"action_score_raw={raw_score:.3f}; "
        f"quality_penalty={penalty:.3f}; "
        f"max_disruption_risk={max_disruption:.3f}; "
        f"action_score_final={final_score:.3f}"
    )


# ---------------------------------------------------------------------------
# Core inner function
# ---------------------------------------------------------------------------

def _apply_actions(
    risk: pd.DataFrame,
    policy: pd.DataFrame,
    bottleneck: pd.DataFrame,
    quality_flags: pd.DataFrame,
    resilience: pd.DataFrame,
) -> pd.DataFrame:
    """Apply action policies to integrated risk and produce planner actions.

    I/O-free inner function — testable without file system.

    Args:
        risk:          fact_integrated_risk_base
        policy:        dim_action_policy
        bottleneck:    fact_capacity_bottleneck_summary
        quality_flags: fact_data_quality_flags
        resilience:    fact_scenario_resilience_impact

    Returns:
        fact_planner_actions DataFrame
    """
    if risk.empty or policy.empty:
        return _empty_actions()

    # Pre-build indexes
    penalty_index = _build_quality_penalty_index(quality_flags)
    wc_index = _build_bottleneck_wc_index(bottleneck)
    disruption_idx = _build_disruption_index(resilience)

    # Merge penalty into risk
    risk = risk.copy()
    if not penalty_index.empty:
        risk = risk.merge(
            penalty_index[["scenario", "plant", "total_weaken_penalty", "has_block"]],
            on=["scenario", "plant"], how="left",
        )
    else:
        risk["total_weaken_penalty"] = 0.0
        risk["has_block"] = False
    risk["total_weaken_penalty"] = risk["total_weaken_penalty"].fillna(0.0).clip(0.0, 1.0)
    risk["has_block"] = risk["has_block"].fillna(False).infer_objects(copy=False)

    # Merge disruption max risk
    if not disruption_idx.empty:
        risk = risk.merge(disruption_idx, on=["scenario", "plant", "week"], how="left")
    else:
        risk["max_disruption_risk"] = 0.0
    risk["max_disruption_risk"] = risk["max_disruption_risk"].fillna(0.0)

    # Build policy lookup
    policy_lookup: dict[str, dict] = {
        row["action_type"]: row.to_dict()
        for _, row in policy.iterrows()
    }

    frames: list[pd.DataFrame] = []

    for action_type, trigger_fn in _TRIGGERS.items():
        pol = policy_lookup.get(action_type, {})
        expected_effect = pol.get("expected_effect_type", "unknown")

        # Evaluate trigger mask
        try:
            mask = trigger_fn(risk)
        except Exception:
            continue

        subset = risk[mask].copy()
        if subset.empty:
            continue

        # Action score = action_score_base - quality_penalty + disruption_boost, clamped
        disruption_boost = subset["max_disruption_risk"] * 0.10
        raw_score = subset["action_score_base"].clip(0.0, 1.0)
        penalty = subset["total_weaken_penalty"].clip(0.0, 1.0)
        final_score = (raw_score - penalty * 0.20 + disruption_boost).clip(0.0, 1.0).round(6)

        # Build output frame
        frame = pd.DataFrame(index=subset.index)
        frame["scenario"] = subset["scenario"].values
        frame["action_type"] = action_type
        frame["action_score"] = final_score.values
        frame["project_id"] = subset.get("project_id", pd.Series(dtype="object")).values
        frame["plant"] = subset["plant"].values
        frame["material_or_wc"] = [
            _material_or_wc(action_type, p, s, wc_index)
            for p, s in zip(subset["plant"], subset["scenario"])
        ]
        frame["recommended_target_plant"] = [
            _suggest_alt_plant(p) if action_type in _ALT_PLANT_ACTIONS else "N/A"
            for p in subset["plant"]
        ]
        frame["reason"] = [_build_reason(action_type, row) for _, row in subset.iterrows()]
        frame["expected_effect"] = expected_effect
        frame["confidence"] = [
            _confidence_label(s, b)
            for s, b in zip(final_score, subset["has_block"])
        ]
        frame["explanation_trace"] = [
            _build_trace(action_type, row, raw_score.iloc[i], penalty.iloc[i],
                         final_score.iloc[i], subset["max_disruption_risk"].iloc[i])
            for i, (_, row) in enumerate(subset.iterrows())
        ]
        frames.append(frame)

    if not frames:
        return _empty_actions()

    result = pd.concat(frames, ignore_index=True)[_OUTPUT_COLUMNS]
    return result.sort_values("action_score", ascending=False).reset_index(drop=True)


def _empty_actions() -> pd.DataFrame:
    return pd.DataFrame(columns=_OUTPUT_COLUMNS)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_fact_planner_actions(
    risk: pd.DataFrame,
    policy: pd.DataFrame,
    bottleneck: pd.DataFrame,
    quality_flags: pd.DataFrame,
    resilience: pd.DataFrame,
) -> pd.DataFrame:
    """Build fact_planner_actions from all Wave 3/4 inputs."""
    return _apply_actions(risk, policy, bottleneck, quality_flags, resilience)
