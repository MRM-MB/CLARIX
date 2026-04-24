"""Wave 2 Scenario & Translation Engine for Luigi."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_SEED = 42
DEFAULT_TRIALS = 200


@dataclass(frozen=True)
class TranslationValidation:
    row_count: int
    duplicate_key_count: int
    unmapped_row_count: int
    scenario_count: int


def load_wave2_inputs(base_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load Luigi Wave 2 inputs from the processed project directory."""

    base = Path(base_dir)
    return {
        "fact_pipeline_monthly": pd.read_pickle(base / "fact_pipeline_monthly.pkl"),
        "dim_project_priority": pd.read_pickle(base / "dim_project_priority.pkl"),
        "bridge_material_tool_wc": pd.read_pickle(base / "bridge_material_tool_wc.pkl"),
        "bridge_month_week_calendar": pd.read_pickle(base / "bridge_month_week_calendar.pkl"),
    }


def _calendar_for_allocation(calendar: pd.DataFrame) -> pd.DataFrame:
    """Normalize the month-week bridge to a single reusable allocation table."""

    if calendar.empty:
        return pd.DataFrame(
            columns=["period_date", "week", "week_start", "month_week_weight", "calendar_source"]
        )

    cal = calendar.copy()
    cal = cal.sort_values(["period_date", "plant", "week_start", "week"])
    cal = cal[cal["plant"].isin(["ALL"]) | cal["plant"].isna() | (cal["plant"] == "")].copy()
    if cal.empty:
        cal = calendar.copy()
        cal = cal.sort_values(["period_date", "plant", "week_start", "week"])
        cal = cal.drop_duplicates(["period_date", "week"], keep="first")

    cal["week"] = (
        cal["year"].astype(int).astype(str)
        + "-W"
        + cal["week"].astype(int).astype(str).str.zfill(2)
    )
    keep = ["period_date", "week", "week_start", "month_week_weight", "calendar_source"]
    return cal[keep].drop_duplicates(["period_date", "week"]).reset_index(drop=True)


def _monte_carlo_quantity(probability: pd.Series, raw_qty: pd.Series, *, seed: int, n_trials: int) -> tuple[pd.Series, pd.Series]:
    """Seeded Monte Carlo light translation at row level."""

    if len(probability) == 0:
        empty = pd.Series(dtype=float)
        return empty, empty

    rng = np.random.default_rng(seed)
    prob = probability.to_numpy(dtype=float)
    qty = raw_qty.to_numpy(dtype=float)
    draws = (rng.random((n_trials, len(prob))) < prob).astype(np.float32)
    mean_qty = draws.mean(axis=0) * qty
    std_error = np.sqrt(np.clip(prob * (1.0 - prob), 0.0, 1.0) / float(n_trials))
    confidence = 1.0 - np.clip(4.0 * std_error, 0.0, 1.0)
    return (
        pd.Series(mean_qty, index=probability.index, dtype=float),
        pd.Series(confidence, index=probability.index, dtype=float),
    )


