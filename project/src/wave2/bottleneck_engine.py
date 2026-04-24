"""
bottleneck_engine.py
====================
Wave 2 Task 3: Build fact_capacity_bottleneck_summary

Ranks overloaded work centers by severity, exposes available capacity levers
(upside_1, upside_2 from dim_wc_scenario_limits), and generates explanation notes.

Open-scaffold pattern: one output fact per concern.
  - Input: fact_scenario_capacity_weekly (overload rows only)
  - Input: demand detail (for top_driver_project_count)
  - Input: bridge_material_tool_wc (for tool_no resolution)
  - Input: dim_wc_scenario_limits (for lever suggestion)

Output grain: scenario × plant × work_center

Columns (Wave 2 contract):
  scenario, plant, work_center, tool_no_if_available,
  bottleneck_severity, top_driver_project_count,
  suggested_capacity_lever, explanation_note
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from project.src.wave1.operational_mapping import build_bridge_material_tool_wc
from project.src.wave1.scenario_limits import build_dim_wc_scenario_limits
from project.src.wave2.capacity_overlay import WARN_THRESHOLD, CRIT_THRESHOLD

# Severity bands
SEV_CRITICAL = "critical"
SEV_WARNING = "warning"
SEV_OK = "ok"


def build_fact_capacity_bottleneck_summary(
    fact_scenario_capacity_weekly: pd.DataFrame,
    translated_demand: pd.DataFrame,
    xlsx_path=None,
) -> pd.DataFrame:
    """
    Build fact_capacity_bottleneck_summary.

    Parameters
    ----------
    fact_scenario_capacity_weekly : from capacity_overlay.build_fact_scenario_capacity_weekly
    translated_demand             : from demand_translation.build_fact_translated_project_demand_weekly
    xlsx_path                     : workbook path for bridge lookups
    """
    if fact_scenario_capacity_weekly.empty:
        return _empty_summary()

    # Only keep demand scenarios (not capacity variant suffixes like __upside_1)
    base_scenarios = fact_scenario_capacity_weekly[
        ~fact_scenario_capacity_weekly["scenario"].str.contains("__", na=False)
    ].copy()

    bottlenecks = base_scenarios[base_scenarios["bottleneck_flag"]].copy()
    if bottlenecks.empty:
        return _empty_summary()

    tool_bridge = build_bridge_material_tool_wc(xlsx_path)
    limits = build_dim_wc_scenario_limits(xlsx_path)

    return _summarise(bottlenecks, translated_demand, tool_bridge, limits, fact_scenario_capacity_weekly)


def _summarise(
    bottlenecks: pd.DataFrame,
    demand: pd.DataFrame,
    tool_bridge: pd.DataFrame,
    limits: pd.DataFrame,
    full_cap: pd.DataFrame,
) -> pd.DataFrame:
    """Core summarisation — testable independently."""
    if bottlenecks.empty or "scenario" not in bottlenecks.columns:
        return _empty_summary()

    # Aggregate bottleneck stats per (scenario, plant, work_center)
    agg = (
        bottlenecks.groupby(["scenario", "plant", "work_center"], as_index=False)
        .agg(
            peak_overload_pct=("overload_pct", "max"),
            total_overload_hours=("overload_hours", "sum"),
            overloaded_weeks=("bottleneck_flag", "sum"),
        )
    )

    # Severity band
    agg["bottleneck_severity"] = pd.cut(
        agg["peak_overload_pct"],
        bins=[-np.inf, WARN_THRESHOLD, CRIT_THRESHOLD, np.inf],
        labels=[SEV_OK, SEV_WARNING, SEV_CRITICAL],
    ).astype(str)
    # Correct ok label (shouldn't appear since we filtered bottleneck_flag=True)
    agg.loc[agg["bottleneck_severity"] == SEV_OK, "bottleneck_severity"] = SEV_WARNING

    # Top driver project count per (scenario, plant, work_center)
    if not demand.empty and "work_center" in demand.columns:
        driver_counts = (
            demand[demand["demand_hours"] > 0]
            .groupby(["scenario_name", "plant", "work_center"])["project_id"]
            .nunique()
            .reset_index(name="top_driver_project_count")
            .rename(columns={"scenario_name": "scenario"})
        )
        agg = agg.merge(driver_counts, on=["scenario", "plant", "work_center"], how="left")
    else:
        agg["top_driver_project_count"] = 0
    agg["top_driver_project_count"] = agg["top_driver_project_count"].fillna(0).astype(int)

    # Tool number lookup (first tool per WC at plant)
    if not tool_bridge.empty:
        tool_lookup = (
            tool_bridge[tool_bridge["tool_no"].notna()]
            .groupby(["plant", "work_center"])["tool_no"]
            .first()
            .reset_index()
        )
        agg = agg.merge(tool_lookup, on=["plant", "work_center"], how="left")
        agg = agg.rename(columns={"tool_no": "tool_no_if_available"})
    else:
        agg["tool_no_if_available"] = None

    # Suggest capacity lever from dim_wc_scenario_limits
    agg["suggested_capacity_lever"] = agg.apply(
        lambda r: _suggest_lever(r, limits, full_cap), axis=1
    )

    # Explanation note
    agg["explanation_note"] = agg.apply(_explain, axis=1)

    # Sort before slicing (peak_overload_pct is dropped from final schema)
    agg = agg.sort_values(["scenario", "peak_overload_pct"], ascending=[True, False])

    cols = [
        "scenario", "plant", "work_center", "tool_no_if_available",
        "bottleneck_severity", "top_driver_project_count",
        "suggested_capacity_lever", "explanation_note",
    ]
    return agg[[c for c in cols if c in agg.columns]].reset_index(drop=True)


def _suggest_lever(row: pd.Series, limits: pd.DataFrame, full_cap: pd.DataFrame) -> str:
    """
    Find the cheapest upside shift level that brings utilisation below WARN_THRESHOLD.
    Returns 'upside_1', 'upside_2', or 'no_lever_available'.
    """
    if limits.empty:
        return "no_lever_available"

    wc_limits = limits[
        (limits["plant"] == row["plant"]) &
        (limits["work_center"] == row["work_center"])
    ]
    if wc_limits.empty:
        return "no_lever_available"

    # Total load from full_cap for this (scenario, plant, wc)
    load_rows = full_cap[
        (full_cap["scenario"] == row["scenario"]) &
        (full_cap["plant"] == row["plant"]) &
        (full_cap["work_center"] == row["work_center"])
    ]
    if load_rows.empty:
        return "no_lever_available"
    avg_total_load = load_rows["total_load_hours"].mean()

    for lever in ["upside_1", "upside_2"]:
        lev_row = wc_limits[wc_limits["scenario_limit_name"] == lever]
        if lev_row.empty:
            continue
        lever_hours = pd.to_numeric(
            lev_row["available_hours_variant"].iloc[0], errors="coerce"
        )
        if pd.isna(lever_hours) or lever_hours <= 0:
            continue
        if (avg_total_load / lever_hours) < WARN_THRESHOLD:
            return lever

    return "no_lever_available"


def _explain(row: pd.Series) -> str:
    """Generate a human-readable explanation note."""
    sev = row.get("bottleneck_severity", "unknown")
    wc = row.get("work_center", "?")
    pct = row.get("peak_overload_pct", 0)
    overload_h = row.get("total_overload_hours", 0)
    n_proj = row.get("top_driver_project_count", 0)
    lever = row.get("suggested_capacity_lever", "no_lever_available")

    if sev == SEV_CRITICAL:
        sev_txt = "CRITICAL — fully overloaded"
    else:
        sev_txt = "WARNING — approaching limit"

    lever_txt = (
        f"Shift to {lever} schedule to resolve."
        if lever != "no_lever_available"
        else "No upside shift lever available — consider rerouting or rescheduling."
    )

    return (
        f"{sev_txt}: {wc} peaks at {pct:.0%} utilisation, "
        f"{overload_h:.1f} overload hours total, "
        f"driven by {n_proj} pipeline project(s). {lever_txt}"
    )


def _empty_summary() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "scenario", "plant", "work_center", "tool_no_if_available",
        "bottleneck_severity", "top_driver_project_count",
        "suggested_capacity_lever", "explanation_note",
    ])
