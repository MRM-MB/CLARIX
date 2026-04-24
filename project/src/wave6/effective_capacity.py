"""
effective_capacity.py
=====================
Wave 6 Lara: Build fact_effective_capacity_weekly_v2 and fact_maintenance_impact_summary.

One concern: subtract maintenance/downtime from nominal capacity to produce
effective capacity, then summarise before/after impact per WC.
Inner functions _apply_downtime() and _build_impact_summary() are I/O-free.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WARN_THRESHOLD = 0.85

_EFFECTIVE_COLS = [
    "scope_id",
    "scenario",
    "plant",
    "work_center",
    "week",
    "nominal_available_capacity_hours",
    "scheduled_maintenance_hours",
    "downtime_buffer_hours",
    "effective_available_capacity_hours",
    "total_load_hours",
    "overload_hours",
    "overload_pct",
    "bottleneck_flag",
]

_IMPACT_COLS = [
    "scope_id",
    "scenario",
    "plant",
    "work_center",
    "nominal_avg_available_hours",
    "effective_avg_available_hours",
    "avg_maintenance_reduction_hours",
    "pct_capacity_lost_to_maintenance",
    "effective_bottleneck_weeks",
    "nominal_bottleneck_weeks",
    "delta_avg_overload_hours",
    "worst_week",
    "impact_severity",
]


def _apply_downtime(
    scoped: pd.DataFrame,
    calendar: pd.DataFrame,
    base_scenario: str = "expected_value",
) -> pd.DataFrame:
    """Apply maintenance downtime to nominal capacity.

    For each maintenance scenario in the calendar, takes the nominal capacity
    from `base_scenario` in scoped, subtracts scheduled + unscheduled downtime,
    and recomputes load metrics.

    Invariant: effective_available_capacity_hours ≤ nominal_available_capacity_hours.

    Args:
        scoped:        fact_scoped_capacity_weekly
        calendar:      fact_maintenance_downtime_calendar
        base_scenario: which base scenario's nominal capacity to use

    Returns:
        fact_effective_capacity_weekly_v2
    """
    if scoped.empty or calendar.empty:
        return pd.DataFrame(columns=_EFFECTIVE_COLS)

    # Take the base scenario's nominal capacity + load values
    base_mask = scoped["scenario"] == base_scenario
    if not base_mask.any():
        # Fallback: use first available scenario
        base_scenario = scoped["scenario"].iloc[0]
        base_mask = scoped["scenario"] == base_scenario

    base = scoped[base_mask][
        ["scope_id", "plant", "work_center", "week",
         "available_capacity_hours", "total_load_hours"]
    ].copy()
    base = base.rename(columns={"available_capacity_hours": "nominal_available_capacity_hours"})

    # Merge calendar onto base (one row per maintenance scenario × base WC-week)
    merged = calendar.merge(
        base,
        on=["scope_id", "plant", "work_center", "week"],
        how="inner",
    )

    if merged.empty:
        return pd.DataFrame(columns=_EFFECTIVE_COLS)

    nominal = merged["nominal_available_capacity_hours"]
    sched = merged["scheduled_maintenance_hours"]
    unsched = merged["unscheduled_downtime_buffer_hours"]

    effective = (nominal - sched - unsched).clip(lower=0.0)
    # Ensure effective never exceeds nominal (invariant)
    effective = effective.clip(upper=nominal)

    total_load = merged["total_load_hours"].fillna(0.0)
    overload = (total_load - effective).clip(lower=0.0)
    overload_pct = (overload / effective.clip(lower=0.001)).round(6)
    bottleneck = overload_pct >= WARN_THRESHOLD

    out = pd.DataFrame({
        "scope_id": merged["scope_id"].values,
        "scenario": merged["scenario"].values,
        "plant": merged["plant"].values,
        "work_center": merged["work_center"].values,
        "week": merged["week"].values,
        "nominal_available_capacity_hours": nominal.round(4).values,
        "scheduled_maintenance_hours": sched.round(4).values,
        "downtime_buffer_hours": unsched.round(4).values,
        "effective_available_capacity_hours": effective.round(4).values,
        "total_load_hours": total_load.round(4).values,
        "overload_hours": overload.round(4).values,
        "overload_pct": overload_pct.values,
        "bottleneck_flag": bottleneck.values,
    })

    return out[_EFFECTIVE_COLS].reset_index(drop=True)


def _build_impact_summary(
    effective: pd.DataFrame,
    scoped: pd.DataFrame,
    base_scenario: str = "expected_value",
) -> pd.DataFrame:
    """Compare effective capacity vs nominal and produce before/after summary.

    Args:
        effective: fact_effective_capacity_weekly_v2
        scoped:    fact_scoped_capacity_weekly (nominal baseline)
        base_scenario: which scenario in scoped to use as nominal

    Returns:
        fact_maintenance_impact_summary
    """
    if effective.empty or scoped.empty:
        return pd.DataFrame(columns=_IMPACT_COLS)

    # Nominal bottleneck weeks from base scoped scenario
    base = scoped[scoped["scenario"] == base_scenario].copy()
    if base.empty:
        base = scoped.copy()

    # Compute nominal overload hours: max(0, total_load - available_capacity)
    base["_nominal_overload"] = (base["total_load_hours"].fillna(0.0) - base["available_capacity_hours"]).clip(lower=0.0)

    nominal_agg = (
        base.groupby(["scope_id", "plant", "work_center"], as_index=False)
        .agg(
            nominal_avg_available_hours=("available_capacity_hours", "mean"),
            nominal_bottleneck_weeks=("bottleneck_flag", "sum"),
            avg_nominal_overload_hours=("_nominal_overload", "mean"),
        )
    )
    nominal_agg["nominal_bottleneck_weeks"] = nominal_agg["nominal_bottleneck_weeks"].astype(int)

    # Effective summary per (scope_id, scenario, plant, work_center)
    eff_agg = (
        effective.groupby(["scope_id", "scenario", "plant", "work_center"], as_index=False)
        .agg(
            effective_avg_available_hours=("effective_available_capacity_hours", "mean"),
            avg_maintenance_reduction_hours=("scheduled_maintenance_hours", "mean"),
            effective_bottleneck_weeks=("bottleneck_flag", "sum"),
            avg_effective_overload_hours=("overload_hours", "mean"),
            worst_week=("overload_hours", "idxmax"),
        )
    )
    eff_agg["effective_bottleneck_weeks"] = eff_agg["effective_bottleneck_weeks"].astype(int)

    # Get worst week string (week with highest overload hours)
    week_lookup = effective[["scope_id", "scenario", "plant", "work_center", "week", "overload_hours"]].copy()
    worst_week_map: dict[tuple, str] = {}
    for key, grp in week_lookup.groupby(["scope_id", "scenario", "plant", "work_center"]):
        if not grp.empty:
            idx = grp["overload_hours"].idxmax()
            worst_week_map[key] = grp.loc[idx, "week"]

    eff_agg["worst_week"] = eff_agg.apply(
        lambda r: worst_week_map.get(
            (r["scope_id"], r["scenario"], r["plant"], r["work_center"]), "N/A"
        ),
        axis=1,
    )

    # Merge nominal into effective summary
    result = eff_agg.merge(nominal_agg, on=["scope_id", "plant", "work_center"], how="left")

    result["nominal_avg_available_hours"] = result["nominal_avg_available_hours"].fillna(0.0)
    result["nominal_bottleneck_weeks"] = result["nominal_bottleneck_weeks"].fillna(0).astype(int)

    result["pct_capacity_lost_to_maintenance"] = (
        result["avg_maintenance_reduction_hours"] /
        result["nominal_avg_available_hours"].clip(lower=0.001)
    ).clip(0.0, 1.0).round(4)

    # delta_avg_overload_hours: positive = maintenance made things worse
    result["delta_avg_overload_hours"] = (
        result["avg_effective_overload_hours"].fillna(0.0)
        - result["avg_nominal_overload_hours"].fillna(0.0)
    ).round(4)

    # Severity: based on pct capacity lost
    def _severity(pct: float) -> str:
        if pct >= 0.20:
            return "high"
        if pct >= 0.10:
            return "medium"
        if pct > 0.0:
            return "low"
        return "none"

    result["impact_severity"] = result["pct_capacity_lost_to_maintenance"].apply(_severity)

    return result[_IMPACT_COLS].reset_index(drop=True)


def build_fact_effective_capacity_weekly_v2(
    scoped: pd.DataFrame,
    calendar: pd.DataFrame,
    base_scenario: str = "expected_value",
) -> pd.DataFrame:
    """Public entry point."""
    return _apply_downtime(scoped, calendar, base_scenario)


def build_fact_maintenance_impact_summary(
    effective: pd.DataFrame,
    scoped: pd.DataFrame,
    base_scenario: str = "expected_value",
) -> pd.DataFrame:
    """Public entry point."""
    return _build_impact_summary(effective, scoped, base_scenario)
