"""
calendar_bridge.py
==================
Wave 1 Task 3: Build bridge_month_week_calendar

Reuse decision: NEW MODULE — sheet 2_4 was not loaded by legacy backend.
  The legacy engine used even-spread month-to-week allocation.
  This module replaces that with calendar-accurate weights from 2_4.

2_4 structure (transposed):
  - Rows = attribute labels (Day Number, Week Number, Month Number, Year,
    Working Days NW01..NW15, etc.)
  - Columns = calendar days (~830 across 2026-2028) + weekly summary columns

Strategy:
  1. Try to load and parse 2_4 for working-day-weighted bridge
  2. If parsing fails (schema drift), fall back to pandas date-arithmetic bridge
     (allocation_weight only; working_day_weight = allocation_weight)

Output columns (contracts.md schema):
  plant, month, week, year, allocation_weight, working_day_weight, bridge_version

Validation: allocation_weight sums to 1.0 per (plant, year, month).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..legacy_adapters.legacy_loader import read_raw_sheet, DEFAULT_XLSX

# Plants in the dataset (NW01–NW15, but real data may have fewer)
_KNOWN_PLANTS = [f"NW{i:02d}" for i in range(1, 16)]

BRIDGE_VERSION_REAL = "2_4_working_day_weighted_v1"
BRIDGE_VERSION_FALLBACK = "pandas_calendar_fallback_v1"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_bridge_month_week_calendar(
    xlsx_path: str | Path | None = None,
    *,
    start_year: int = 2026,
    end_year: int = 2028,
) -> pd.DataFrame:
    """
    Build bridge_month_week_calendar.

    Tries real 2_4 sheet first; falls back to pandas date arithmetic.
    """
    path = xlsx_path or DEFAULT_XLSX
    try:
        bridge = _build_from_2_4(path, start_year=start_year, end_year=end_year)
        if not bridge.empty:
            return bridge
    except Exception:
        pass
    return _build_fallback(start_year=start_year, end_year=end_year)


# ---------------------------------------------------------------------------
# Real 2_4 parser
# ---------------------------------------------------------------------------

def _build_from_2_4(
    xlsx_path: str | Path,
    *,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Parse the transposed 2_4 calendar sheet."""
    raw = read_raw_sheet(
        "2_4 Model Calendar",
        xlsx_path=xlsx_path,
        header=None,
        index_col=0,
    )
    if raw.empty or raw.shape[0] < 5:
        return pd.DataFrame()

    # 2_4 is transposed: index = attribute labels, columns = day/week columns
    # Transpose so rows = days, columns = attributes
    cal = raw.T.copy()
    cal.index = range(len(cal))
    cal.columns = [str(c).strip() for c in cal.columns]

    # Identify key attribute columns (case-insensitive search)
    col_lower = {c.lower(): c for c in cal.columns}

    def _find_col(*candidates: str) -> str | None:
        for c in candidates:
            if c.lower() in col_lower:
                return col_lower[c.lower()]
        return None

    week_col = _find_col("week number", "week number weekly", "week number weekly {corrected}")
    month_col = _find_col(
        "month number weekly {corrected}",
        "month number weekly",
        "month number",
    )
    year_col = _find_col("year")
    day_col = _find_col("day number")

    if not all([week_col, month_col, year_col]):
        return pd.DataFrame()

    # Filter to day-level rows only (exclude weekly summary rows — day_col is numeric)
    if day_col:
        valid = pd.to_numeric(cal[day_col], errors="coerce").notna()
        cal = cal[valid].copy()

    cal["_week"] = pd.to_numeric(cal[week_col], errors="coerce")
    cal["_month"] = pd.to_numeric(cal[month_col], errors="coerce")
    cal["_year"] = pd.to_numeric(cal[year_col], errors="coerce")

    # Drop rows with missing week/month/year
    cal = cal.dropna(subset=["_week", "_month", "_year"])
    cal = cal[
        cal["_year"].between(start_year, end_year)
    ].copy()

    if cal.empty:
        return pd.DataFrame()

    # Identify per-plant working-day columns: "Working Days NW01" etc.
    plant_cols: dict[str, str] = {}
    for col in cal.columns:
        if col.lower().startswith("working days nw"):
            plant_id = col.strip().split()[-1].upper()  # "NW01"
            plant_cols[plant_id] = col

    # Build base bridge (plant-agnostic allocation_weight from day counts)
    # Count days per (year, month, iso_year, week)
    day_counts = (
        cal.groupby(["_year", "_month", "_week"])
        .size()
        .reset_index(name="days_in_week_month")
    )
    month_totals = (
        cal.groupby(["_year", "_month"])
        .size()
        .reset_index(name="days_in_month")
    )
    base = day_counts.merge(month_totals, on=["_year", "_month"])
    base["allocation_weight"] = base["days_in_week_month"] / base["days_in_month"]

    bridges = []

    if plant_cols:
        for plant, wcol in plant_cols.items():
            cal[wcol] = pd.to_numeric(cal[wcol], errors="coerce").fillna(0.0)
            wd_week_month = (
                cal.groupby(["_year", "_month", "_week"])[wcol]
                .sum()
                .reset_index(name="wd_in_week_month")
            )
            wd_month = (
                cal.groupby(["_year", "_month"])[wcol]
                .sum()
                .reset_index(name="wd_in_month")
            )
            plant_df = base.merge(wd_week_month, on=["_year", "_month", "_week"], how="left")
            plant_df = plant_df.merge(wd_month, on=["_year", "_month"], how="left")
            plant_df["wd_in_month"] = plant_df["wd_in_month"].fillna(0.0)
            plant_df["wd_in_week_month"] = plant_df["wd_in_week_month"].fillna(0.0)
            plant_df["working_day_weight"] = np.where(
                plant_df["wd_in_month"] > 0,
                plant_df["wd_in_week_month"] / plant_df["wd_in_month"],
                plant_df["allocation_weight"],
            )
            plant_df["plant"] = plant
            bridges.append(plant_df)
    else:
        # No per-plant working-day columns found — use allocation_weight as proxy
        base["working_day_weight"] = base["allocation_weight"]
        base["plant"] = "ALL"
        bridges.append(base)

    out = pd.concat(bridges, ignore_index=True)
    out = out.rename(columns={"_year": "year", "_month": "month", "_week": "week"})
    out["bridge_version"] = BRIDGE_VERSION_REAL

    return out[["plant", "year", "month", "week", "allocation_weight",
                "working_day_weight", "bridge_version"]].copy()


