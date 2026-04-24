"""Wave 3 Carolina: fact_data_quality_flags engine.

Scans Wave 2 outputs for data quality issues and produces one flag row per
issue found. Deduplicates on (entity_type, entity_key, issue_type).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helper: safe numeric coerce for bottleneck_severity
# ---------------------------------------------------------------------------

def _severity_is_critical(val) -> bool:
    """Return True if bottleneck_severity maps to critical."""
    if pd.isna(val):
        return False
    try:
        return float(val) >= 0.8
    except (ValueError, TypeError):
        return str(val).strip().lower() == "critical"


def _severity_is_warning(val) -> bool:
    """Return True if bottleneck_severity maps to warning (0.5–<0.8 or 'high')."""
    if pd.isna(val):
        return False
    try:
        fval = float(val)
        return 0.5 <= fval < 0.8
    except (ValueError, TypeError):
        return str(val).strip().lower() == "high"


# ---------------------------------------------------------------------------
# Per-source scanners
# ---------------------------------------------------------------------------

def _scan_sourcing(df: pd.DataFrame) -> pd.DataFrame:
    """Scan fact_scenario_sourcing_weekly for issues 1–3."""
    records = []

    for _, row in df.iterrows():
        key = f"{row['scenario']}|{row['plant']}|{row['component_material']}|{row['week']}"
        cov = row["coverage_days_or_weeks"]
        flag = row["shortage_flag"]
        demand = row["component_demand_qty"]
        avail = row["available_qty"]

        # Issue 1: missing_inventory_coverage
        if flag and cov < 7:
            records.append({
                "entity_type": "sourcing_row",
                "entity_key": key,
                "issue_type": "missing_inventory_coverage",
                "severity": "critical",
                "penalty_score": 0.4,
                "reason_code": "SHORTAGE_CRITICAL",
                "recommended_handling": "weaken",
            })

        # Issue 2: low_inventory_coverage
        elif flag and 7 <= cov < 14:
            records.append({
                "entity_type": "sourcing_row",
                "entity_key": key,
                "issue_type": "low_inventory_coverage",
                "severity": "warning",
                "penalty_score": 0.2,
                "reason_code": "SHORTAGE_WARNING",
                "recommended_handling": "flag_only",
            })

        # Issue 3: zero_demand_with_bom
        if demand == 0 and avail > 0:
            records.append({
                "entity_type": "sourcing_row",
                "entity_key": key,
                "issue_type": "zero_demand_with_bom",
                "severity": "info",
                "penalty_score": 0.0,
                "reason_code": "ZERO_DEMAND",
                "recommended_handling": "flag_only",
            })

    return pd.DataFrame(records) if records else _empty_flags()


def _scan_logistics(df: pd.DataFrame) -> pd.DataFrame:
    """Scan fact_scenario_logistics_weekly for issues 4–6."""
    records = []

    for _, row in df.iterrows():
        key = f"{row['scenario']}|{row['project_id']}|{row['plant']}|{row['week']}"

        # Issue 4: synthetic_logistics_dependency
        if row["synthetic_dependency_flag"]:
            records.append({
                "entity_type": "logistics_row",
                "entity_key": key,
                "issue_type": "synthetic_logistics_dependency",
                "severity": "warning",
                "penalty_score": 0.1,
                "reason_code": "SYNTHETIC_DATA",
                "recommended_handling": "flag_only",
            })

        # Issue 5: on_time_infeasible
        if not row["on_time_feasible_flag"]:
            records.append({
                "entity_type": "logistics_row",
                "entity_key": key,
                "issue_type": "on_time_infeasible",
                "severity": "critical",
                "penalty_score": 0.3,
                "reason_code": "LATE_DELIVERY_RISK",
                "recommended_handling": "weaken",
            })

        # Issue 6: high_logistics_risk
        if row["logistics_risk_score"] >= 0.5:
            records.append({
                "entity_type": "logistics_row",
                "entity_key": key,
                "issue_type": "high_logistics_risk",
                "severity": "warning",
                "penalty_score": 0.15,
                "reason_code": "LOGISTICS_RISK_HIGH",
                "recommended_handling": "flag_only",
            })

    return pd.DataFrame(records) if records else _empty_flags()


def _scan_bottlenecks(df: pd.DataFrame) -> pd.DataFrame:
    """Scan fact_capacity_bottleneck_summary for issues 7–8."""
    records = []

    for _, row in df.iterrows():
        key = f"{row['scenario']}|{row['plant']}|{row['work_center']}"
        sev = row["bottleneck_severity"]

        # Issue 7: capacity_bottleneck_critical
        if _severity_is_critical(sev):
            records.append({
                "entity_type": "bottleneck_row",
                "entity_key": key,
                "issue_type": "capacity_bottleneck_critical",
                "severity": "critical",
                "penalty_score": 0.35,
                "reason_code": "BOTTLENECK_CRITICAL",
                "recommended_handling": "weaken",
            })

        # Issue 8: capacity_bottleneck_warning
        elif _severity_is_warning(sev):
            records.append({
                "entity_type": "bottleneck_row",
                "entity_key": key,
                "issue_type": "capacity_bottleneck_warning",
                "severity": "warning",
                "penalty_score": 0.15,
                "reason_code": "BOTTLENECK_WARNING",
                "recommended_handling": "flag_only",
            })

    return pd.DataFrame(records) if records else _empty_flags()


def _scan_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Scan fact_integrated_risk_base for issues 9–10."""
    records = []

    for _, row in df.iterrows():
        key = f"{row['scenario']}|{row['project_id']}|{row['plant']}|{row['week']}"

        # Issue 9: high_action_score
        if row["action_score_base"] >= 0.8:
            records.append({
                "entity_type": "risk_row",
                "entity_key": key,
                "issue_type": "high_action_score",
                "severity": "critical",
                "penalty_score": 0.0,
                "reason_code": "ESCALATION_NEEDED",
                "recommended_handling": "flag_only",
            })

        # Issue 10: placeholder_quality_zero
        if row["data_quality_penalty_placeholder"] == 0.0:
            records.append({
                "entity_type": "risk_row",
                "entity_key": key,
                "issue_type": "placeholder_quality_zero",
                "severity": "info",
                "penalty_score": 0.05,
                "reason_code": "QUALITY_PENALTY_PLACEHOLDER",
                "recommended_handling": "flag_only",
            })

    return pd.DataFrame(records) if records else _empty_flags()


