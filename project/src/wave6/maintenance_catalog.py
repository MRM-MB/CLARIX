"""
maintenance_catalog.py
======================
Wave 6 Lara: Build dim_maintenance_policy_synth.

One concern: define explicit maintenance policies per (plant, work_center)
with documented synthetic generation rules.
Inner function _build_policy() is I/O-free and fully testable.
"""

from __future__ import annotations

import pandas as pd

GENERATION_VERSION = "wave6_maintenance_v1"
CATALOG_SEED = 42

# WC name keyword → maintenance trigger type
_WC_TYPE_MAP: list[tuple[str, str]] = [
    ("PRESS",      "scheduled_preventive"),
    ("EXTRUSION",  "scheduled_preventive"),
    ("GRINDING",   "regulatory_inspection"),
    ("GRIND",      "regulatory_inspection"),
    ("ASSY",       "corrective_unscheduled"),
    ("ASSEMBLY",   "corrective_unscheduled"),
    ("WELD",       "scheduled_preventive"),
    ("PAINT",      "regulatory_inspection"),
    ("LATHE",      "scheduled_preventive"),
    ("MILL",       "scheduled_preventive"),
]

# trigger_type → (interval_weeks, downtime_hours, rule_description)
_POLICY_DEFAULTS: dict[str, tuple[int, float, str]] = {
    "scheduled_preventive": (
        8, 4.0,
        "Scheduled preventive: every 8 weeks, 4h downtime per event. "
        "Interval and duration are synthetic expert estimates."
    ),
    "corrective_unscheduled": (
        4, 8.0,
        "Corrective unscheduled: expected recurrence every 4 weeks, 8h downtime. "
        "Represents mean-time-between-failure analogue. Fully synthetic."
    ),
    "regulatory_inspection": (
        13, 2.0,
        "Regulatory inspection: quarterly (every 13 weeks), 2h downtime. "
        "Based on typical EU/OSHA inspection frequency. Synthetic."
    ),
}

_COLUMN_ORDER = [
    "policy_id",
    "plant",
    "work_center",
    "tool_no_if_available",
    "maintenance_trigger_type",
    "estimated_interval_weeks_synth",
    "expected_downtime_hours_synth",
    "policy_generation_rule",
    "generation_version",
    "random_seed",
]


def _infer_trigger_type(work_center: str) -> str:
    wc_upper = work_center.upper()
    for keyword, trigger in _WC_TYPE_MAP:
        if keyword in wc_upper:
            return trigger
    return "scheduled_preventive"


def _build_policy(
    scoped_wcs: pd.DataFrame,
    bridge: pd.DataFrame,
) -> pd.DataFrame:
    """Build dim_maintenance_policy_synth from unique WCs in scope.

    Args:
        scoped_wcs: DataFrame with at minimum columns [plant, work_center]
                    (typically fact_scoped_capacity_weekly)
        bridge:     bridge_material_tool_wc — used to attach first tool_no per WC

    Returns:
        dim_maintenance_policy_synth with one row per (plant, work_center)
    """
    if scoped_wcs.empty:
        return pd.DataFrame(columns=_COLUMN_ORDER)

    # Unique (plant, work_center) pairs in scope
    pairs = (
        scoped_wcs[["plant", "work_center"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # Build tool lookup: (plant, work_center) → first tool_no
    tool_index: dict[tuple, str] = {}
    if not bridge.empty and "tool" in bridge.columns:
        for _, row in bridge.dropna(subset=["tool"]).iterrows():
            key = (str(row["plant"]), str(row["work_center"]))
            if key not in tool_index:
                tool_index[key] = str(row["tool"])

    rows = []
    for i, (_, pair) in enumerate(pairs.iterrows()):
        plant = str(pair["plant"])
        wc = str(pair["work_center"])
        trigger = _infer_trigger_type(wc)
        interval, downtime, rule = _POLICY_DEFAULTS[trigger]
        tool = tool_index.get((plant, wc), "N/A")

        rows.append({
            "policy_id": f"MAINT_{plant}_{wc}_{trigger[:3].upper()}",
            "plant": plant,
            "work_center": wc,
            "tool_no_if_available": tool,
            "maintenance_trigger_type": trigger,
            "estimated_interval_weeks_synth": interval,
            "expected_downtime_hours_synth": downtime,
            "policy_generation_rule": rule,
            "generation_version": GENERATION_VERSION,
            "random_seed": CATALOG_SEED,
        })

    return pd.DataFrame(rows)[_COLUMN_ORDER]


def build_dim_maintenance_policy_synth(
    scoped_capacity: pd.DataFrame,
    bridge: pd.DataFrame,
) -> pd.DataFrame:
    """Public entry point."""
    return _build_policy(scoped_capacity, bridge)
