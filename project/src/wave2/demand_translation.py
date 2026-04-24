"""
demand_translation.py
=====================
Wave 2 Task 1: Build fact_translated_project_demand_weekly

Translates monthly scenario demand into weekly work-center demand hours.

Pipeline (open-scaffold pattern — one concern per step):
  Step 1: Expand monthly demand into scenarios
          (from Luigi's build_scenario_project_demand_seed)
  Step 2: Allocate monthly qty to weeks via bridge_month_week_calendar
          (Lara Wave 1 — working-day-weighted or calendar-fallback)
  Step 3: Join bridge_material_tool_wc to resolve work_center + cycle_time
          (Lara Wave 1 — enriched with reason codes)
  Step 4: Convert pieces → hours: demand_hours = qty × (cycle_time_min / 60)

Output grain: scenario × plant × work_center × year × week × project_id × material
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from project.src.canonical.pipeline_demand import build_fact_pipeline_monthly
from project.src.scenarios.demand_qualification import build_scenario_project_demand_seed
from project.src.wave1.calendar_bridge import build_bridge_month_week_calendar
from project.src.wave1.operational_mapping import build_bridge_material_tool_wc

# ---------------------------------------------------------------------------
# Reason codes
# ---------------------------------------------------------------------------
RC_READY = "TRANSLATED"
RC_NO_WC = "MISSING_WORK_CENTER"
RC_NO_CT = "MISSING_CYCLE_TIME"
RC_NO_MAPPING = "NO_TOOL_MAPPING"


def build_fact_translated_project_demand_weekly(
    xlsx_path: str | Path | None = None,
    *,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Full pipeline: monthly pipeline → weekly WC demand hours (all scenarios).

    Returns DataFrame with columns:
      scenario_name, scenario_confidence, project_id, plant, material,
      work_center, year, week, demand_qty, demand_hours, reason_code
    """
    # Step 1: monthly scenario seed (Luigi Wave 1)
    fact_monthly = build_fact_pipeline_monthly()
    if fact_monthly.empty:
        return _empty_demand()

    seed = build_scenario_project_demand_seed(fact_monthly)
    if seed.empty:
        return _empty_demand()

    # Step 2: calendar bridge (Lara Wave 1)
    calendar = build_bridge_month_week_calendar(xlsx_path)

    # Step 3: tool/WC bridge (Lara Wave 1)
    tool_bridge = build_bridge_material_tool_wc(xlsx_path)

    return _translate(seed, calendar, tool_bridge)


def _translate(
    seed: pd.DataFrame,
    calendar: pd.DataFrame,
    tool_bridge: pd.DataFrame,
) -> pd.DataFrame:
    """Core translation logic — testable independently of I/O."""
    # Extract (year, month_num) from seed's 'month' column (datetime)
    seed = seed.copy()
    seed["_dt"] = pd.to_datetime(seed["month"], errors="coerce")
    seed["_year"] = seed["_dt"].dt.year
    seed["_month"] = seed["_dt"].dt.month
    seed = seed[seed["_dt"].notna()].copy()

    # Normalise calendar: handle plant="ALL" fallback
    cal = calendar.copy()
    cal_has_plants = (cal["plant"] != "ALL").any()

    # Prepare tool bridge — keep only complete or partially-complete rows
    tb = tool_bridge[tool_bridge["work_center"].notna()].copy()
    tb = tb[["plant", "material", "work_center", "cycle_time", "reason_code"]].copy()
    tb = tb.rename(columns={"cycle_time": "cycle_time_min", "reason_code": "tool_reason"})
    # If multiple (plant, material) rows pick best: prefer COMPLETE
    tb["_pref"] = (tb["tool_reason"] == "COMPLETE").astype(int)
    tb = (
        tb.sort_values("_pref", ascending=False)
        .drop_duplicates(subset=["plant", "material", "work_center"])
        .drop(columns=["_pref"])
    )

    # Join seed × calendar (by plant + year + month)
    if cal_has_plants:
        # Plant-specific weights available
        merged = seed.merge(
            cal.rename(columns={"month": "_month", "year": "_year"}),
            on=["plant", "_year", "_month"],
            how="left",
        )
        # Fill missing plant weights from "ALL" fallback if present
        if "ALL" in cal["plant"].values:
            fallback = cal[cal["plant"] == "ALL"].rename(
                columns={"month": "_month", "year": "_year"}
            ).drop(columns=["plant"])
            missing_mask = merged["allocation_weight"].isna()
            if missing_mask.any():
                merged_fb = seed[missing_mask].merge(
                    fallback, on=["_year", "_month"], how="left"
                )
                merged.loc[missing_mask, ["week", "allocation_weight", "working_day_weight"]] = (
                    merged_fb[["week", "allocation_weight", "working_day_weight"]].values
                )
    else:
        # Only ALL-plant calendar — join without plant key
        cal_no_plant = cal.drop(columns=["plant"]).rename(
            columns={"month": "_month", "year": "_year"}
        )
        merged = seed.merge(cal_no_plant, on=["_year", "_month"], how="left")

    if merged.empty or "week" not in merged.columns:
        return _empty_demand()

    # Weekly demand qty = scenario_qty × allocation_weight
    merged["allocation_weight"] = pd.to_numeric(
        merged.get("allocation_weight"), errors="coerce"
    ).fillna(0.0)
    merged["demand_qty"] = merged["scenario_qty"].fillna(0.0) * merged["allocation_weight"]

    # Keep only rows with demand
    merged = merged[merged["demand_qty"] > 0].copy()
    if merged.empty:
        return _empty_demand()

    # Join tool bridge to get work_center + cycle_time
    demand = merged.merge(tb, on=["plant", "material"], how="left")

    # Rows without any tool mapping
    no_mapping = demand["work_center"].isna()
    demand.loc[no_mapping, "reason_code"] = RC_NO_MAPPING
    demand["reason_code"] = demand["reason_code"].fillna(RC_READY)

    # Convert pieces → hours
    demand["cycle_time_min"] = pd.to_numeric(
        demand.get("cycle_time_min"), errors="coerce"
    )
    demand["demand_hours"] = np.where(
        demand["cycle_time_min"].notna() & (demand["cycle_time_min"] > 0),
        demand["demand_qty"] * (demand["cycle_time_min"] / 60.0),
        0.0,
    )

    # Flag missing cycle time
    demand.loc[
        demand["cycle_time_min"].isna() & demand["work_center"].notna(),
        "reason_code",
    ] = RC_NO_CT

    # Aggregate to output grain
    out = (
        demand.groupby(
            ["scenario_name", "scenario_confidence", "project_id",
             "plant", "material", "work_center", "_year", "week"],
            as_index=False,
            dropna=False,
        )
        .agg(
            demand_qty=("demand_qty", "sum"),
            demand_hours=("demand_hours", "sum"),
            reason_code=("reason_code", "first"),
        )
        .rename(columns={"_year": "year"})
    )

    # Final schema
    cols = [
        "scenario_name", "scenario_confidence", "project_id",
        "plant", "material", "work_center", "year", "week",
        "demand_qty", "demand_hours", "reason_code",
    ]
    return out[[c for c in cols if c in out.columns]].reset_index(drop=True)


def _empty_demand() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "scenario_name", "scenario_confidence", "project_id",
        "plant", "material", "work_center", "year", "week",
        "demand_qty", "demand_hours", "reason_code",
    ])
