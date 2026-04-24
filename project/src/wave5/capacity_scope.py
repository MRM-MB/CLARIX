"""
capacity_scope.py
=================
Wave 5 Lara: scoped regional capacity foundation and quarter-aware state layer.

One concern: filter capacity data to an MVP scope, aggregate to quarters,
and build a carry-over capacity history across consecutive quarters.

All inner functions are I/O-free and fully testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from project.src.wave5.scoped_filter import DEFAULT_SCOPE
from project.src.wave5.quarterly_snapshot import week_to_quarter

# Base scenarios only — exclude upside/downside variants for quarterly views
_BASE_SCENARIOS = {"all_in", "expected_value", "high_confidence"}

_SCOPED_WEEKLY_COLS = [
    "scope_id", "scenario", "plant", "work_center", "week",
    "available_capacity_hours", "planned_load_hours", "incremental_load_hours",
    "total_load_hours", "overload_hours", "overload_pct", "bottleneck_flag",
]

_QUARTERLY_COLS = [
    "scope_id", "quarter_id", "plant", "work_center",
    "total_available_capacity_hours", "total_planned_load_hours",
    "total_incremental_load_hours", "total_overload_hours",
    "bottleneck_weeks_count",
]

_HISTORY_COLS = [
    "scope_id", "quarter_id", "plant", "work_center",
    "prior_quarter_bottleneck_flag", "prior_quarter_overload_hours",
    "prior_quarter_mitigation_used", "carry_over_capacity_risk_flag",
    "learning_note",
]


# ---------------------------------------------------------------------------
# Quarter helpers
# ---------------------------------------------------------------------------

def _year_week_to_quarter(year: int, week: int) -> str:
    """Convert integer year + week to quarter string e.g. '2026-Q1'."""
    week_str = f"{int(year)}-W{int(week):02d}"
    return week_to_quarter(week_str)


def _quarter_sort_key(q: str) -> tuple[int, int]:
    """Return (year, quarter_num) for correct chronological sorting."""
    try:
        year_str, q_str = q.split("-Q")
        return int(year_str), int(q_str)
    except Exception:
        return 9999, 9


def _prior_quarter_id(quarter_id: str) -> str | None:
    """Return the immediately preceding quarter string, or None for Q1 of first year."""
    year, q = _quarter_sort_key(quarter_id)
    if q == 1:
        return f"{year - 1}-Q4"
    return f"{year}-Q{q - 1}"


# ---------------------------------------------------------------------------
# Inner functions (I/O-free)
# ---------------------------------------------------------------------------

def _scope_capacity_weekly(
    cap: pd.DataFrame,
    scope_id: str,
    plants: list[str],
    scenarios: list[str] | None = None,
) -> pd.DataFrame:
    """Filter fact_scenario_capacity_weekly to scope plants and add scope_id.

    Args:
        cap:      fact_scenario_capacity_weekly (grain: scenario × plant × wc × year × week)
        scope_id: label for this scope
        plants:   list of plant codes to include
        scenarios: if None, all scenarios included; otherwise filter to these

    Returns:
        fact_scoped_capacity_weekly with scope_id column and canonical column order.
        Row count is always ≤ input row count (validates at end).
    """
    if cap.empty:
        return pd.DataFrame(columns=_SCOPED_WEEKLY_COLS)

    out = cap.copy()

    if plants:
        out = out[out["plant"].isin(plants)]

    if scenarios is not None:
        out = out[out["scenario"].isin(scenarios)]

    out = out.copy()
    out["scope_id"] = scope_id

    # Build canonical week string from year + week integers
    if "week" in out.columns and "year" in out.columns:
        if out["week"].dtype != object or not out["week"].astype(str).str.contains("-W").any():
            out["week"] = out["year"].astype(int).astype(str) + "-W" + out["week"].astype(int).astype(str).str.zfill(2)

    # Ensure bottleneck_flag is bool
    out["bottleneck_flag"] = out["bottleneck_flag"].astype(bool)

    assert len(out) <= len(cap), (
        f"_scope_capacity_weekly: scoped rows ({len(out)}) > source rows ({len(cap)})"
    )

    # Select only columns that exist + scope_id
    available = [c for c in _SCOPED_WEEKLY_COLS if c in out.columns]
    return out[available].reset_index(drop=True)


def _aggregate_quarterly(
    scoped: pd.DataFrame,
    base_scenarios: set[str] = _BASE_SCENARIOS,
) -> pd.DataFrame:
    """Aggregate scoped weekly capacity into quarterly snapshots.

    Uses base scenarios only (excludes upside/downside variants).
    Aggregates over all base scenarios together (max bottleneck, sum hours).

    Args:
        scoped: fact_scoped_capacity_weekly

    Returns:
        fact_capacity_quarterly_snapshot
    """
    if scoped.empty:
        return pd.DataFrame(columns=_QUARTERLY_COLS)

    df = scoped.copy()

    # Filter to base scenarios only
    df = df[df["scenario"].isin(base_scenarios)].copy()
    if df.empty:
        return pd.DataFrame(columns=_QUARTERLY_COLS)

    # Derive quarter_id from week string
    df["quarter_id"] = df["week"].apply(week_to_quarter)

    agg = (
        df.groupby(["scope_id", "quarter_id", "plant", "work_center"], as_index=False)
        .agg(
            total_available_capacity_hours=("available_capacity_hours", "sum"),
            total_planned_load_hours=("planned_load_hours", "sum"),
            total_incremental_load_hours=("incremental_load_hours", "sum"),
            total_overload_hours=("overload_hours", "sum"),
            bottleneck_weeks_count=("bottleneck_flag", "sum"),
        )
    )
    agg["bottleneck_weeks_count"] = agg["bottleneck_weeks_count"].astype(int)

    return agg[_QUARTERLY_COLS].reset_index(drop=True)


def _build_state_history(
    quarterly: pd.DataFrame,
    bottleneck: pd.DataFrame,
) -> pd.DataFrame:
    """Build carry-over capacity risk history by comparing consecutive quarters.

    For each (scope_id, plant, work_center, quarter_id):
        - looks up the immediately prior quarter's data
        - flags carry_over_capacity_risk_flag if BOTH quarters had bottleneck weeks
        - attaches prior mitigation lever from bottleneck summary
        - writes a human-readable learning_note

    Args:
        quarterly: fact_capacity_quarterly_snapshot (output of _aggregate_quarterly)
        bottleneck: fact_capacity_bottleneck_summary (scenario × plant × work_center)

    Returns:
        fact_capacity_state_history
    """
    if quarterly.empty:
        return pd.DataFrame(columns=_HISTORY_COLS)

    # Build a lookup: (plant, work_center) → suggested mitigation lever
    mitigation_index: dict[tuple, str] = {}
    if not bottleneck.empty and "suggested_capacity_lever" in bottleneck.columns:
        for _, row in bottleneck.drop_duplicates(["plant", "work_center"], keep="first").iterrows():
            mitigation_index[(row["plant"], row["work_center"])] = str(row["suggested_capacity_lever"])

    # Sort quarterly by (scope_id, plant, work_center, quarter chronologically)
    q = quarterly.copy()
    q["_sort_key"] = q["quarter_id"].apply(_quarter_sort_key)
    q = q.sort_values(["scope_id", "plant", "work_center", "_sort_key"]).drop(columns=["_sort_key"])

    # Build a fast lookup: (scope_id, plant, work_center, quarter_id) → row
    idx: dict[tuple, dict] = {}
    for _, row in q.iterrows():
        key = (row["scope_id"], row["plant"], row["work_center"], row["quarter_id"])
        idx[key] = row.to_dict()

    records = []
    for _, row in q.iterrows():
        scope_id = row["scope_id"]
        plant = row["plant"]
        work_center = row["work_center"]
        quarter_id = row["quarter_id"]

        prior_qid = _prior_quarter_id(quarter_id)
        prior_key = (scope_id, plant, work_center, prior_qid) if prior_qid else None
        prior = idx.get(prior_key) if prior_key else None

        prior_bottleneck_flag = bool((prior["bottleneck_weeks_count"] > 0) if prior else False)
        prior_overload_hours = float(prior["total_overload_hours"] if prior else 0.0)
        prior_mitigation = mitigation_index.get((plant, work_center), "none")

        carry_over = bool(
            prior_bottleneck_flag and (int(row["bottleneck_weeks_count"]) > 0)
        )

        # Learning note
        if prior is None:
            note = f"{plant}/{work_center}: no prior quarter data — first planning period"
        elif carry_over:
            note = (
                f"{plant}/{work_center}: bottleneck persisted from {prior_qid} into {quarter_id} "
                f"({prior['bottleneck_weeks_count']} prior weeks, "
                f"{row['bottleneck_weeks_count']} current weeks) — escalate lever: {prior_mitigation}"
            )
        elif prior_bottleneck_flag:
            note = (
                f"{plant}/{work_center}: {prior_qid} had {prior['bottleneck_weeks_count']} bottleneck weeks "
                f"— resolved in {quarter_id}; prior lever was {prior_mitigation}"
            )
        else:
            note = f"{plant}/{work_center}: no carry-over risk from {prior_qid}"

        records.append({
            "scope_id": scope_id,
            "quarter_id": quarter_id,
            "plant": plant,
            "work_center": work_center,
            "prior_quarter_bottleneck_flag": prior_bottleneck_flag,
            "prior_quarter_overload_hours": round(prior_overload_hours, 2),
            "prior_quarter_mitigation_used": prior_mitigation,
            "carry_over_capacity_risk_flag": carry_over,
            "learning_note": note,
        })

    return pd.DataFrame(records)[_HISTORY_COLS].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def build_fact_scoped_capacity_weekly(
    cap: pd.DataFrame,
    scope: dict | None = None,
) -> pd.DataFrame:
    if scope is None:
        scope = DEFAULT_SCOPE
    return _scope_capacity_weekly(cap, scope["scope_id"], scope["plants"])


def build_fact_capacity_quarterly_snapshot(
    scoped: pd.DataFrame,
) -> pd.DataFrame:
    return _aggregate_quarterly(scoped)


def build_fact_capacity_state_history(
    quarterly: pd.DataFrame,
    bottleneck: pd.DataFrame,
) -> pd.DataFrame:
    return _build_state_history(quarterly, bottleneck)
