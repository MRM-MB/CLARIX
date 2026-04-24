"""
operational_mapping.py
======================
Wave 1 Task 1: Build bridge_material_tool_wc

Reuse decision: ADAPT legacy clarix.data_loader._build_tool_master()
  - Legacy missing: Rev no, work_center (full), mapping_status, reason_code
  - Re-reads 2_6 directly to capture Rev no (not loaded by legacy builder)
  - Adds reason codes per contracts.md rules

Output columns (contracts.md schema):
  plant, material, revision, tool_no, work_center, cycle_time,
  mapping_status, reason_code
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..legacy_adapters.legacy_loader import read_raw_sheet, DEFAULT_XLSX

# ---------------------------------------------------------------------------
# Reason codes (contracts.md uppercase snake_case)
# ---------------------------------------------------------------------------
RC_COMPLETE = "COMPLETE"
RC_MISSING_WC = "MISSING_WORK_CENTER"
RC_MISSING_CT = "MISSING_CYCLE_TIME"
RC_MISSING_TOOL = "MISSING_TOOL"
RC_MISSING_WC_AND_CT = "MISSING_WORK_CENTER|MISSING_CYCLE_TIME"
RC_PLACEHOLDER = "PLACEHOLDER_MATERIAL"

# Placeholder sentinel strings in the raw sheet
_PLACEHOLDER_MATERIALS = {"Missing WC", "Missing tool", "Missing CT", "_"}
_PLACEHOLDER_WC = {"#N/A", "Missing WC", "Missing tool", ""}
_PLACEHOLDER_CT = {"Missing CT", ""}


def _is_placeholder(val: object) -> bool:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return True
    return str(val).strip() in _PLACEHOLDER_MATERIALS


def _is_missing_wc(val: object) -> bool:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return True
    return str(val).strip() in _PLACEHOLDER_WC


def _is_missing_ct(val: object) -> bool:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return True
    s = str(val).strip()
    return s in _PLACEHOLDER_CT or s.lower().startswith("missing")


def _assign_reason_code(row: pd.Series) -> str:
    missing_wc = _is_missing_wc(row.get("work_center_raw"))
    missing_ct = _is_missing_ct(row.get("cycle_time_raw"))
    missing_tool = _is_placeholder(row.get("tool_no"))
    if missing_wc and missing_ct:
        return RC_MISSING_WC_AND_CT
    if missing_wc:
        return RC_MISSING_WC
    if missing_ct:
        return RC_MISSING_CT
    if missing_tool:
        return RC_MISSING_TOOL
    return RC_COMPLETE


def build_bridge_material_tool_wc(
    xlsx_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Build the enriched bridge_material_tool_wc from sheet 2_6.

    Returns DataFrame with columns:
      plant, material, revision, tool_no, work_center, cycle_time,
      mapping_status, reason_code
    """
    path = xlsx_path or DEFAULT_XLSX

    # Load 2_6 with keep_default_na=False so '#N/A' stays as string, not NaN
    raw = read_raw_sheet(
        "2_6 Tool_material nr master",
        xlsx_path=path,
        keep_default_na=False,
        na_values=["", "NULL", "null"],
    )
    if raw.empty:
        return _empty_bridge()

    # Canonical column rename
    col_map = {
        "Plant": "plant",
        "Sap code": "material",
        "Type": "type",
        "Tool No.": "tool_no",
        "Work center": "work_center_raw",
        "Cycle times Standard Value (Machine)": "cycle_time_raw",
        "Material Status": "mapping_status",
        "Rev no": "revision",
        "Material description": "material_description",
    }
    df = raw.rename(columns={k: v for k, v in col_map.items() if k in raw.columns})

    # Ensure required columns exist (defensively)
    for col in ["plant", "material", "tool_no", "work_center_raw", "cycle_time_raw",
                "revision", "mapping_status"]:
        if col not in df.columns:
            df[col] = None

    # Build full work_center code: P01_{plant}_{work_center_short}
    def _full_wc(row: pd.Series) -> str:
        wc_raw = str(row.get("work_center_raw", "") or "").strip()
        if _is_missing_wc(wc_raw) or wc_raw == "#N/A":
            return None
        plant = str(row.get("plant", "") or "").strip()
        return f"P01_{plant}_{wc_raw}" if plant else wc_raw

    df["work_center"] = df.apply(_full_wc, axis=1)

    # Normalise cycle_time to float (None if missing)
    def _parse_ct(val: object) -> float | None:
        if _is_missing_ct(val):
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    df["cycle_time"] = df["cycle_time_raw"].map(_parse_ct)

    # Assign reason codes
    df["reason_code"] = df.apply(_assign_reason_code, axis=1)

    # mapping_status: preserve original (Active / Phase-out) or fallback
    if "mapping_status" not in df.columns or df["mapping_status"].isna().all():
        df["mapping_status"] = "unknown"
    df["mapping_status"] = df["mapping_status"].fillna("unknown").astype(str)

    # Revision: keep as string; NaN → "UNKNOWN"
    df["revision"] = df["revision"].fillna("UNKNOWN").astype(str).str.strip()

    # Final output schema
    out_cols = ["plant", "material", "revision", "tool_no", "work_center",
                "cycle_time", "mapping_status", "reason_code"]
    out = df[[c for c in out_cols if c in df.columns]].copy()
    # Drop rows where plant and material are both null (truly blank rows)
    out = out[~(out["plant"].isna() & out["material"].isna())].reset_index(drop=True)

    return out


def summarise_mapping_gaps(bridge: pd.DataFrame) -> dict:
    """Return gap counts for Wave 1 report."""
    total = len(bridge)
    complete = (bridge["reason_code"] == RC_COMPLETE).sum()
    missing_wc = bridge["reason_code"].str.contains("MISSING_WORK_CENTER").sum()
    missing_ct = bridge["reason_code"].str.contains("MISSING_CYCLE_TIME").sum()
    missing_tool = (bridge["reason_code"] == RC_MISSING_TOOL).sum()
    revision_dupes = (
        bridge.groupby(["plant", "material"])["revision"]
        .nunique()
        .gt(1)
        .sum()
    )
    return {
        "total_rows": int(total),
        "complete_mappings": int(complete),
        "missing_work_center": int(missing_wc),
        "missing_cycle_time": int(missing_ct),
        "missing_tool": int(missing_tool),
        "materials_with_revision_mismatch": int(revision_dupes),
    }


def _empty_bridge() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "plant", "material", "revision", "tool_no", "work_center",
        "cycle_time", "mapping_status", "reason_code",
    ])
