"""Build procurement decision support from SAP master data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.legacy_adapters.legacy_loader import DEFAULT_XLSX, read_raw_sheet


_PROCUREMENT_TYPE_MAP = {
    "E": "External procurement",
    "F": "In-house production",
    "X": "Mixed procurement",
}


def _derive_lead_time(row: pd.Series) -> float | None:
    """Primary planned delivery time, fallback in-house production days x 1.4."""

    primary = row.get("Planned Delivery Time (MARC) (CD)")
    if pd.notna(primary):
        try:
            return float(primary)
        except (TypeError, ValueError):
            pass

    fallback = row.get("In House Production Time (WD)")
    if pd.notna(fallback):
        try:
            return float(fallback) * 1.4
        except (TypeError, ValueError):
            pass

    return None


def build_dim_procurement_logic(
    xlsx_path: str | Path | None = None,
) -> pd.DataFrame:
    """Build `dim_procurement_logic` from sheet `2_3 SAP MasterData`."""

    raw = read_raw_sheet("2_3 SAP MasterData", xlsx_path=xlsx_path or DEFAULT_XLSX)
    if raw.empty:
        return pd.DataFrame(
            columns=[
                "plant",
                "material",
                "procurement_type",
                "lead_time_days",
                "order_policy_note",
                "reason_code",
            ]
        )

    df = raw.replace("#N/A", None).copy()
    out = pd.DataFrame(
        {
            "plant": df.get("G35 - Plant"),
            "material": df.get("Sap code"),
            "procurement_type": df.get("Procurement Type"),
        }
    )
    out["lead_time_days"] = df.apply(_derive_lead_time, axis=1)
    out["order_policy_note"] = out["procurement_type"].apply(
        lambda pt: _PROCUREMENT_TYPE_MAP.get(str(pt).strip(), "Unknown") if pd.notna(pt) else "Unknown"
    )
    out["reason_code"] = out["lead_time_days"].apply(
        lambda v: "READY" if pd.notna(v) else "MISSING_LEAD_TIME"
    )
    out = out.dropna(subset=["plant", "material"]).drop_duplicates(["plant", "material"]).reset_index(drop=True)
    return out
