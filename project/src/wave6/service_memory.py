"""
service_memory.py
=================
Wave 6 Carolina: build fact_quarter_service_memory from scoped logistics and
delivery commitment.

Uses expected_value scenario only (deterministic base).

Usage:
  from project.src.wave6.service_memory import build_fact_quarter_service_memory
"""

from __future__ import annotations

import pandas as pd

_REQUIRED_OUTPUT_COLS = [
    "scope_id",
    "quarter_id",
    "project_id",
    "prior_on_time_feasible_flag",
    "prior_expedite_flag",
    "prior_service_violation_risk",
    "carry_over_service_caution_flag",
    "explanation_note",
]


def week_to_quarter(week_str: str) -> str:
    """Map YYYY-Www to YYYY-Q[1-4].

    W01-W13 -> Q1, W14-W26 -> Q2, W27-W39 -> Q3, W40-W53 -> Q4
    """
    year, week_part = week_str.split("-W")
    w = int(week_part)
    if w <= 13:
        q = 1
    elif w <= 26:
        q = 2
    elif w <= 39:
        q = 3
    else:
        q = 4
    return f"{year}-Q{q}"


def _empty_memory() -> pd.DataFrame:
    return pd.DataFrame(columns=_REQUIRED_OUTPUT_COLS)


def _derive_explanation_note(
    carry_over: bool,
    violation_risk: float,
    on_time: bool,
    quarter_id: str,
) -> str:
    if carry_over and violation_risk > 0.4:
        return (
            f"High service violation risk in {quarter_id} "
            "— apply caution buffer in next quarter"
        )
    if carry_over and not on_time:
        return (
            f"Majority of weeks infeasible in {quarter_id} "
            "— consider rerouting or upshift"
        )
    return f"Service levels met in {quarter_id} — maintain current approach"


def build_fact_quarter_service_memory(
    scoped_logistics: pd.DataFrame,
    delivery_commitment: pd.DataFrame,
) -> pd.DataFrame:
    """Build quarterly service memory fact table.

    Parameters
    ----------
    scoped_logistics:
        fact_scoped_logistics_weekly — columns include:
        scope_id, scenario, project_id, week,
        on_time_feasible_flag, expedite_option_flag
    delivery_commitment:
        fact_delivery_commitment_weekly — columns include:
        scope_id, scenario, project_id, week, service_violation_risk

    Returns
    -------
    DataFrame with _REQUIRED_OUTPUT_COLS, expected_value scenario only.
    Deduplicated on (scope_id, quarter_id, project_id).
    """
    if scoped_logistics.empty or delivery_commitment.empty:
        return _empty_memory()

    # --- 1. Filter both to expected_value scenario ---
    ev_logistics = scoped_logistics[
        scoped_logistics["scenario"] == "expected_value"
    ].copy()
    ev_commitment = delivery_commitment[
        delivery_commitment["scenario"] == "expected_value"
    ].copy()

    if ev_logistics.empty or ev_commitment.empty:
        return _empty_memory()

    # --- 2. Add quarter_id to logistics ---
    ev_logistics["quarter_id"] = ev_logistics["week"].apply(week_to_quarter)

    # --- 3. Aggregate logistics to (scope_id, scenario, project_id, quarter_id) ---
    logi_agg = (
        ev_logistics.groupby(["scope_id", "project_id", "quarter_id"])
        .agg(
            prior_on_time_feasible_flag=("on_time_feasible_flag", "mean"),
            prior_expedite_flag=("expedite_option_flag", "mean"),
        )
        .reset_index()
    )
    # Convert mean -> bool by threshold
    logi_agg["prior_on_time_feasible_flag"] = (
        logi_agg["prior_on_time_feasible_flag"] >= 0.5
    )
    logi_agg["prior_expedite_flag"] = logi_agg["prior_expedite_flag"] >= 0.3

    # --- 4. Add quarter_id to commitment, aggregate violation risk ---
    ev_commitment["quarter_id"] = ev_commitment["week"].apply(week_to_quarter)
    commit_agg = (
        ev_commitment.groupby(["scope_id", "project_id", "quarter_id"])
        .agg(prior_service_violation_risk=("service_violation_risk", "mean"))
        .reset_index()
    )

    # --- 5. Join the two aggregations ---
    merged = logi_agg.merge(
        commit_agg,
        on=["scope_id", "project_id", "quarter_id"],
        how="left",
    )
    merged["prior_service_violation_risk"] = (
        merged["prior_service_violation_risk"].fillna(0.0)
    )

    # --- 6. carry_over_service_caution_flag ---
    merged["carry_over_service_caution_flag"] = (
        (~merged["prior_on_time_feasible_flag"])
        | (merged["prior_service_violation_risk"] > 0.4)
    )

    # --- 7. explanation_note ---
    merged["explanation_note"] = merged.apply(
        lambda r: _derive_explanation_note(
            carry_over=bool(r["carry_over_service_caution_flag"]),
            violation_risk=float(r["prior_service_violation_risk"]),
            on_time=bool(r["prior_on_time_feasible_flag"]),
            quarter_id=r["quarter_id"],
        ),
        axis=1,
    )

    # --- 8. Select output columns and cast types ---
    result = merged[_REQUIRED_OUTPUT_COLS].copy()
    result["prior_on_time_feasible_flag"] = result["prior_on_time_feasible_flag"].astype(bool)
    result["prior_expedite_flag"] = result["prior_expedite_flag"].astype(bool)
    result["carry_over_service_caution_flag"] = result["carry_over_service_caution_flag"].astype(bool)
    result["prior_service_violation_risk"] = result["prior_service_violation_risk"].astype(float)

    # --- 9. Deduplicate on natural key ---
    key_cols = ["scope_id", "quarter_id", "project_id"]
    result = result.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)

    return result
