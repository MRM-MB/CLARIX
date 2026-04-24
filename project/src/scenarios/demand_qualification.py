"""Wave 1 scenario seed tables for downstream engines."""

from __future__ import annotations

import numpy as np
import pandas as pd


SCENARIO_FAMILY = "pipeline"


def build_scenario_project_demand_seed(fact_pipeline_monthly: pd.DataFrame) -> pd.DataFrame:
    """Materialize scenario seed rows for all_in, expected_value, and high_confidence."""

    if fact_pipeline_monthly.empty:
        return pd.DataFrame(
            columns=[
                "scenario_name",
                "scenario_family",
                "scenario_confidence",
                "project_id",
                "plant",
                "material",
                "month",
                "raw_qty",
                "probability",
                "scenario_qty",
                "project_value",
                "expected_value",
                "priority_score",
                "mapping_ready_flag",
                "reason_code",
            ]
        )

    base = fact_pipeline_monthly.copy()
    scenarios: list[tuple[str, float, pd.Series]] = [
        ("all_in", 1.00, base["raw_qty"]),
        ("expected_value", base["probability"], base["expected_qty"]),
        (
            "high_confidence",
            np.where(base["probability"] >= 0.70, 0.90, 0.60),
            np.where(base["probability"] >= 0.70, base["raw_qty"], 0.0),
        ),
    ]

    parts = []
    keep = [
        "project_id",
        "plant",
        "material",
        "month",
        "raw_qty",
        "probability",
        "project_value",
        "expected_value",
        "priority_score",
        "mapping_ready_flag",
        "reason_code",
    ]
    for scenario_name, scenario_confidence, scenario_qty in scenarios:
        tmp = base[keep].copy()
        tmp["scenario_name"] = scenario_name
        tmp["scenario_family"] = SCENARIO_FAMILY
        tmp["scenario_confidence"] = scenario_confidence
        tmp["scenario_qty"] = pd.Series(scenario_qty, index=tmp.index, dtype=float)
        parts.append(tmp)

    out = pd.concat(parts, ignore_index=True)
    ordered = [
        "scenario_name",
        "scenario_family",
        "scenario_confidence",
        "project_id",
        "plant",
        "material",
        "month",
        "raw_qty",
        "probability",
        "scenario_qty",
        "project_value",
        "expected_value",
        "priority_score",
        "mapping_ready_flag",
        "reason_code",
    ]
    return out[ordered].sort_values(["scenario_name", "project_id", "month"]).reset_index(drop=True)
