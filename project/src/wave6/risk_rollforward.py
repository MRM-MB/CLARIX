"""
risk_rollforward.py
===================
Wave 6 Carolina: build fact_delivery_risk_rollforward from Q1 service memory
projected forward to Q2 planning caution.

Business intent: Q1 service failures → caution buffer recommendations for Q2.

Usage:
  from project.src.wave6.risk_rollforward import build_fact_delivery_risk_rollforward
"""

from __future__ import annotations

import pandas as pd

_REQUIRED_OUTPUT_COLS = [
    "scope_id",
    "source_quarter_id",
    "carry_forward_quarter_id",
    "project_id",
    "prior_service_violation_risk",
    "carry_over_service_caution_flag",
    "recommended_caution_level",
    "caution_explanation",
    "synthetic_dependency_flag",
]


def _empty_rollforward() -> pd.DataFrame:
    return pd.DataFrame(columns=_REQUIRED_OUTPUT_COLS)


def _next_quarter(quarter_id: str) -> str:
    """Advance any quarter by one.

    Examples: '2026-Q1' -> '2026-Q2', '2026-Q4' -> '2027-Q1'
    """
    year, q = quarter_id.split("-Q")
    q_num = int(q)
    if q_num < 4:
        return f"{year}-Q{q_num + 1}"
    return f"{int(year) + 1}-Q1"


def _caution_level(carry_over: bool, violation_risk: float) -> str:
    if carry_over and violation_risk > 0.6:
        return "high"
    if carry_over and violation_risk > 0.3:
        return "medium"
    return "low"


def _caution_explanation(level: str) -> str:
    if level == "high":
        return "Q1 had critical service failures — add 2-week buffer to Q2 lead times"
    if level == "medium":
        return "Q1 had moderate risk — add 1-week buffer and monitor expedite options"
    return "Q1 was clean — proceed with standard Q2 planning"


def build_fact_delivery_risk_rollforward(
    service_memory: pd.DataFrame,
    logistics_snapshot: pd.DataFrame,
) -> pd.DataFrame:
    """Build delivery risk rollforward from Q1 service memory to Q2.

    Parameters
    ----------
    service_memory:
        fact_quarter_service_memory — columns include:
        scope_id, quarter_id, project_id,
        prior_service_violation_risk, carry_over_service_caution_flag
    logistics_snapshot:
        fact_logistics_quarterly_snapshot — columns include:
        scope_id, plant, quarter_id, avg_transit_time_days

    Returns
    -------
    DataFrame with _REQUIRED_OUTPUT_COLS.
    Deduplicated on (scope_id, source_quarter_id, project_id).
    synthetic_dependency_flag = True (logistics snapshot is synthetic).
    """
    if service_memory.empty:
        return _empty_rollforward()

    # --- 1. All quarters roll forward (not just Q1) ---
    q1_memory = service_memory.copy()
    q1_memory = q1_memory.rename(columns={"quarter_id": "source_quarter_id"})

    # --- 2. Compute carry_forward_quarter_id (any quarter -> next quarter) ---
    q1_memory["carry_forward_quarter_id"] = q1_memory["source_quarter_id"].apply(_next_quarter)

    # --- 3. Join logistics_snapshot Q2 signal on (scope_id, plant) ---
    # This enriches the data with transit time signal but doesn't change the key grain.
    # The join is optional — we proceed without it if logistics_snapshot is empty
    # (avg_transit_time_days is informational, not used in caution logic here).
    if not logistics_snapshot.empty and "avg_transit_time_days" in logistics_snapshot.columns:
        q2_logi = logistics_snapshot[
            logistics_snapshot["quarter_id"].str.endswith("Q2")
        ][["scope_id", "plant", "avg_transit_time_days"]].drop_duplicates(
            subset=["scope_id", "plant"]
        )
        # We only join if plant is present in service_memory
        if "plant" in q1_memory.columns:
            q1_memory = q1_memory.merge(q2_logi, on=["scope_id", "plant"], how="left")

    # --- 4. recommended_caution_level ---
    q1_memory["recommended_caution_level"] = q1_memory.apply(
        lambda r: _caution_level(
            carry_over=bool(r["carry_over_service_caution_flag"]),
            violation_risk=float(r["prior_service_violation_risk"]),
        ),
        axis=1,
    )

    # --- 5. caution_explanation ---
    q1_memory["caution_explanation"] = q1_memory["recommended_caution_level"].apply(
        _caution_explanation
    )

    # --- 6. synthetic_dependency_flag = True (logistics snapshot is synthetic) ---
    q1_memory["synthetic_dependency_flag"] = True

    # --- 7. Select output columns ---
    # Only keep columns that exist in _REQUIRED_OUTPUT_COLS
    available = [c for c in _REQUIRED_OUTPUT_COLS if c in q1_memory.columns]
    result = q1_memory[available].copy()

    # Ensure all required columns exist (fill missing with safe defaults)
    for col in _REQUIRED_OUTPUT_COLS:
        if col not in result.columns:
            result[col] = None

    result = result[_REQUIRED_OUTPUT_COLS].copy()

    # --- 8. Cast types ---
    result["prior_service_violation_risk"] = result["prior_service_violation_risk"].astype(float)
    result["carry_over_service_caution_flag"] = result["carry_over_service_caution_flag"].astype(bool)
    result["synthetic_dependency_flag"] = result["synthetic_dependency_flag"].astype(bool)

    # --- 9. Deduplicate on natural key ---
    key_cols = ["scope_id", "source_quarter_id", "project_id"]
    result = result.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)

    return result
