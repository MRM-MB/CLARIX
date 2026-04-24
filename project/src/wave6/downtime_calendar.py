"""
downtime_calendar.py
====================
Wave 6 Lara: Build fact_maintenance_downtime_calendar.

One concern: expand maintenance policy into a per-week downtime schedule
for each (scope_id, scenario, plant, work_center, week).
Inner function _build_calendar() is I/O-free and fully testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# The 4 maintenance scenarios and their multiplier profiles
MAINTENANCE_SCENARIOS: dict[str, dict] = {
    "baseline_maintenance": {
        "scheduled_multiplier": 1.0,
        "interval_multiplier": 1.0,
        "unscheduled_buffer_factor": 0.0,
        "description": "Nominal maintenance schedule per policy",
    },
    "maintenance_overrun": {
        "scheduled_multiplier": 1.5,
        "interval_multiplier": 1.0,
        "unscheduled_buffer_factor": 0.05,
        "description": "Maintenance takes 50% longer + small unscheduled component",
    },
    "unexpected_breakdown": {
        "scheduled_multiplier": 1.0,
        "interval_multiplier": 1.0,
        "unscheduled_buffer_factor": 0.25,
        "description": "On top of scheduled, 25% of nominal capacity lost to random breakdowns",
    },
    "preventive_maintenance_shift": {
        "scheduled_multiplier": 0.70,
        "interval_multiplier": 0.75,
        "unscheduled_buffer_factor": 0.0,
        "description": "More frequent (75% interval) but shorter (70% duration) events",
    },
}

_CALENDAR_COLS = [
    "scope_id",
    "scenario",
    "plant",
    "work_center",
    "week",
    "scheduled_maintenance_hours",
    "unscheduled_downtime_buffer_hours",
    "maintenance_source_type",
    "synthetic_flag",
]


def _week_str_to_num(week: str) -> int:
    """Extract ISO week number from string like '2026-W01' → 1."""
    try:
        return int(week.split("-W")[1])
    except Exception:
        return 1


def _phase_offset(plant: str, work_center: str, seed: int = 42) -> int:
    """Deterministic phase offset so maintenance weeks are staggered across WCs."""
    rng = np.random.default_rng(seed + hash(f"{plant}_{work_center}") % (2**31))
    return int(rng.integers(0, 20))


def _build_calendar(
    scoped: pd.DataFrame,
    policy: pd.DataFrame,
) -> pd.DataFrame:
    """Build fact_maintenance_downtime_calendar.

    For each (plant, work_center, week) in scoped capacity and each maintenance
    scenario, computes scheduled_maintenance_hours and unscheduled_downtime_buffer_hours.

    A maintenance event occurs when (week_num + phase_offset) % effective_interval == 0.

    Args:
        scoped: fact_scoped_capacity_weekly — provides (scope_id, plant, wc, week, available_hours)
        policy: dim_maintenance_policy_synth — provides (plant, wc, interval, downtime)

    Returns:
        fact_maintenance_downtime_calendar
    """
    if scoped.empty or policy.empty:
        return pd.DataFrame(columns=_CALENDAR_COLS)

    # Build policy lookup: (plant, wc) → (interval_weeks, downtime_hours, trigger_type)
    pol_idx: dict[tuple, tuple] = {}
    for _, row in policy.iterrows():
        key = (str(row["plant"]), str(row["work_center"]))
        pol_idx[key] = (
            int(row["estimated_interval_weeks_synth"]),
            float(row["expected_downtime_hours_synth"]),
            str(row["maintenance_trigger_type"]),
        )

    # Get unique (scope_id, plant, wc, week, available_capacity_hours)
    # Use one representative base scenario to avoid row explosion
    base_mask = scoped["scenario"].isin(["expected_value", "all_in"])
    base = scoped[base_mask].copy() if base_mask.any() else scoped.copy()
    week_rows = (
        base.groupby(["scope_id", "plant", "work_center", "week"], as_index=False)["available_capacity_hours"]
        .mean()
    )

    frames: list[pd.DataFrame] = []

    for maint_scenario, profile in MAINTENANCE_SCENARIOS.items():
        sched_mult = float(profile["scheduled_multiplier"])
        interval_mult = float(profile["interval_multiplier"])
        unscheduled_factor = float(profile["unscheduled_buffer_factor"])

        rows = []
        for _, wr in week_rows.iterrows():
            plant = str(wr["plant"])
            wc = str(wr["work_center"])
            week = str(wr["week"])
            scope_id = str(wr["scope_id"])
            nominal = float(wr["available_capacity_hours"])

            pol = pol_idx.get((plant, wc))
            if pol is None:
                # Default: 8-week scheduled, 4h downtime
                base_interval, base_downtime, trigger = 8, 4.0, "scheduled_preventive"
            else:
                base_interval, base_downtime, trigger = pol

            effective_interval = max(1, round(base_interval * interval_mult))
            effective_downtime = base_downtime * sched_mult

            week_num = _week_str_to_num(week)
            phase = _phase_offset(plant, wc)
            event_occurs = ((week_num + phase) % effective_interval) == 0

            scheduled_hours = effective_downtime if event_occurs else 0.0
            unscheduled_hours = nominal * unscheduled_factor

            rows.append({
                "scope_id": scope_id,
                "scenario": maint_scenario,
                "plant": plant,
                "work_center": wc,
                "week": week,
                "scheduled_maintenance_hours": round(scheduled_hours, 4),
                "unscheduled_downtime_buffer_hours": round(unscheduled_hours, 4),
                "maintenance_source_type": trigger,
                "synthetic_flag": True,
            })

        frames.append(pd.DataFrame(rows))

    if not frames:
        return pd.DataFrame(columns=_CALENDAR_COLS)

    return pd.concat(frames, ignore_index=True)[_CALENDAR_COLS]


def build_fact_maintenance_downtime_calendar(
    scoped: pd.DataFrame,
    policy: pd.DataFrame,
) -> pd.DataFrame:
    """Public entry point."""
    return _build_calendar(scoped, policy)
