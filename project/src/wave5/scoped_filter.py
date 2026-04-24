"""
scoped_filter.py
================
Wave 5 Carolina: filter sourcing and logistics data to MVP scope plants.

Usage:
  from project.src.wave5.scoped_filter import filter_sourcing, filter_logistics, DEFAULT_SCOPE
"""

from __future__ import annotations

import pandas as pd

DEFAULT_SCOPE = {
    "scope_id": "mvp_3plant",
    "plants": ["NW01", "NW02", "NW05"],  # North America, Europe West, East Asia
    "description": "MVP scope: 3 representative plants across NA/EU/APAC",
}


def filter_sourcing(df: pd.DataFrame, scope: dict = DEFAULT_SCOPE) -> pd.DataFrame:
    """Filter fact_scenario_sourcing_weekly to scope plants.

    Returns fact_scoped_sourcing_weekly with an added scope_id column.
    Asserts scoped row count <= base row count.
    """
    if df.empty:
        out = df.copy()
        out["scope_id"] = pd.Series(dtype="object")
        return out

    plants = scope["plants"]
    scoped = df[df["plant"].isin(plants)].copy()
    scoped["scope_id"] = scope["scope_id"]

    assert len(scoped) <= len(df), (
        f"filter_sourcing: scoped rows ({len(scoped)}) > base rows ({len(df)}) — data integrity error"
    )

    return scoped.reset_index(drop=True)


def filter_logistics(df: pd.DataFrame, scope: dict = DEFAULT_SCOPE) -> pd.DataFrame:
    """Filter fact_scenario_logistics_weekly to scope plants.

    Returns fact_scoped_logistics_weekly with an added scope_id column.
    Asserts scoped row count <= base row count.
    """
    if df.empty:
        out = df.copy()
        out["scope_id"] = pd.Series(dtype="object")
        return out

    plants = scope["plants"]
    scoped = df[df["plant"].isin(plants)].copy()
    scoped["scope_id"] = scope["scope_id"]

    assert len(scoped) <= len(df), (
        f"filter_logistics: scoped rows ({len(scoped)}) > base rows ({len(df)}) — data integrity error"
    )

    return scoped.reset_index(drop=True)
