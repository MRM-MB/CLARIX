"""
src/carolina/logistics_engine.py

Logistics engine for Carolina Wave 2.
Maps demand rows to shipping lanes and cost indices to produce a weekly
logistics feasibility and risk table.

NOTE: All shipping/cost dimensions originate from synthetic data sources.
      All output rows carry synthetic_dependency_flag=True.
"""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Plant -> origin country
PLANT_TO_COUNTRY: dict[str, str] = {
    "NW01": "US",
    "NW02": "DE",
    "NW03": "PL",
    "NW04": "IN",
    "NW05": "CN",
    "NW06": "US",
    "NW07": "US",
    "NW08": "ES",
    "NW09": "CH",
    "NW10": "LV",
    "NW11": "IL",
    "NW12": "BR",
    "NW13": "CL",
    "NW14": "AU",
    "NW15": "VN",
}

# Plant -> destination country (estimated from plant region)
PLANT_TO_DEST_COUNTRY: dict[str, str] = {
    "NW01": "US",
    "NW06": "US",
    "NW07": "US",
    "NW02": "DE",
    "NW08": "DE",
    "NW09": "DE",
    "NW03": "PL",
    "NW10": "PL",
    "NW04": "IN",
    "NW05": "CN",
    "NW15": "CN",
    "NW11": "IL",
    "NW12": "BR",
    "NW13": "BR",
    "NW14": "AU",
}

# Revenue tier thresholds based on priority_score
def _priority_to_revenue_tier(priority: float) -> str:
    if priority < 0.3:
        return "Small"
    elif priority < 0.5:
        return "Medium"
    elif priority < 0.75:
        return "Large"
    else:
        return "Strategic"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_week_to_monday(week_str: str) -> pd.Timestamp:
    """Convert 'YYYY-Www' (Luigi W2 format) to Monday of that ISO week."""
    try:
        return pd.Timestamp(datetime.strptime(f"{week_str}-1", "%G-W%V-%u"))
    except ValueError:
        return pd.NaT


