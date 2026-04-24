"""
scenario_limits.py
==================
Wave 1 Task 4: Build dim_wc_scenario_limits

Reuse decision: ADAPT legacy clarix.data_loader._build_wc_limits()
  - Legacy collapses 5 shift levels into one monthly table, losing AP Limit name
  - This module re-reads 2_5 directly to capture all 5 shift-level variants
    and map them to scenario dimension names

2_5 structure:
  - 5 rows per WC, one per shift level
  - AP Limit column: "Downside Limit 2 (hrs)" / "Downside Limit 1 (hrs)" /
    "Available Capacity, hours" / "Upside Limit 1 (hrs)" / "Upside Limit 2 (hrs)"
  - Weekly available time: computed hours
  - OEE (in %), Hours, Days per level

Output columns (Wave 1 contract):
  plant, work_center, scenario_limit_name, available_hours_variant,
  oee_variant, weekly_time_variant, source_level
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..legacy_adapters.legacy_loader import read_raw_sheet, DEFAULT_XLSX

# ---------------------------------------------------------------------------
# AP Limit → scenario_limit_name mapping
# ---------------------------------------------------------------------------
_AP_LIMIT_MAP: dict[str, str] = {
    "downside limit 2 (hrs)": "downside_2",
    "downside limit 1 (hrs)": "downside_1",
    "available capacity, hours": "baseline",
    "available capacity (hrs)": "baseline",
    "upside limit 1 (hrs)": "upside_1",
    "upside limit 2 (hrs)": "upside_2",
}

# Fallback ordinal when AP Limit label isn't recognised
_ORDINAL_NAMES = ["downside_2", "downside_1", "baseline", "upside_1", "upside_2"]


def _map_limit_name(raw_label: str, rank: int) -> str:
    """Map raw AP Limit label to scenario_limit_name, with ordinal fallback."""
    if raw_label:
        key = str(raw_label).strip().lower()
        if key in _AP_LIMIT_MAP:
            return _AP_LIMIT_MAP[key]
    if 0 <= rank < len(_ORDINAL_NAMES):
        return _ORDINAL_NAMES[rank]
    return f"level_{rank + 1}"


def build_dim_wc_scenario_limits(
    xlsx_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Build dim_wc_scenario_limits from sheet 2_5.

    Returns DataFrame with columns:
      plant, work_center, scenario_limit_name, available_hours_variant,
      oee_variant, weekly_time_variant, source_level
    """
    path = xlsx_path or DEFAULT_XLSX

    raw = read_raw_sheet("2_5 WC Schedule_limits", xlsx_path=path)
    if raw.empty:
        return _empty_limits()

    # Column aliases — handle minor naming variants
    col_alias = {
        "Plant": "plant",
        "WC-Description": "wc_description",
        "WC-Description long": "wc_description_long",
        "AP Limit": "ap_limit_label",
        "Weekly available time": "weekly_time_variant",
        "Weekly available time ": "weekly_time_variant",   # trailing space variant
        "OEE (in %)": "oee_variant",
        "Hours": "hours_per_day",
        "Days": "days_per_week",
        "WC Schedule Label": "wc_schedule_label",
        "AP Limit time (in H)": "available_hours_variant",
        "AP Limit time (in H) ": "available_hours_variant",
        "Suggested % Limit / AP Limit (in %)": "limit_pct",
    }
    df = raw.rename(columns={k: v for k, v in col_alias.items() if k in raw.columns})

    # Ensure required columns exist
    for col in ["plant", "wc_description", "ap_limit_label", "oee_variant"]:
        if col not in df.columns:
            df[col] = None

    # available_hours_variant: prefer the explicit H column; fall back to weekly_time_variant
    if "available_hours_variant" not in df.columns:
        if "weekly_time_variant" in df.columns:
            df["available_hours_variant"] = df["weekly_time_variant"]
        else:
            df["available_hours_variant"] = None

    if "weekly_time_variant" not in df.columns:
        df["weekly_time_variant"] = df.get("available_hours_variant")

    # Build work_center = "P01_{plant}_{wc_description}"
    df["work_center"] = df.apply(
        lambda r: f"P01_{str(r.get('plant', '')).strip()}_{str(r.get('wc_description', '')).strip()}"
        if pd.notna(r.get("plant")) and pd.notna(r.get("wc_description"))
        else None,
        axis=1,
    )

    # Rank within each work_center to assign fallback ordinal names
    df["_rank"] = df.groupby("work_center").cumcount()

    df["ap_limit_label"] = df["ap_limit_label"].fillna("").astype(str)
    df["scenario_limit_name"] = df.apply(
        lambda r: _map_limit_name(r["ap_limit_label"], int(r["_rank"])), axis=1
    )

    # source_level = the raw AP Limit label for traceability
    df["source_level"] = df["ap_limit_label"].where(df["ap_limit_label"] != "", "unknown")

    # Numeric coercion
    for col in ["available_hours_variant", "oee_variant", "weekly_time_variant"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Final schema
    out_cols = [
        "plant", "work_center", "scenario_limit_name", "available_hours_variant",
        "oee_variant", "weekly_time_variant", "source_level",
    ]
    out = df[[c for c in out_cols if c in df.columns]].copy()
    out = out[out["plant"].notna() & out["work_center"].notna()].reset_index(drop=True)
    return out


def _empty_limits() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "plant", "work_center", "scenario_limit_name", "available_hours_variant",
        "oee_variant", "weekly_time_variant", "source_level",
    ])