# ---------------------------------------------------------------------------
# Schema skeleton for empty results
# ---------------------------------------------------------------------------

_COLUMNS = [
    "entity_type",
    "entity_key",
    "issue_type",
    "severity",
    "penalty_score",
    "reason_code",
    "recommended_handling",
]


def _empty_flags() -> pd.DataFrame:
    return pd.DataFrame(columns=_COLUMNS)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_fact_data_quality_flags(
    real_processed_dir: str | Path,
    synth_processed_dir: str | Path,
) -> pd.DataFrame:
    """Scan all Wave 2 outputs and return one flag row per issue found.

    Parameters
    ----------
    real_processed_dir:
        Path to project/data/processed/ containing Wave 2 CSVs.
    synth_processed_dir:
        Path to processed/ containing Wave 1 synthetic CSVs (not used for
        scanning in Wave 3, kept for future use).

    Returns
    -------
    pd.DataFrame
        Deduplicated on (entity_type, entity_key, issue_type).
    """
    real = Path(real_processed_dir)

    sourcing = pd.read_csv(real / "fact_scenario_sourcing_weekly.csv")
    logistics = pd.read_csv(real / "fact_scenario_logistics_weekly.csv")
    bottlenecks = pd.read_csv(real / "fact_capacity_bottleneck_summary.csv")
    risk = pd.read_csv(real / "fact_integrated_risk_base.csv")

    # Normalise bool columns that may be read as object from CSV
    for col in ("shortage_flag",):
        if col in sourcing.columns:
            sourcing[col] = sourcing[col].map(
                lambda v: str(v).strip().lower() in ("true", "1", "yes")
            )
    for col in ("synthetic_dependency_flag", "on_time_feasible_flag"):
        if col in logistics.columns:
            logistics[col] = logistics[col].map(
                lambda v: str(v).strip().lower() in ("true", "1", "yes")
            )

    parts = [
        _scan_sourcing(sourcing),
        _scan_logistics(logistics),
        _scan_bottlenecks(bottlenecks),
        _scan_risk(risk),
    ]

    combined = pd.concat(parts, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["entity_type", "entity_key", "issue_type"]
    ).reset_index(drop=True)

    combined["penalty_score"] = combined["penalty_score"].astype(float)
    return combined
