"""
quarterly_snapshot.py
=====================
Wave 5 Carolina: aggregate weekly scoped data into quarterly snapshots.

Usage:
  from project.src.wave5.quarterly_snapshot import (
      week_to_quarter,
      build_sourcing_quarterly_snapshot,
      build_logistics_quarterly_snapshot,
  )
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def week_to_quarter(week_str: str) -> str:
    """Convert a week string (YYYY-Www) to a quarter string (YYYY-Qn).

    Mapping:
      W01-W13 -> Q1
      W14-W26 -> Q2
      W27-W39 -> Q3
      W40-W52 -> Q4
      W53     -> Q4 (edge case)
    """
    try:
        year, week_part = week_str.split("-W")
        week_num = int(week_part)
    except (ValueError, AttributeError):
        return "UNKNOWN-Q0"

    if week_num <= 13:
        q = 1
    elif week_num <= 26:
        q = 2
    elif week_num <= 39:
        q = 3
    else:
        q = 4

    return f"{year}-Q{q}"


def build_sourcing_quarterly_snapshot(scoped_sourcing: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fact_scoped_sourcing_weekly into fact_sourcing_quarterly_snapshot.

    Groups by (scope_id, scenario, plant, component_material, quarter_id).
    synthetic_dependency_flag = False (sourcing uses real data).
    """
    if scoped_sourcing.empty:
        return pd.DataFrame(columns=[
            "scope_id", "scenario", "plant", "component_material", "quarter_id",
            "total_demand_qty", "total_shortage_qty", "shortage_weeks_count",
            "avg_sourcing_risk_score", "max_sourcing_risk_score",
            "earliest_recommended_order_date", "synthetic_dependency_flag",
        ])

    df = scoped_sourcing.copy()
    df["quarter_id"] = df["week"].apply(week_to_quarter)

    # Coerce shortage_flag to bool
    df["shortage_flag"] = df["shortage_flag"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    ).fillna(False)

    # Coerce recommended_order_date to datetime for min aggregation
    df["recommended_order_date"] = pd.to_datetime(df["recommended_order_date"], errors="coerce")

    group_keys = ["scope_id", "scenario", "plant", "component_material", "quarter_id"]

    agg = df.groupby(group_keys, sort=False).agg(
        total_demand_qty=("component_demand_qty", "sum"),
        total_shortage_qty=("shortage_qty", "sum"),
        shortage_weeks_count=("shortage_flag", "sum"),
        avg_sourcing_risk_score=("sourcing_risk_score", "mean"),
        max_sourcing_risk_score=("sourcing_risk_score", "max"),
        earliest_recommended_order_date=("recommended_order_date", "min"),
    ).reset_index()

    agg["shortage_weeks_count"] = agg["shortage_weeks_count"].astype(int)
    agg["earliest_recommended_order_date"] = agg["earliest_recommended_order_date"].dt.strftime("%Y-%m-%d")
    agg["synthetic_dependency_flag"] = False

    return agg


def build_logistics_quarterly_snapshot(scoped_logistics: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fact_scoped_logistics_weekly into fact_logistics_quarterly_snapshot.

    Groups by (scope_id, scenario, plant, destination_country, quarter_id).
    synthetic_dependency_flag = True (logistics uses synthetic lane data).
    """
    if scoped_logistics.empty:
        return pd.DataFrame(columns=[
            "scope_id", "scenario", "plant", "destination_country", "quarter_id",
            "route_count", "avg_transit_time_days", "avg_shipping_cost",
            "avg_landed_cost_proxy", "pct_on_time_feasible", "pct_expedite_option",
            "avg_logistics_risk_score", "synthetic_dependency_flag",
        ])

    df = scoped_logistics.copy()
    df["quarter_id"] = df["week"].apply(week_to_quarter)

    # Coerce boolean flags to float for mean
    for col in ("on_time_feasible_flag", "expedite_option_flag"):
        df[col] = df[col].astype(str).str.lower().map(
            {"true": True, "false": False, "1": True, "0": False}
        ).fillna(False).astype(float)

    group_keys = ["scope_id", "scenario", "plant", "destination_country", "quarter_id"]

    agg = df.groupby(group_keys, sort=False).agg(
        route_count=("project_id", "nunique"),
        avg_transit_time_days=("transit_time_days", "mean"),
        avg_shipping_cost=("shipping_cost", "mean"),
        avg_landed_cost_proxy=("landed_cost_proxy", "mean"),
        pct_on_time_feasible=("on_time_feasible_flag", "mean"),
        pct_expedite_option=("expedite_option_flag", "mean"),
        avg_logistics_risk_score=("logistics_risk_score", "mean"),
    ).reset_index()

    agg["synthetic_dependency_flag"] = True

    return agg
