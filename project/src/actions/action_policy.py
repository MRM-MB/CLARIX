"""Wave 3 Carolina: dim_action_policy builder.

Produces a hardcoded configuration table — one row per action family.
No data input required.
"""

from __future__ import annotations

import pandas as pd


def build_dim_action_policy() -> pd.DataFrame:
    """Return the dim_action_policy table with 9 action families.

    Returns
    -------
    pd.DataFrame
        Columns: action_type, trigger_condition, minimum_priority_threshold,
        minimum_risk_threshold, requires_alt_plant_flag, allows_expedite_flag,
        allows_upshift_flag, expected_effect_type, policy_version
    """
    rows = [
        {
            "action_type": "buy_now",
            "trigger_condition": (
                "sourcing_risk_score >= 0.7 AND shortage_flag AND lead_time allows"
            ),
            "minimum_priority_threshold": 0.3,
            "minimum_risk_threshold": 0.6,
            "requires_alt_plant_flag": False,
            "allows_expedite_flag": False,
            "allows_upshift_flag": False,
            "expected_effect_type": "reduce_shortage",
            "policy_version": "v1",
        },
        {
            "action_type": "wait",
            "trigger_condition": (
                "risk_score_base < 0.3 AND priority_score < 0.4"
            ),
            "minimum_priority_threshold": 0.0,
            "minimum_risk_threshold": 0.0,
            "requires_alt_plant_flag": False,
            "allows_expedite_flag": False,
            "allows_upshift_flag": False,
            "expected_effect_type": "hedge_uncertainty",
            "policy_version": "v1",
        },
        {
            "action_type": "reroute",
            "trigger_condition": (
                "logistics_risk_score >= 0.5 AND alt plant available with capacity"
            ),
            "minimum_priority_threshold": 0.4,
            "minimum_risk_threshold": 0.4,
            "requires_alt_plant_flag": True,
            "allows_expedite_flag": False,
            "allows_upshift_flag": False,
            "expected_effect_type": "reduce_delay",
            "policy_version": "v1",
        },
        {
            "action_type": "upshift",
            "trigger_condition": (
                "capacity_risk_score >= 0.8 AND upshift limit available"
            ),
            "minimum_priority_threshold": 0.3,
            "minimum_risk_threshold": 0.5,
            "requires_alt_plant_flag": False,
            "allows_expedite_flag": False,
            "allows_upshift_flag": True,
            "expected_effect_type": "reduce_overload",
            "policy_version": "v1",
        },
        {
            "action_type": "expedite_shipping",
            "trigger_condition": (
                "logistics_risk_score >= 0.6 AND expedite_allowed_flag"
            ),
            "minimum_priority_threshold": 0.5,
            "minimum_risk_threshold": 0.5,
            "requires_alt_plant_flag": False,
            "allows_expedite_flag": True,
            "allows_upshift_flag": False,
            "expected_effect_type": "reduce_delay",
            "policy_version": "v1",
        },
        {
            "action_type": "reschedule",
            "trigger_condition": (
                "capacity_risk_score >= 0.6 AND priority_score < 0.5"
            ),
            "minimum_priority_threshold": 0.0,
            "minimum_risk_threshold": 0.4,
            "requires_alt_plant_flag": False,
            "allows_expedite_flag": False,
            "allows_upshift_flag": False,
            "expected_effect_type": "reduce_overload",
            "policy_version": "v1",
        },
        {
            "action_type": "escalate",
            "trigger_condition": (
                "action_score_base >= 0.8 AND top_driver in [capacity_risk, sourcing_risk]"
            ),
            "minimum_priority_threshold": 0.7,
            "minimum_risk_threshold": 0.7,
            "requires_alt_plant_flag": False,
            "allows_expedite_flag": False,
            "allows_upshift_flag": False,
            "expected_effect_type": "escalate_decision",
            "policy_version": "v1",
        },
        {
            "action_type": "hedge_inventory",
            "trigger_condition": (
                "sourcing_risk_score >= 0.5 AND coverage_days_or_weeks < 14"
            ),
            "minimum_priority_threshold": 0.2,
            "minimum_risk_threshold": 0.3,
            "requires_alt_plant_flag": False,
            "allows_expedite_flag": False,
            "allows_upshift_flag": False,
            "expected_effect_type": "hedge_uncertainty",
            "policy_version": "v1",
        },
        {
            "action_type": "split_production",
            "trigger_condition": (
                "capacity_risk_score >= 0.7 AND alt plant available"
            ),
            "minimum_priority_threshold": 0.4,
            "minimum_risk_threshold": 0.6,
            "requires_alt_plant_flag": True,
            "allows_expedite_flag": False,
            "allows_upshift_flag": False,
            "expected_effect_type": "reduce_overload",
            "policy_version": "v1",
        },
    ]

    df = pd.DataFrame(rows)
    df["requires_alt_plant_flag"] = df["requires_alt_plant_flag"].astype(bool)
    df["allows_expedite_flag"] = df["allows_expedite_flag"].astype(bool)
    df["allows_upshift_flag"] = df["allows_upshift_flag"].astype(bool)
    df["minimum_priority_threshold"] = df["minimum_priority_threshold"].astype(float)
    df["minimum_risk_threshold"] = df["minimum_risk_threshold"].astype(float)
    return df
