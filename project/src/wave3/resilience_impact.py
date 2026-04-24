"""
resilience_impact.py
====================
Wave 3 Lara: Applies disruption multipliers to base risk and produces
fact_scenario_resilience_impact with before/after deltas and mitigation candidates.

One concern: compute disruption impact deltas from base risk + catalog.
Inner function _apply_disruption() is I/O-free and fully testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

GENERATION_VERSION = "wave3_resilience_v1"

# Weights for disruption_risk_score composite (delta-based)
_DELTA_WEIGHTS = {
    "delta_capacity_risk": 0.40,
    "delta_sourcing_risk": 0.30,
    "delta_logistics_risk": 0.30,
}

_OUTPUT_COLUMNS = [
    "scenario",
    "project_id_if_available",
    "plant",
    "week",
    "affected_branch",
    "delta_capacity_risk",
    "delta_sourcing_risk",
    "delta_logistics_risk",
    "disruption_risk_score",
    "mitigation_candidate",
    "explanation_note",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_affected_plants(affected_plants: str) -> set[str]:
    val = affected_plants.strip().upper()
    if val == "ALL":
        return {"ALL"}
    return {p.strip() for p in affected_plants.split(",")}


def _compute_disrupted_scores(
    base_cap: "pd.Series",
    base_src: "pd.Series",
    base_log: "pd.Series",
    cap_mult: float,
    lt_mult: float,
    rel_pen: float,
    cost_mult: float,
) -> tuple["pd.Series", "pd.Series", "pd.Series"]:
    """Vectorised disruption math. Returns (dis_cap, dis_src, dis_log) clamped [0,1].

    Capacity risk:
        When cap_mult < 1 the plant loses capacity → overload risk rises.
        Risk = base_risk / cap_mult (approaches 1 as cap_mult → 0; hard cap at 1).
        When cap_mult >= 1, capacity is unaffected.

    Sourcing risk:
        Longer lead times reduce coverage → risk = base_risk × lead_time_multiplier.

    Logistics risk:
        Reliability penalty + shipping cost premium compound existing risk.
        factor = 1 + reliability_penalty + (cost_mult - 1) × 0.10
    """
    # Capacity
    if cap_mult < 1.0:
        cap_factor = 1.0 / max(cap_mult, 0.001)
    else:
        cap_factor = 1.0
    dis_cap = (base_cap * cap_factor).clip(0.0, 1.0)

    # Sourcing
    dis_src = (base_src * lt_mult).clip(0.0, 1.0)

    # Logistics
    log_factor = 1.0 + rel_pen + (cost_mult - 1.0) * 0.10
    dis_log = (base_log * log_factor).clip(0.0, 1.0)

    return dis_cap, dis_src, dis_log


def _select_mitigation_vectorised(
    delta_cap: "pd.Series",
    delta_src: "pd.Series",
    delta_log: "pd.Series",
    cap_mult: float,
) -> "pd.Series":
    """Assign mitigation candidate label per row, fully vectorised.

    Priority:
        1. plant_outage (cap_mult == 0) → reschedule
        2. capacity dominant and meaningful → upshift
        3. logistics dominant and meaningful → reroute
        4. sourcing dominant and meaningful → expedite
        5. no meaningful impact → no_action_needed
        6. all else → monitor
    """
    THRESH = 0.01

    conditions = [
        cap_mult == 0.0,
        (delta_cap >= delta_src) & (delta_cap >= delta_log) & (delta_cap > THRESH),
        (delta_log >= delta_cap) & (delta_log >= delta_src) & (delta_log > THRESH),
        (delta_src >= delta_cap) & (delta_src >= delta_log) & (delta_src > THRESH),
        (delta_cap <= THRESH) & (delta_src <= THRESH) & (delta_log <= THRESH),
    ]
    choices = ["reschedule", "upshift", "reroute", "expedite", "no_action_needed"]
    return pd.Series(
        np.select(conditions, choices, default="monitor"),
        index=delta_cap.index,
    )


def _build_explanation_series(
    disruption_name: str,
    plant: "pd.Series",
    delta_cap: "pd.Series",
    delta_src: "pd.Series",
    delta_log: "pd.Series",
    disruption_risk: "pd.Series",
    mitigation: "pd.Series",
) -> "pd.Series":
    return (
        "disruption=" + disruption_name + "; plant=" + plant.astype(str) + "; "
        + "Δcapacity=" + delta_cap.round(3).astype(str) + "; "
        + "Δsourcing=" + delta_src.round(3).astype(str) + "; "
        + "Δlogistics=" + delta_log.round(3).astype(str) + "; "
        + "disruption_risk=" + disruption_risk.round(3).astype(str) + "; "
        + "mitigation=" + mitigation.astype(str)
    )


# ---------------------------------------------------------------------------
# Core inner function
# ---------------------------------------------------------------------------

def _apply_disruption(
    base_risk: pd.DataFrame,
    catalog: pd.DataFrame,
) -> pd.DataFrame:
    """Apply each disruption scenario to base risk rows.

    I/O-free inner function — testable without file system.

    Args:
        base_risk: fact_integrated_risk_base with at minimum:
            scenario, project_id, plant, week,
            capacity_risk_score, sourcing_risk_score, logistics_risk_score
        catalog: dim_disruption_scenario_synth

    Returns:
        fact_scenario_resilience_impact DataFrame
    """
    if base_risk.empty or catalog.empty:
        return _empty_impact()

    all_plants = set(base_risk["plant"].dropna().unique())
    frames: list[pd.DataFrame] = []

    for _, dis in catalog.iterrows():
        affected = _parse_affected_plants(str(dis["affected_plants"]))

        if "ALL" in affected:
            subset = base_risk.copy()
        else:
            subset = base_risk[base_risk["plant"].isin(affected)].copy()

        if subset.empty:
            continue

        cap_mult = float(dis["available_capacity_multiplier"])
        lt_mult = float(dis["lead_time_multiplier"])
        rel_pen = float(dis["reliability_penalty"])
        cost_mult = float(dis["shipping_cost_multiplier"])
        dis_name = str(dis["scenario_name"])

        base_cap = subset["capacity_risk_score"].fillna(0.0).clip(0.0, 1.0)
        base_src = subset["sourcing_risk_score"].fillna(0.0).clip(0.0, 1.0)
        base_log = subset["logistics_risk_score"].fillna(0.0).clip(0.0, 1.0)

        dis_cap, dis_src, dis_log = _compute_disrupted_scores(
            base_cap, base_src, base_log,
            cap_mult, lt_mult, rel_pen, cost_mult,
        )

        delta_cap = (dis_cap - base_cap).round(6)
        delta_src = (dis_src - base_src).round(6)
        delta_log = (dis_log - base_log).round(6)

        disruption_risk = (
            _DELTA_WEIGHTS["delta_capacity_risk"] * delta_cap
            + _DELTA_WEIGHTS["delta_sourcing_risk"] * delta_src
            + _DELTA_WEIGHTS["delta_logistics_risk"] * delta_log
        ).clip(0.0, 1.0).round(6)

        mitigation = _select_mitigation_vectorised(delta_cap, delta_src, delta_log, cap_mult)
        note = _build_explanation_series(
            dis_name, subset["plant"],
            delta_cap, delta_src, delta_log,
            disruption_risk, mitigation,
        )

        frame = pd.DataFrame(index=subset.index)
        frame["scenario"] = subset["scenario"].values
        frame["project_id_if_available"] = subset.get("project_id", pd.Series(dtype="object")).values
        frame["plant"] = subset["plant"].values
        frame["week"] = subset["week"].values
        frame["affected_branch"] = dis_name
        frame["delta_capacity_risk"] = delta_cap.values
        frame["delta_sourcing_risk"] = delta_src.values
        frame["delta_logistics_risk"] = delta_log.values
        frame["disruption_risk_score"] = disruption_risk.values
        frame["mitigation_candidate"] = mitigation.values
        frame["explanation_note"] = note.values
        frames.append(frame)

    if not frames:
        return _empty_impact()

    return pd.concat(frames, ignore_index=True)[_OUTPUT_COLUMNS]


def _empty_impact() -> pd.DataFrame:
    return pd.DataFrame(columns=_OUTPUT_COLUMNS)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_fact_scenario_resilience_impact(
    base_risk: pd.DataFrame,
    catalog: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build fact_scenario_resilience_impact from integrated risk base + disruption catalog."""
    if catalog is None:
        from project.src.wave3.disruption_catalog import build_dim_disruption_scenario_synth
        catalog = build_dim_disruption_scenario_synth()
    return _apply_disruption(base_risk, catalog)
