"""
src/carolina/sourcing_engine.py

Sourcing engine for Carolina Wave 2.
Explodes BOM demand through inventory and procurement logic to produce a
weekly sourcing requirement table with shortage flags and risk scores.
"""

import os
import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LEAD_TIME_DAYS = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_week_to_monday(week_str: str) -> datetime:
    """Convert 'YYYY-Www' (Luigi W2 format) to Monday of that ISO week."""
    try:
        return datetime.strptime(f"{week_str}-1", "%G-W%V-%u")
    except ValueError:
        raise ValueError(f"Cannot parse week string: {week_str!r}")


def _load_translated_demand(real_processed_dir: str) -> pd.DataFrame:
    """Load fact_translated_project_demand_weekly from Luigi W2 output dir."""
    demand_path = os.path.join(real_processed_dir, "fact_translated_project_demand_weekly.csv")
    print(f"[sourcing_engine] Loading demand from {demand_path}")
    return pd.read_csv(demand_path)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_sourcing_engine(
    real_processed_dir: str = "project/data/processed",
    synth_processed_dir: str = "processed",
) -> pd.DataFrame:
    """
    Run the sourcing engine.

    Parameters
    ----------
    real_processed_dir : str
        Directory with Luigi/Lara Wave 1+2 outputs (fact_translated_project_demand_weekly,
        fact_finished_to_component, fact_inventory_snapshot, dim_procurement_logic).
    synth_processed_dir : str
        Directory with Carolina Wave 1 synthetic outputs (not used by sourcing engine
        directly, but kept for signature parity with logistics engine).

    Returns
    -------
    pd.DataFrame with columns:
        scenario, plant, component_material, week,
        component_demand_qty, available_qty, shortage_qty,
        coverage_days_or_weeks, recommended_order_date,
        shortage_flag, sourcing_risk_score
    """
    # ------------------------------------------------------------------
    # 1. Load BOM
    # ------------------------------------------------------------------
    bom_path = os.path.join(real_processed_dir, "fact_finished_to_component.csv")
    fact_bom = pd.read_csv(bom_path)
    # Normalise plant column — project BOM uses compound string P01_NW01_...; extract NW-code
    if fact_bom["plant"].str.startswith("P01_").any():
        fact_bom["plant"] = fact_bom["plant"].str.extract(r"P01_(\w+)_")[0].fillna(fact_bom["plant"])

    # Normalise column name — Lara/project uses qty_per_effective; Carolina W1 used effective_component_qty
    if "qty_per_effective" in fact_bom.columns and "effective_component_qty" not in fact_bom.columns:
        fact_bom = fact_bom.rename(columns={"qty_per_effective": "effective_component_qty"})
    fact_bom["effective_component_qty"] = pd.to_numeric(
        fact_bom["effective_component_qty"], errors="coerce"
    ).fillna(0.0)

    # ------------------------------------------------------------------
    # 2. Load translated demand from Luigi W2
    # ------------------------------------------------------------------
    demand = _load_translated_demand(real_processed_dir)

    required_demand_cols = {"scenario", "plant", "material", "week", "expected_weekly_qty"}
    missing = required_demand_cols - set(demand.columns)
    if missing:
        raise ValueError(f"Demand table missing columns: {missing}")

    demand["expected_weekly_qty"] = pd.to_numeric(
        demand["expected_weekly_qty"], errors="coerce"
    ).fillna(0.0)

    # ------------------------------------------------------------------
    # 3. BOM explosion: join demand on (plant, header_material=material)
    # ------------------------------------------------------------------
    exploded = demand.merge(
        fact_bom,
        left_on=["plant", "material"],
        right_on=["plant", "header_material"],
        how="left",
    )
    # Rows with no BOM match → component_material NaN; drop them
    exploded = exploded.dropna(subset=["component_material"])

    exploded["component_demand_qty"] = (
        exploded["expected_weekly_qty"] * exploded["effective_component_qty"]
    )

    # ------------------------------------------------------------------
    # 4. Aggregate by (scenario, plant, component_material, week)
    # ------------------------------------------------------------------
    agg = (
        exploded.groupby(["scenario", "plant", "component_material", "week"], as_index=False)
        ["component_demand_qty"]
        .sum()
    )

    # ------------------------------------------------------------------
    # 5. Join inventory snapshot on (plant, material=component_material)
    # ------------------------------------------------------------------
    inv_path = os.path.join(real_processed_dir, "fact_inventory_snapshot.csv")
    inventory = pd.read_csv(inv_path)
    for col in ["stock_qty", "in_transit_qty"]:
        inventory[col] = pd.to_numeric(inventory[col], errors="coerce").fillna(0.0)

    agg = agg.merge(
        inventory[["plant", "material", "stock_qty", "in_transit_qty"]],
        left_on=["plant", "component_material"],
        right_on=["plant", "material"],
        how="left",
    ).drop(columns=["material"], errors="ignore")

    agg["stock_qty"] = agg["stock_qty"].fillna(0.0)
    agg["in_transit_qty"] = agg["in_transit_qty"].fillna(0.0)

    agg["available_qty"] = agg["stock_qty"] + agg["in_transit_qty"]
    agg["shortage_qty"] = (agg["component_demand_qty"] - agg["available_qty"]).clip(lower=0.0)
    agg["shortage_flag"] = agg["shortage_qty"] > 0

    # ------------------------------------------------------------------
    # 6. Join procurement logic on (plant, material=component_material)
    # ------------------------------------------------------------------
    proc_path = os.path.join(real_processed_dir, "dim_procurement_logic.csv")
    procurement = pd.read_csv(proc_path)
    # Normalise column name — project uses lead_time_days; Carolina W1 used lead_time_days_or_weeks
    if "lead_time_days" in procurement.columns and "lead_time_days_or_weeks" not in procurement.columns:
        procurement = procurement.rename(columns={"lead_time_days": "lead_time_days_or_weeks"})
    procurement["lead_time_days_or_weeks"] = pd.to_numeric(
        procurement["lead_time_days_or_weeks"], errors="coerce"
    ).fillna(DEFAULT_LEAD_TIME_DAYS)

    agg = agg.merge(
        procurement[["plant", "material", "lead_time_days_or_weeks"]],
        left_on=["plant", "component_material"],
        right_on=["plant", "material"],
        how="left",
    ).drop(columns=["material"], errors="ignore")

    agg["lead_time_days_or_weeks"] = agg["lead_time_days_or_weeks"].fillna(DEFAULT_LEAD_TIME_DAYS)

    # Convert week string to date and compute recommended_order_date
    def _week_to_monday(w: str) -> pd.Timestamp:
        try:
            return pd.Timestamp(_parse_week_to_monday(w))
        except Exception:
            return pd.NaT

    week_dates = {w: _week_to_monday(w) for w in agg["week"].unique()}
    agg["week_start_date"] = agg["week"].map(week_dates)
    agg["recommended_order_date"] = agg.apply(
        lambda r: r["week_start_date"] - timedelta(days=int(r["lead_time_days_or_weeks"]))
        if pd.notna(r["week_start_date"])
        else pd.NaT,
        axis=1,
    )

    # coverage_days = (available_qty / max(component_demand_qty, 0.001)) * 7
    agg["coverage_days_or_weeks"] = (
        agg["available_qty"] / agg["component_demand_qty"].clip(lower=0.001) * 7
    )

    # ------------------------------------------------------------------
    # 7. sourcing_risk_score = clamp(shortage_qty / max(component_demand_qty, 1), 0, 1)
    # ------------------------------------------------------------------
    agg["sourcing_risk_score"] = (
        agg["shortage_qty"] / agg["component_demand_qty"].clip(lower=1.0)
    ).clip(0.0, 1.0)

    # ------------------------------------------------------------------
    # 8. Select output columns, dedup, return
    # ------------------------------------------------------------------
    output_cols = [
        "scenario",
        "plant",
        "component_material",
        "week",
        "component_demand_qty",
        "available_qty",
        "shortage_qty",
        "coverage_days_or_weeks",
        "recommended_order_date",
        "shortage_flag",
        "sourcing_risk_score",
    ]
    result = agg[output_cols].drop_duplicates(
        subset=["scenario", "plant", "component_material", "week"], keep="first"
    ).reset_index(drop=True)

    # Ensure shortage_flag is bool
    result["shortage_flag"] = result["shortage_flag"].astype(bool)

    return result
