"""
capacity_baseline.py
====================
Wave 1 Task 2: Build fact_wc_capacity_weekly

Reuse decision: ADAPT legacy clarix.data_loader._build_wc_capacity()
  - Legacy output already has: work_center, plant, week, year, available_hours,
    baseline_demand_qty, week_start
  - This module renames to contract schema and adds derived columns:
      remaining_capacity_hours = available - planned (floor 0 for headroom view)
      missing_capacity_hours   = max(0, planned - available) (overload)

Validation: every row unique by (plant, work_center, week).

Output columns (Wave 1 contract):
  plant, work_center, week, available_capacity_hours, planned_load_hours,
  remaining_capacity_hours, missing_capacity_hours
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..legacy_adapters.legacy_loader import get_canonical, DEFAULT_XLSX


def build_fact_wc_capacity_weekly(
    xlsx_path: str | Path | None = None,
    *,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Build fact_wc_capacity_weekly from the legacy canonical loader.

    Returns DataFrame with columns:
      plant, work_center, week, year, week_start,
      available_capacity_hours, planned_load_hours,
      remaining_capacity_hours, missing_capacity_hours
    """
    data = get_canonical(xlsx_path or DEFAULT_XLSX, use_cache=use_cache)
    raw = data.fact_wc_capacity_weekly.copy()

    if raw.empty:
        return _empty_capacity()

    # Rename to contract schema
    rename = {
        "available_hours": "available_capacity_hours",
        "baseline_demand_qty": "planned_load_hours",
    }
    df = raw.rename(columns=rename)

    # Ensure numeric
    df["available_capacity_hours"] = pd.to_numeric(
        df["available_capacity_hours"], errors="coerce"
    ).fillna(0.0)
    df["planned_load_hours"] = pd.to_numeric(
        df["planned_load_hours"], errors="coerce"
    ).fillna(0.0)

    # Derived columns
    df["remaining_capacity_hours"] = (
        df["available_capacity_hours"] - df["planned_load_hours"]
    ).clip(lower=0.0)

    df["missing_capacity_hours"] = np.maximum(
        0.0,
        df["planned_load_hours"] - df["available_capacity_hours"],
    )

    # Deduplicate: if multiple measures landed in the same (plant, wc, week, year),
    # sum the demand and take max of available (safety for legacy wide-pivot quirks)
    key = ["plant", "work_center", "year", "week"]
    # Some rows may be duplicates from the wide-melt; aggregate defensively
    if df.duplicated(key).any():
        df = (
            df.groupby(key + ["week_start"], as_index=False)
            .agg(
                available_capacity_hours=("available_capacity_hours", "max"),
                planned_load_hours=("planned_load_hours", "sum"),
            )
        )
        df["remaining_capacity_hours"] = (
            df["available_capacity_hours"] - df["planned_load_hours"]
        ).clip(lower=0.0)
        df["missing_capacity_hours"] = np.maximum(
            0.0,
            df["planned_load_hours"] - df["available_capacity_hours"],
        )

    # Final column order
    out_cols = [
        "plant", "work_center", "year", "week", "week_start",
        "available_capacity_hours", "planned_load_hours",
        "remaining_capacity_hours", "missing_capacity_hours",
    ]
    out = df[[c for c in out_cols if c in df.columns]].copy()
    return out.reset_index(drop=True)


def validate_capacity(df: pd.DataFrame) -> dict:
    """Check uniqueness and return validation summary."""
    key = ["plant", "work_center", "week"]
    # year must also be included if multi-year
    full_key = ["plant", "work_center", "year", "week"]
    present_key = [c for c in full_key if c in df.columns]
    dupes = df.duplicated(present_key).sum()
    return {
        "total_rows": len(df),
        "unique_by_plant_wc_week": int(dupes == 0),
        "duplicate_rows": int(dupes),
        "plants": int(df["plant"].nunique()) if "plant" in df.columns else 0,
        "work_centers": int(df["work_center"].nunique()) if "work_center" in df.columns else 0,
        "overloaded_wc_weeks": int((df["missing_capacity_hours"] > 0).sum()),
    }


def _empty_capacity() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "plant", "work_center", "year", "week", "week_start",
        "available_capacity_hours", "planned_load_hours",
        "remaining_capacity_hours", "missing_capacity_hours",
    ])
