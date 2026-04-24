"""
capacity_overlay.py
===================
Wave 2 Task 2: Build fact_scenario_capacity_weekly

Overlays incremental pipeline demand on top of the approved baseline load
and evaluates headroom or overload per scenario, plant, WC, and week.

Capacity variants:
  - "baseline" capacity = available_capacity_hours from fact_wc_capacity_weekly
  - "upside_1" / "upside_2" variants = from dim_wc_scenario_limits
    → used to show what headroom a shift-level change would unlock

Output grain: scenario × plant × work_center × year × week

Columns (contracts.md schema):
  scenario, plant, work_center, week, year,
  incremental_load_hours, planned_load_hours, total_load_hours,
  available_capacity_hours, remaining_capacity_hours,
  overload_hours, overload_pct, bottleneck_flag
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from project.src.wave1.capacity_baseline import build_fact_wc_capacity_weekly
from project.src.wave1.scenario_limits import build_dim_wc_scenario_limits

# Utilisation thresholds (mirrors Wave 1 bottleneck conventions)
WARN_THRESHOLD = 0.85
CRIT_THRESHOLD = 1.00

# Capacity variant scenarios to materialise alongside each demand scenario
_CAPACITY_VARIANTS = ["baseline", "upside_1", "upside_2"]


def build_fact_scenario_capacity_weekly(
    translated_demand: pd.DataFrame,
    xlsx_path: str | Path | None = None,
    *,
    use_cache: bool = True,
    capacity_variants: bool = True,
) -> pd.DataFrame:
    """
    Build fact_scenario_capacity_weekly.

    Parameters
    ----------
    translated_demand : output of build_fact_translated_project_demand_weekly
    xlsx_path         : path to workbook (for capacity and limits tables)
    capacity_variants : if True, also produce upside_1/upside_2 capacity rows
    """
    cap = build_fact_wc_capacity_weekly(xlsx_path, use_cache=use_cache)
    limits = build_dim_wc_scenario_limits(xlsx_path)

    if translated_demand.empty or cap.empty:
        return _empty_scenario_capacity()

    return _overlay(translated_demand, cap, limits, capacity_variants=capacity_variants)


def _overlay(
    demand: pd.DataFrame,
    cap: pd.DataFrame,
    limits: pd.DataFrame,
    *,
    capacity_variants: bool,
) -> pd.DataFrame:
    """Core overlay logic — testable independently of I/O."""
    # Aggregate incremental demand to grain: scenario × plant × work_center × year × week
    inc = (
        demand.groupby(
            ["scenario_name", "plant", "work_center", "year", "week"],
            as_index=False,
        )["demand_hours"]
        .sum()
        .rename(columns={
            "scenario_name": "scenario",
            "demand_hours": "incremental_load_hours",
        })
    )
    inc["work_center"] = inc["work_center"].fillna("")

    # Baseline capacity fact: one row per (plant, work_center, year, week)
    cap_base = cap[
        ["plant", "work_center", "year", "week",
         "available_capacity_hours", "planned_load_hours"]
    ].copy()
    cap_base["work_center"] = cap_base["work_center"].fillna("")
    cap_base["available_capacity_hours"] = cap_base["available_capacity_hours"].fillna(0.0)
    cap_base["planned_load_hours"] = cap_base["planned_load_hours"].fillna(0.0)

    # Join incremental demand onto capacity baseline
    merged = cap_base.merge(inc, on=["plant", "work_center", "year", "week"], how="left")
    # fill WCs with no incremental demand (scenarios that don't touch them)
    # also cross-join scenarios onto baseline rows without demand
    all_scenarios = inc["scenario"].unique().tolist()
    if not all_scenarios:
        return _empty_scenario_capacity()

    # For WCs not in demand for a given scenario → incremental = 0
    merged["scenario"] = merged["scenario"].fillna("__temp__")
    # Expand cap_base to all scenarios, then left-join actual incremental
    cap_expanded = cap_base.assign(__key=1).merge(
        pd.DataFrame({"scenario": all_scenarios, "__key": 1}),
        on="__key",
    ).drop(columns=["__key"])
    cap_expanded = cap_expanded.merge(
        inc, on=["scenario", "plant", "work_center", "year", "week"], how="left"
    )
    cap_expanded["incremental_load_hours"] = (
        cap_expanded["incremental_load_hours"].fillna(0.0)
    )

    result = _compute_metrics(cap_expanded, capacity_col="available_capacity_hours")
    parts = [result]

    # Capacity variants: upside_1, upside_2 for each demand scenario
    if capacity_variants and not limits.empty:
        for variant in ["upside_1", "upside_2"]:
            lim = limits[limits["scenario_limit_name"] == variant][
                ["plant", "work_center", "available_hours_variant"]
            ].rename(columns={"available_hours_variant": "variant_hours"}).copy()
            lim = lim.dropna(subset=["variant_hours"])
            if lim.empty:
                continue
            variant_df = cap_expanded.merge(
                lim, on=["plant", "work_center"], how="inner"
            )
            variant_df["available_capacity_hours"] = variant_df["variant_hours"]
            variant_df["scenario"] = variant_df["scenario"] + f"__{variant}"
            variant_df = _compute_metrics(variant_df, capacity_col="available_capacity_hours")
            parts.append(variant_df)

    out = pd.concat(parts, ignore_index=True)

    cols = [
        "scenario", "plant", "work_center", "year", "week",
        "incremental_load_hours", "planned_load_hours", "total_load_hours",
        "available_capacity_hours", "remaining_capacity_hours",
        "overload_hours", "overload_pct", "bottleneck_flag",
    ]
    return out[[c for c in cols if c in out.columns]].reset_index(drop=True)


def _compute_metrics(df: pd.DataFrame, capacity_col: str) -> pd.DataFrame:
    """Add total_load, overload, headroom, and flag columns."""
    out = df.copy()
    out["total_load_hours"] = out["planned_load_hours"] + out["incremental_load_hours"]
    avail = out[capacity_col].clip(lower=0.0)
    out["available_capacity_hours"] = avail
    out["remaining_capacity_hours"] = (avail - out["total_load_hours"]).clip(lower=0.0)
    out["overload_hours"] = np.maximum(0.0, out["total_load_hours"] - avail)
    out["overload_pct"] = np.where(
        avail > 0,
        out["total_load_hours"] / avail,
        np.where(out["total_load_hours"] > 0, np.inf, 0.0),
    )
    out["bottleneck_flag"] = out["overload_pct"] >= WARN_THRESHOLD
    return out


def validate_scenario_capacity(df: pd.DataFrame) -> dict:
    """Validate output grain and overload reproducibility."""
    if df.empty:
        return {"valid": False, "reason": "empty"}
    key = ["scenario", "plant", "work_center", "year", "week"]
    dupes = df.duplicated(key).sum()
    n_bottleneck = int(df["bottleneck_flag"].sum())
    n_critical = int((df["overload_pct"] >= CRIT_THRESHOLD).sum())
    return {
        "total_rows": len(df),
        "unique_at_grain": int(dupes == 0),
        "duplicate_rows": int(dupes),
        "scenarios": sorted(df["scenario"].unique().tolist()),
        "bottleneck_wc_weeks": n_bottleneck,
        "critical_wc_weeks": n_critical,
        "overload_hours_total": round(float(df["overload_hours"].sum()), 1),
    }


def _empty_scenario_capacity() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "scenario", "plant", "work_center", "year", "week",
        "incremental_load_hours", "planned_load_hours", "total_load_hours",
        "available_capacity_hours", "remaining_capacity_hours",
        "overload_hours", "overload_pct", "bottleneck_flag",
    ])