def _load_translated_demand(real_processed_dir: str) -> pd.DataFrame:
    """Load fact_translated_project_demand_weekly from Luigi W2 output dir."""
    demand_path = os.path.join(real_processed_dir, "fact_translated_project_demand_weekly.csv")
    print(f"[logistics_engine] Loading demand from {demand_path}")
    return pd.read_csv(demand_path)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_logistics_engine(
    real_processed_dir: str = "project/data/processed",
    synth_processed_dir: str = "processed",
) -> pd.DataFrame:
    """
    Run the logistics engine.

    Parameters
    ----------
    real_processed_dir : str
        Directory with Luigi/Lara W1+2 outputs (fact_translated_project_demand_weekly).
    synth_processed_dir : str
        Directory with Carolina W1 synthetic outputs (dim_shipping_lane_synth,
        dim_country_cost_index_synth, dim_service_level_policy_synth).

    Returns
    -------
    pd.DataFrame with columns:
        scenario, project_id, plant, destination_country, week,
        transit_time_days, shipping_cost, landed_cost_proxy,
        on_time_feasible_flag, expedite_option_flag,
        logistics_risk_score, synthetic_dependency_flag
    """
    # ------------------------------------------------------------------
    # 1. Load translated demand from Luigi W2
    # ------------------------------------------------------------------
    demand = _load_translated_demand(real_processed_dir)

    required_cols = {"scenario", "project_id", "plant", "material", "week", "expected_weekly_qty"}
    missing = required_cols - set(demand.columns)
    if missing:
        raise ValueError(f"Demand table missing columns: {missing}")

    demand["expected_weekly_qty"] = pd.to_numeric(
        demand["expected_weekly_qty"], errors="coerce"
    ).fillna(0.0)
    demand["priority_score"] = pd.to_numeric(
        demand.get("priority_score", pd.Series(0.5, index=demand.index)),
        errors="coerce",
    ).fillna(0.5)

    # ------------------------------------------------------------------
    # 2. Load dimension tables
    # ------------------------------------------------------------------
    lanes_path = os.path.join(synth_processed_dir, "dim_shipping_lane_synth.csv")
    cost_path = os.path.join(synth_processed_dir, "dim_country_cost_index_synth.csv")
    svc_path = os.path.join(synth_processed_dir, "dim_service_level_policy_synth.csv")

    lanes = pd.read_csv(lanes_path)
    cost_idx = pd.read_csv(cost_path)
    service = pd.read_csv(svc_path)

    # Normalise boolean columns in service level
    for bool_col in ["expedite_allowed_flag", "reroute_allowed_flag", "premium_shipping_allowed_flag"]:
        if bool_col in service.columns:
            service[bool_col] = service[bool_col].astype(str).str.lower().isin(["true", "1", "yes"])

    # ------------------------------------------------------------------
    # 3. Map plant to origin and destination countries
    # ------------------------------------------------------------------
    df = demand.copy()
    df["origin_country"] = df["plant"].map(PLANT_TO_COUNTRY).fillna("US")
    df["destination_country"] = df["plant"].map(PLANT_TO_DEST_COUNTRY).fillna("US")

    # ------------------------------------------------------------------
    # 4. Join shipping lanes on (origin_country, destination_country)
    # ------------------------------------------------------------------
    df = df.merge(
        lanes[[
            "origin_country", "destination_country",
            "transit_time_days_synth", "base_shipping_cost_synth",
            "route_reliability_score_synth", "disruption_sensitivity_score_synth",
        ]],
        on=["origin_country", "destination_country"],
        how="left",
    )

    # Fill missing lane data with sensible defaults
    df["transit_time_days_synth"] = df["transit_time_days_synth"].fillna(14.0)
    df["base_shipping_cost_synth"] = df["base_shipping_cost_synth"].fillna(1000.0)
    df["route_reliability_score_synth"] = df["route_reliability_score_synth"].fillna(0.85)
    df["disruption_sensitivity_score_synth"] = df["disruption_sensitivity_score_synth"].fillna(0.2)

    # transit_time_days
    df["transit_time_days"] = df["transit_time_days_synth"]

    # shipping_cost = base_shipping_cost_synth * max(expected_weekly_qty, 1) * 0.01
    df["shipping_cost"] = (
        df["base_shipping_cost_synth"] * df["expected_weekly_qty"].clip(lower=1.0) * 0.01
    )

    # ------------------------------------------------------------------
    # 5. Join country cost index on origin_country
    # ------------------------------------------------------------------
    df = df.merge(
        cost_idx[[
            "country_code",
            "labor_cost_index_synth",
            "energy_cost_index_synth",
            "overhead_cost_index_synth",
        ]],
        left_on="origin_country",
        right_on="country_code",
        how="left",
    ).drop(columns=["country_code"], errors="ignore")

    df["labor_cost_index_synth"] = df["labor_cost_index_synth"].fillna(1.0)
    df["energy_cost_index_synth"] = df["energy_cost_index_synth"].fillna(1.0)
    df["overhead_cost_index_synth"] = df["overhead_cost_index_synth"].fillna(1.0)

    # landed_cost_proxy = shipping_cost * (1 + labor*0.1 + energy*0.05 + overhead*0.05)
    df["landed_cost_proxy"] = df["shipping_cost"] * (
        1
        + df["labor_cost_index_synth"] * 0.1
        + df["energy_cost_index_synth"] * 0.05
        + df["overhead_cost_index_synth"] * 0.05
    )

    # ------------------------------------------------------------------
    # 6. Week date and revenue tier
    # ------------------------------------------------------------------
    week_dates = {w: _parse_week_to_monday(w) for w in df["week"].unique()}
    df["week_date"] = df["week"].map(week_dates)

    df["revenue_tier"] = df["priority_score"].apply(_priority_to_revenue_tier)

    # ------------------------------------------------------------------
    # 7. Join service level policy on revenue_tier
    # ------------------------------------------------------------------
    df = df.merge(
        service[["revenue_tier", "max_allowed_late_days", "expedite_allowed_flag"]],
        on="revenue_tier",
        how="left",
    )

    df["max_allowed_late_days"] = df["max_allowed_late_days"].fillna(14.0)
    df["expedite_allowed_flag"] = df["expedite_allowed_flag"].fillna(False).astype(bool)

    # on_time_feasible_flag: delivery assumed 4 weeks from week_date
    # feasible if transit_time_days <= max_allowed_late_days + 28
    df["on_time_feasible_flag"] = (
        df["transit_time_days"] <= (df["max_allowed_late_days"] + 28)
    )

    df["expedite_option_flag"] = df["expedite_allowed_flag"]

    # ------------------------------------------------------------------
    # 8. logistics_risk_score
    # ------------------------------------------------------------------
    df["logistics_risk_score"] = (
        (1.0 - df["route_reliability_score_synth"]) * df["disruption_sensitivity_score_synth"]
    ).clip(0.0, 1.0)

    # ------------------------------------------------------------------
    # 9. synthetic_dependency_flag
    # ------------------------------------------------------------------
    df["synthetic_dependency_flag"] = True

    # ------------------------------------------------------------------
    # 10. Select output columns, dedup, return
    # ------------------------------------------------------------------
    output_cols = [
        "scenario",
        "project_id",
        "plant",
        "destination_country",
        "week",
        "transit_time_days",
        "shipping_cost",
        "landed_cost_proxy",
        "on_time_feasible_flag",
        "expedite_option_flag",
        "logistics_risk_score",
        "synthetic_dependency_flag",
    ]
    result = df[output_cols].drop_duplicates(
        subset=["scenario", "project_id", "plant", "destination_country", "week"],
        keep="first",
    ).reset_index(drop=True)

    return result
