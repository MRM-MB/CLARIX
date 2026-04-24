"""
delivery_commitment.py
======================
Wave 6 Carolina: build fact_delivery_commitment_weekly from scoped logistics
and service-level policy dimensions.

Synthetic assumptions (labeled):
- requested_delivery_date = week_date + 28 days (4-week forward window)
- production_time_proxy_days = 14 (constant — no real production lead-time data)

Usage:
  from project.src.wave6.delivery_commitment import build_fact_delivery_commitment_weekly
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

_REQUIRED_OUTPUT_COLS = [
    "scope_id",
    "scenario",
    "project_id",
    "plant",
    "week",
    "requested_delivery_date",
    "transit_time_days",
    "production_time_proxy_days",
    "total_commitment_time_days",
    "on_time_feasible_flag",
    "expedite_option_flag",
    "service_violation_risk",
    "synthetic_delivery_assumption",
]

# Synthetic constant — labeled per governance policy
_PRODUCTION_TIME_PROXY_DAYS: int = 14
# Synthetic assumption — 4-week forward delivery window
_DELIVERY_WINDOW_DAYS: int = 28


def week_to_date(week_str: str) -> pd.Timestamp:
    """Convert YYYY-Www to the Monday (day 1) of that ISO week.

    Example: '2026-W01' -> Timestamp('2026-01-05 00:00:00')
    """
    dt = datetime.strptime(f"{week_str}-1", "%G-W%V-%u")
    return pd.Timestamp(dt)


def _derive_revenue_tier(logistics_risk_score: float) -> str:
    """Map logistics_risk_score to revenue tier bucket."""
    if logistics_risk_score < 0.2:
        return "Small"
    if logistics_risk_score < 0.4:
        return "Medium"
    if logistics_risk_score < 0.6:
        return "Large"
    return "Strategic"


def _empty_commitment() -> pd.DataFrame:
    return pd.DataFrame(columns=_REQUIRED_OUTPUT_COLS)


def build_fact_delivery_commitment_weekly(
    scoped_logistics: pd.DataFrame,
    service_policy: pd.DataFrame,
    project_priority: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build weekly delivery commitment fact table.

    Parameters
    ----------
    scoped_logistics:
        fact_scoped_logistics_weekly — must contain columns:
        scope_id, scenario, project_id, plant, week,
        transit_time_days, logistics_risk_score, synthetic_dependency_flag
    service_policy:
        dim_service_level_policy_synth — must contain columns:
        revenue_tier, max_allowed_late_days, expedite_allowed_flag
    project_priority:
        dim_project_priority (optional) — when provided, revenue_tier is taken
        from this table via project_id join; falls back to heuristic for gaps.

    Returns
    -------
    DataFrame with _REQUIRED_OUTPUT_COLS plus synthetic_delivery_assumption=True.
    """
    if scoped_logistics.empty:
        return _empty_commitment()

    df = scoped_logistics.copy()

    # --- 1. Compute week_date (Monday of ISO week) ---
    df["week_date"] = df["week"].apply(week_to_date)

    # --- 2. requested_delivery_date: SYNTHETIC ASSUMPTION — week_date + 28 days ---
    df["requested_delivery_date"] = df["week_date"] + pd.Timedelta(days=_DELIVERY_WINDOW_DAYS)

    # --- 3. production_time_proxy_days: SYNTHETIC CONSTANT ---
    df["production_time_proxy_days"] = _PRODUCTION_TIME_PROXY_DAYS

    # --- 4. total_commitment_time_days ---
    df["total_commitment_time_days"] = (
        df["transit_time_days"] + df["production_time_proxy_days"]
    )

    # --- 5. Resolve revenue_tier: real join first, heuristic fallback ---
    if project_priority is not None and not project_priority.empty and "revenue_tier" in project_priority.columns:
        tier_map = (
            project_priority[["project_id", "revenue_tier"]]
            .drop_duplicates(subset=["project_id"])
        )
        df = df.merge(tier_map, on="project_id", how="left")
        # Heuristic fallback for rows without a match
        missing = df["revenue_tier"].isna()
        if missing.any():
            df.loc[missing, "revenue_tier"] = df.loc[missing, "logistics_risk_score"].apply(_derive_revenue_tier)
    else:
        df["revenue_tier"] = df["logistics_risk_score"].apply(_derive_revenue_tier)

    # --- 6. Join service policy on revenue_tier ---
    if service_policy.empty:
        df["max_allowed_late_days"] = 7  # conservative fallback
        df["expedite_allowed_flag"] = False
    else:
        policy_cols = service_policy[
            ["revenue_tier", "max_allowed_late_days", "expedite_allowed_flag"]
        ].drop_duplicates(subset=["revenue_tier"])
        df = df.merge(policy_cols, on="revenue_tier", how="left")
        df["max_allowed_late_days"] = df["max_allowed_late_days"].fillna(7).astype(int)
        df["expedite_allowed_flag"] = df["expedite_allowed_flag"].fillna(False).astype(bool)

    # --- 7. days_until_deadline = (requested_delivery_date - week_date).days ---
    df["days_until_deadline"] = (df["requested_delivery_date"] - df["week_date"]).dt.days

    # --- 8. lateness_exposure = max(0, total_commitment_time_days - days_until_deadline) ---
    df["lateness_exposure"] = (
        df["total_commitment_time_days"] - df["days_until_deadline"]
    ).clip(lower=0)

    # --- 9. service_violation_risk = clip(lateness_exposure / max(days_until_deadline, 1), 0, 1) ---
    denom = df["days_until_deadline"].clip(lower=1)
    df["service_violation_risk"] = (df["lateness_exposure"] / denom).clip(0, 1)

    # --- 10. on_time_feasible_flag from policy constraint ---
    df["on_time_feasible_flag"] = (
        df["total_commitment_time_days"]
        <= (df["days_until_deadline"] + df["max_allowed_late_days"])
    )

    # --- 11. expedite_option_flag from service policy ---
    df["expedite_option_flag"] = df["expedite_allowed_flag"]

    # --- 12. Label synthetic assumptions ---
    df["synthetic_delivery_assumption"] = True

    # --- 13. Select and cast output columns ---
    result = df[_REQUIRED_OUTPUT_COLS].copy()
    result["on_time_feasible_flag"] = result["on_time_feasible_flag"].astype(bool)
    result["expedite_option_flag"] = result["expedite_option_flag"].astype(bool)
    result["service_violation_risk"] = result["service_violation_risk"].astype(float)
    result["requested_delivery_date"] = pd.to_datetime(
        result["requested_delivery_date"]
    ).dt.date

    # --- 14. Deduplicate on natural key ---
    key_cols = ["scope_id", "scenario", "project_id", "plant", "week"]
    result = result.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)

    return result
