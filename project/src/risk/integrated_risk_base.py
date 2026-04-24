"""Wave 3 Luigi: Base integrated risk engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


SCENARIO_CONFIDENCE_DEFAULTS = {
    "all_in": 1.0,
    "expected_value": None,  # project probability_score
    "high_confidence": 0.90,
    "monte_carlo_light": 0.75,
}

TOP_DRIVER_ORDER = [
    "capacity_risk_score",
    "sourcing_risk_score",
    "logistics_risk_score",
    "lead_time_risk_score",
]


@dataclass(frozen=True)
class IntegratedRiskValidation:
    row_count: int
    duplicate_key_count: int
    placeholder_disruption_nonzero: int
    placeholder_quality_nonzero: int


def load_wave3_inputs(base_dir: str | Path) -> dict[str, pd.DataFrame]:
    base = Path(base_dir)
    return {
        "dim_project_priority": pd.read_pickle(base / "dim_project_priority.pkl"),
        "fact_scenario_capacity_weekly": pd.read_csv(base / "fact_scenario_capacity_weekly.csv"),
        "fact_scenario_sourcing_weekly": pd.read_csv(base / "fact_scenario_sourcing_weekly.csv"),
        "fact_scenario_logistics_weekly": pd.read_csv(base / "fact_scenario_logistics_weekly.csv"),
    }


def _normalize_week_from_capacity(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["week"] = (
        out["year"].astype(int).astype(str)
        + "-W"
        + out["week"].astype(int).astype(str).str.zfill(2)
    )
    return out


def _aggregate_capacity(capacity: pd.DataFrame) -> pd.DataFrame:
    cap = _normalize_week_from_capacity(capacity)
    cap = cap[~cap["scenario"].str.contains("__", na=False)].copy()
    cap["capacity_risk_score"] = np.clip(
        cap["overload_hours"] / np.maximum(cap["total_load_hours"], 1.0),
        0.0,
        1.0,
    )
    agg = (
        cap.groupby(["scenario", "plant", "week"], as_index=False)
        .agg(
            capacity_risk_score=("capacity_risk_score", "max"),
            capacity_overload_pct=("overload_pct", "max"),
        )
    )
    fallback = agg[agg["scenario"] == "expected_value"].copy()
    fallback["scenario"] = "monte_carlo_light"
    agg = pd.concat([agg, fallback], ignore_index=True).drop_duplicates(
        ["scenario", "plant", "week"], keep="first"
    )
    return agg


def _aggregate_sourcing(sourcing: pd.DataFrame) -> pd.DataFrame:
    src = sourcing.copy()
    src["lead_time_risk_score"] = np.clip(
        1.0 - (pd.to_numeric(src["coverage_days_or_weeks"], errors="coerce").fillna(0.0) / 14.0),
        0.0,
        1.0,
    )
    agg = (
        src.groupby(["scenario", "plant", "week"], as_index=False)
        .agg(
            sourcing_risk_score=("sourcing_risk_score", "max"),
            lead_time_risk_score=("lead_time_risk_score", "max"),
        )
    )
    return agg


def _scenario_confidence(scenario: pd.Series, probability_score: pd.Series) -> pd.Series:
    vals = []
    for sc, prob in zip(scenario, probability_score):
        default = SCENARIO_CONFIDENCE_DEFAULTS.get(sc, 0.5)
        if default is None:
            vals.append(float(prob))
        else:
            vals.append(float(default))
    return pd.Series(vals, index=scenario.index, dtype=float).clip(0.0, 1.0)


def _top_driver(df: pd.DataFrame) -> pd.Series:
    def pick(row: pd.Series) -> str:
        best = max(TOP_DRIVER_ORDER, key=lambda c: float(row[c]))
        return best.replace("_score", "")

    return df.apply(pick, axis=1)


def _explainability_note(df: pd.DataFrame) -> pd.Series:
    notes = []
    for row in df.itertuples(index=False):
        notes.append(
            f"priority={row.priority_score:.3f}; "
            f"capacity={row.capacity_risk_score:.3f}; "
            f"sourcing={row.sourcing_risk_score:.3f}; "
            f"logistics={row.logistics_risk_score:.3f}; "
            f"lead_time={row.lead_time_risk_score:.3f}; "
            f"top_driver={row.top_driver}"
        )
    return pd.Series(notes, index=df.index, dtype="object")


def build_fact_integrated_risk_base(
    dim_project_priority: pd.DataFrame,
    fact_scenario_capacity_weekly: pd.DataFrame,
    fact_scenario_sourcing_weekly: pd.DataFrame,
    fact_scenario_logistics_weekly: pd.DataFrame,
) -> pd.DataFrame:
    """Build base integrated risk without disruption-adjusted outputs."""

    base = fact_scenario_logistics_weekly.copy()
    priority = dim_project_priority[["project_id", "priority_score", "probability_score"]].copy()
    capacity = _aggregate_capacity(fact_scenario_capacity_weekly)
    sourcing = _aggregate_sourcing(fact_scenario_sourcing_weekly)

    out = base.merge(priority, on="project_id", how="left")
    out = out.merge(capacity, on=["scenario", "plant", "week"], how="left")
    out = out.merge(sourcing, on=["scenario", "plant", "week"], how="left")

    out["priority_score"] = out["priority_score"].fillna(0.0).clip(0.0, 1.0)
    out["probability_score"] = out["probability_score"].fillna(0.5).clip(0.0, 1.0)
    out["capacity_risk_score"] = out["capacity_risk_score"].fillna(0.0).clip(0.0, 1.0)
    out["sourcing_risk_score"] = out["sourcing_risk_score"].fillna(0.0).clip(0.0, 1.0)
    out["logistics_risk_score"] = pd.to_numeric(out["logistics_risk_score"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out["lead_time_risk_score"] = out["lead_time_risk_score"].fillna(0.0).clip(0.0, 1.0)
    out["disruption_risk_score_placeholder"] = 0.0
    out["data_quality_penalty_placeholder"] = 0.0
    out["scenario_confidence"] = _scenario_confidence(out["scenario"], out["probability_score"])

    out["risk_score_base"] = (
        0.35 * out["capacity_risk_score"]
        + 0.30 * out["sourcing_risk_score"]
        + 0.25 * out["logistics_risk_score"]
        + 0.10 * out["lead_time_risk_score"]
    ).clip(0.0, 1.0)
    out["action_score_base"] = (
        out["priority_score"] * out["risk_score_base"] * out["scenario_confidence"]
    ).clip(0.0, 1.0)
    out["top_driver"] = _top_driver(out)
    out["explainability_note"] = _explainability_note(out.assign(top_driver=out["top_driver"]))

    cols = [
        "scenario",
        "project_id",
        "plant",
        "week",
        "priority_score",
        "capacity_risk_score",
        "sourcing_risk_score",
        "logistics_risk_score",
        "disruption_risk_score_placeholder",
        "lead_time_risk_score",
        "data_quality_penalty_placeholder",
        "risk_score_base",
        "action_score_base",
        "top_driver",
        "explainability_note",
        "scenario_confidence",
    ]
    return out[cols].drop_duplicates(["scenario", "project_id", "plant", "week"]).reset_index(drop=True)


def validate_fact_integrated_risk_base(df: pd.DataFrame) -> IntegratedRiskValidation:
    if df.empty:
        return IntegratedRiskValidation(0, 0, 0, 0)

    return IntegratedRiskValidation(
        row_count=int(len(df)),
        duplicate_key_count=int(df.duplicated(["scenario", "project_id", "plant", "week"]).sum()),
        placeholder_disruption_nonzero=int((df["disruption_risk_score_placeholder"] != 0).sum()),
        placeholder_quality_nonzero=int((df["data_quality_penalty_placeholder"] != 0).sum()),
    )