def _scenario_frame(base: pd.DataFrame, *, seed: int, n_trials: int) -> pd.DataFrame:
    """Expand monthly translated rows into required scenario families."""

    monte_qty, monte_conf = _monte_carlo_quantity(
        base["probability"], base["raw_weekly_qty"], seed=seed, n_trials=n_trials
    )
    scenarios = [
        (
            "all_in",
            pd.Series(1.0, index=base.index, dtype=float),
            base["raw_weekly_qty"],
        ),
        (
            "expected_value",
            base["probability"].clip(0.0, 1.0),
            base["expected_weekly_qty"],
        ),
        (
            "high_confidence",
            pd.Series(
                np.where(base["probability"] >= 0.70, 0.90, 0.60),
                index=base.index,
                dtype=float,
            ),
            pd.Series(
                np.where(base["probability"] >= 0.70, base["raw_weekly_qty"], 0.0),
                index=base.index,
                dtype=float,
            ),
        ),
        (
            "monte_carlo_light",
            monte_conf.clip(0.0, 1.0),
            monte_qty,
        ),
    ]

    parts = []
    keep = [
        "project_id",
        "plant",
        "material",
        "week",
        "week_start",
        "raw_weekly_qty",
        "probability",
        "tool_no",
        "work_center",
        "cycle_time",
        "priority_score",
        "mapping_status",
        "reason_code",
        "reason_code_detail",
        "calendar_source",
        "period_date",
    ]
    for scenario_name, confidence, scenario_qty in scenarios:
        tmp = base[keep].copy()
        tmp["scenario"] = scenario_name
        tmp["scenario_confidence"] = pd.Series(confidence, index=tmp.index, dtype=float)
        tmp["expected_weekly_qty"] = pd.Series(scenario_qty, index=tmp.index, dtype=float)
        parts.append(tmp)
    out = pd.concat(parts, ignore_index=True)
    out = (
        out.groupby(
            [
                "scenario",
                "project_id",
                "plant",
                "material",
                "week",
                "tool_no",
                "work_center",
                "cycle_time",
                "priority_score",
                "scenario_confidence",
                "mapping_status",
                "reason_code",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            raw_weekly_qty=("raw_weekly_qty", "sum"),
            expected_weekly_qty=("expected_weekly_qty", "sum"),
            reason_code_detail=("reason_code_detail", lambda s: "|".join(sorted({str(v) for v in s if pd.notna(v) and str(v)}))),
            week_start=("week_start", "min"),
            period_date=("period_date", "min"),
            calendar_source=("calendar_source", lambda s: "|".join(sorted({str(v) for v in s if pd.notna(v) and str(v)}))),
            probability=("probability", "max"),
        )
    )
    ordered = [
        "scenario",
        "project_id",
        "plant",
        "material",
        "week",
        "raw_weekly_qty",
        "expected_weekly_qty",
        "tool_no",
        "work_center",
        "cycle_time",
        "priority_score",
        "scenario_confidence",
        "mapping_status",
        "reason_code",
        "reason_code_detail",
        "week_start",
        "period_date",
        "calendar_source",
        "probability",
    ]
    return out[ordered].sort_values(["scenario", "project_id", "plant", "material", "week"]).reset_index(drop=True)


def build_fact_translated_project_demand_weekly(
    fact_pipeline_monthly: pd.DataFrame,
    dim_project_priority: pd.DataFrame,
    bridge_material_tool_wc: pd.DataFrame,
    bridge_month_week_calendar: pd.DataFrame,
    *,
    seed: int = DEFAULT_SEED,
    n_trials: int = DEFAULT_TRIALS,
) -> pd.DataFrame:
    """Translate monthly demand into weekly manufacturable demand across scenarios."""

    if fact_pipeline_monthly.empty:
        return pd.DataFrame(
            columns=[
                "scenario",
                "project_id",
                "plant",
                "material",
                "week",
                "raw_weekly_qty",
                "expected_weekly_qty",
                "tool_no",
                "work_center",
                "cycle_time",
                "priority_score",
                "scenario_confidence",
                "mapping_status",
                "reason_code",
            ]
        )

    fact = fact_pipeline_monthly.copy()
    fact = fact[fact["raw_qty"] > 0].copy()
    fact["period_date"] = pd.to_datetime(fact["period_date"], errors="coerce")

    cal = _calendar_for_allocation(bridge_month_week_calendar)
    monthly = fact.merge(cal, on="period_date", how="left")
    monthly["raw_weekly_qty"] = monthly["raw_qty"] * monthly["month_week_weight"].fillna(0.0)
    monthly["expected_weekly_qty"] = monthly["expected_qty"] * monthly["month_week_weight"].fillna(0.0)

    prio = dim_project_priority[["project_id", "priority_score"]].rename(
        columns={"priority_score": "priority_score_dim"}
    )
    monthly = monthly.merge(prio, on="project_id", how="left")
    monthly["priority_score"] = monthly["priority_score_dim"].fillna(monthly["priority_score"]).fillna(0.0)
    monthly = monthly.drop(columns=["priority_score_dim"], errors="ignore")

    bridge = bridge_material_tool_wc.rename(
        columns={
            "tool": "tool_no",
            "cycle_time_min": "cycle_time",
            "material_status": "material_status_bridge",
        }
    ).copy()
    monthly = monthly.merge(
        bridge[["plant", "material", "tool_no", "work_center", "cycle_time", "material_status_bridge", "reason_code"]],
        on=["plant", "material"],
        how="left",
        suffixes=("", "_bridge"),
    )

    monthly["mapping_status"] = np.where(
        monthly["tool_no"].notna() & monthly["work_center"].notna() & monthly["cycle_time"].notna(),
        monthly["material_status_bridge"].fillna("MAPPED"),
        "UNMAPPED",
    )

    monthly["reason_code_detail"] = monthly["reason_code_detail"].fillna("")
    monthly["reason_code"] = np.where(
        monthly["mapping_status"] == "UNMAPPED",
        np.where(
            monthly["reason_code"].fillna("").eq("READY"),
            "MISSING_TOOL_WC_TRANSLATION",
            monthly["reason_code"],
        ),
        monthly["reason_code"].fillna("READY"),
    )
    monthly["reason_code_detail"] = np.where(
        monthly["mapping_status"] == "UNMAPPED",
        np.where(
            monthly["reason_code_detail"].astype(str).str.len() > 0,
            monthly["reason_code_detail"].astype(str) + "|MISSING_TOOL_WC_TRANSLATION",
            "MISSING_TOOL_WC_TRANSLATION",
        ),
        monthly["reason_code_detail"],
    )

    return _scenario_frame(monthly, seed=seed, n_trials=n_trials)


def validate_fact_translated_project_demand_weekly(df: pd.DataFrame) -> TranslationValidation:
    """Validate the Wave 2 translated weekly fact."""

    if df.empty:
        return TranslationValidation(0, 0, 0, 0)

    dupes = int(df.duplicated(["scenario", "project_id", "plant", "material", "week"]).sum())
    unmapped = int((df["mapping_status"] == "UNMAPPED").sum())
    return TranslationValidation(
        row_count=int(len(df)),
        duplicate_key_count=dupes,
        unmapped_row_count=unmapped,
        scenario_count=int(df["scenario"].nunique()),
    )