# ---------------------------------------------------------------------------
# Fallback: pure pandas date arithmetic
# ---------------------------------------------------------------------------

def _build_fallback(*, start_year: int, end_year: int) -> pd.DataFrame:
    """
    Build month-week bridge using pandas date arithmetic.
    allocation_weight = calendar days in (month ∩ week) / calendar days in month.
    working_day_weight = allocation_weight (no plant-specific working day data).
    """
    days = pd.date_range(
        f"{start_year}-01-01", f"{end_year}-12-31", freq="D"
    )
    df = pd.DataFrame({
        "date": days,
        "year": [d.isocalendar().year for d in days],
        "month_year": days.year,
        "month": days.month,
        "week": [d.isocalendar().week for d in days],
    })

    # Days in month (calendar year for month granularity)
    month_totals = (
        df.groupby(["month_year", "month"])["date"]
        .count()
        .reset_index(name="days_in_month")
    )

    # Days per (iso_year, month, week)
    overlap = (
        df.groupby(["year", "month_year", "month", "week"])["date"]
        .count()
        .reset_index(name="days_in_week_month")
    )
    overlap = overlap.merge(
        month_totals, on=["month_year", "month"], how="left"
    )
    overlap["allocation_weight"] = (
        overlap["days_in_week_month"] / overlap["days_in_month"]
    )
    overlap["working_day_weight"] = overlap["allocation_weight"]
    overlap["plant"] = "ALL"
    overlap["bridge_version"] = BRIDGE_VERSION_FALLBACK

    return overlap[
        ["plant", "year", "month", "week", "allocation_weight",
         "working_day_weight", "bridge_version"]
    ].copy().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_calendar_bridge(df: pd.DataFrame) -> dict:
    """Check that weights sum to 1.0 per (plant, year, month)."""
    if df.empty:
        return {"valid": False, "reason": "empty dataframe"}

    sums = df.groupby(["plant", "year", "month"])["allocation_weight"].sum()
    max_err = float((sums - 1.0).abs().max())
    passing = max_err < 0.01

    wd_sums = df.groupby(["plant", "year", "month"])["working_day_weight"].sum()
    wd_max_err = float((wd_sums - 1.0).abs().max())

    return {
        "valid": bool(passing),
        "max_allocation_weight_error": round(max_err, 6),
        "max_working_day_weight_error": round(wd_max_err, 6),
        "bridge_version": df["bridge_version"].iloc[0] if "bridge_version" in df else "unknown",
        "plants": sorted(df["plant"].unique().tolist()),
        "total_rows": len(df),
    }
