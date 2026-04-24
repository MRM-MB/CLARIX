"""
decision_history.py
===================
Wave 5 Carolina: build material decision history from Q1 → Q2 carry-over analysis.

Usage:
  from project.src.wave5.decision_history import build_material_decision_history
"""

from __future__ import annotations

import pandas as pd

_REQUIRED_HISTORY_COLS = [
    "scope_id", "quarter_id", "plant", "component_material",
    "prior_order_recommendation", "prior_shortage_flag", "prior_expedite_flag",
    "prior_on_time_feasible_flag", "carry_over_material_risk_flag", "learning_note",
]


def _empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=_REQUIRED_HISTORY_COLS)


def _derive_learning_note(
    carry_over: bool,
    shortage: bool,
    expedite: bool,
    on_time: bool,
) -> str:
    if carry_over:
        return "Q1 had shortages or expedite issues — increase safety buffer in Q2"
    if shortage:
        return "Q1 shortage detected — order earlier in Q2"
    if expedite:
        return "Q1 required expediting — review lead time assumptions"
    return "Q1 performance acceptable — maintain current strategy"


def build_material_decision_history(
    sourcing_snapshot: pd.DataFrame,
    logistics_snapshot: pd.DataFrame,
) -> pd.DataFrame:
    """Build fact_material_decision_history from Q1 sourcing + logistics snapshots.

    Business intent: for each (plant, component_material), look at Q1 performance
    and flag carry-over risks for Q2.

    Steps:
    1. Filter sourcing_snapshot to scenario='expected_value'
    2. For each (scope_id, plant, component_material): extract Q1 row
    3. Join logistics Q1 on (scope_id, plant) for expedite/on-time signals
    4. Derive carry_over_material_risk_flag and learning_note
    """
    if sourcing_snapshot.empty:
        return _empty_history()

    # --- 1. Filter to expected_value scenario ---
    ev_mask = sourcing_snapshot["scenario"] == "expected_value"
    ev_sourcing = sourcing_snapshot[ev_mask].copy()

    if ev_sourcing.empty:
        # Fallback: use whatever scenario is present
        ev_sourcing = sourcing_snapshot.copy()

    # --- 2. Extract Q1 rows ---
    q1_sourcing = ev_sourcing[ev_sourcing["quarter_id"].str.endswith("Q1")].copy()

    if q1_sourcing.empty:
        return _empty_history()

    # --- 3. Build logistics Q1 index (scope_id, plant) -> (pct_expedite, pct_on_time) ---
    logi_q1_index: dict[tuple, tuple] = {}
    if not logistics_snapshot.empty:
        logi_q1 = logistics_snapshot[logistics_snapshot["quarter_id"].str.endswith("Q1")].copy()
        if not logi_q1.empty:
            # Aggregate to plant level (average across destination countries)
            logi_plant = (
                logi_q1.groupby(["scope_id", "plant"])
                .agg(
                    pct_expedite_option=("pct_expedite_option", "mean"),
                    pct_on_time_feasible=("pct_on_time_feasible", "mean"),
                )
                .reset_index()
            )
            for _, row in logi_plant.iterrows():
                key = (row["scope_id"], row["plant"])
                logi_q1_index[key] = (
                    float(row["pct_expedite_option"]),
                    float(row["pct_on_time_feasible"]),
                )

    # --- 4. Build one row per (scope_id, quarter_id, plant, component_material) ---
    records = []
    for _, row in q1_sourcing.iterrows():
        scope_id = row["scope_id"]
        plant = row["plant"]
        quarter_id = row["quarter_id"]
        component_material = row["component_material"]

        prior_order_recommendation = str(row.get("earliest_recommended_order_date", ""))
        prior_shortage_flag = bool(int(row.get("shortage_weeks_count", 0)) > 0)

        # Logistics signals from index
        logi_key = (scope_id, plant)
        if logi_key in logi_q1_index:
            pct_expedite, pct_on_time = logi_q1_index[logi_key]
        else:
            pct_expedite, pct_on_time = 0.0, 1.0  # conservative defaults

        prior_expedite_flag = pct_expedite > 0.3
        prior_on_time_feasible_flag = pct_on_time >= 0.8

        carry_over_material_risk_flag = bool(
            prior_shortage_flag or (prior_expedite_flag and not prior_on_time_feasible_flag)
        )

        learning_note = _derive_learning_note(
            carry_over=carry_over_material_risk_flag,
            shortage=prior_shortage_flag,
            expedite=prior_expedite_flag,
            on_time=prior_on_time_feasible_flag,
        )

        records.append({
            "scope_id": scope_id,
            "quarter_id": quarter_id,
            "plant": plant,
            "component_material": component_material,
            "prior_order_recommendation": prior_order_recommendation,
            "prior_shortage_flag": prior_shortage_flag,
            "prior_expedite_flag": prior_expedite_flag,
            "prior_on_time_feasible_flag": prior_on_time_feasible_flag,
            "carry_over_material_risk_flag": carry_over_material_risk_flag,
            "learning_note": learning_note,
        })

    if not records:
        return _empty_history()

    result = pd.DataFrame(records)

    # Deduplicate on natural key — keep first occurrence
    key_cols = ["scope_id", "quarter_id", "plant", "component_material"]
    result = result.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)

    return result
