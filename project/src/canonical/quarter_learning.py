"""Wave 6 Luigi: rolling planning inputs and quarterly learning signals."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from clarix.engine import quarter_label


EXPECTED_VALUE_SCENARIO = "expected_value"
DEFER_DELAY_ACTIONS = {"wait", "reschedule", "reroute", "expedite_shipping"}
PRIORITY_WEIGHT = {
    "low": 0.80,
    "medium": 1.00,
    "high": 1.10,
    "critical": 1.20,
}


def load_wave6_inputs(base_dir: str | Path) -> dict[str, pd.DataFrame]:
    base = Path(base_dir)
    return {
        "fact_pipeline_quarterly": pd.read_csv(base / "fact_pipeline_quarterly.csv"),
        "fact_decision_history": pd.read_csv(base / "fact_decision_history.csv"),
        "dim_project_priority": pd.read_csv(base / "dim_project_priority.csv"),
        "fact_integrated_risk": pd.read_csv(base / "fact_integrated_risk.csv"),
    }


def _quarter_sort(quarter_id: pd.Series) -> pd.Series:
    year = quarter_id.astype(str).str.slice(0, 4).astype(int)
    quarter = quarter_id.astype(str).str.extract(r"Q(\d)").astype(int)[0]
    return year * 4 + quarter


def _project_quarter_scope_map(fact_pipeline_quarterly: pd.DataFrame) -> pd.DataFrame:
    return fact_pipeline_quarterly[["scope_id", "quarter_id", "project_id", "plant"]].drop_duplicates().reset_index(drop=True)


def _build_quarter_risk_summary(
    fact_pipeline_quarterly: pd.DataFrame,
    fact_integrated_risk: pd.DataFrame,
) -> pd.DataFrame:
    scoped = _project_quarter_scope_map(fact_pipeline_quarterly)
    risk = fact_integrated_risk[fact_integrated_risk["scenario"] == EXPECTED_VALUE_SCENARIO].copy()
    if risk.empty or scoped.empty:
        return pd.DataFrame(columns=["scope_id", "quarter_id", "project_id", "current_top_driver", "current_max_risk_score"])

    risk["quarter_id"] = risk["week"].map(
        lambda value: quarter_label(int(str(value).split("-W")[0]), int(str(value).split("-W")[1]))
    )
    plant_risk = (
        risk.groupby(["project_id", "plant", "quarter_id"], as_index=False)
        .agg(
            current_max_risk_score=("risk_score", "max"),
            current_top_driver=("top_driver", lambda s: s.value_counts().idxmax()),
        )
    )
    scoped_risk = scoped.merge(plant_risk, on=["project_id", "plant", "quarter_id"], how="left")
    scoped_risk = scoped_risk.sort_values(
        ["scope_id", "quarter_id", "project_id", "current_max_risk_score", "current_top_driver"],
        ascending=[True, True, True, False, True],
        na_position="last",
    )
    summary = scoped_risk.drop_duplicates(["scope_id", "quarter_id", "project_id"], keep="first").copy()
    return summary[["scope_id", "quarter_id", "project_id", "current_top_driver", "current_max_risk_score"]].reset_index(drop=True)


def build_fact_quarter_learning_signals(
    fact_pipeline_quarterly: pd.DataFrame,
    fact_decision_history: pd.DataFrame,
    dim_project_priority: pd.DataFrame,
    fact_integrated_risk: pd.DataFrame,
) -> pd.DataFrame:
    history = fact_decision_history.copy()
    if history.empty:
        return pd.DataFrame(
            columns=[
                "scope_id",
                "quarter_id",
                "project_id",
                "repeated_risk_flag",
                "repeated_action_flag",
                "repeated_delay_flag",
                "confidence_adjustment_signal",
                "explanation_note",
            ]
        )

    risk_summary = _build_quarter_risk_summary(fact_pipeline_quarterly, fact_integrated_risk)
    priority = dim_project_priority[["project_id", "priority_band", "probability_score"]].drop_duplicates("project_id")
    out = history.merge(risk_summary, on=["scope_id", "quarter_id", "project_id"], how="left")
    out = out.merge(priority, on="project_id", how="left")

    out["quarter_sort"] = _quarter_sort(out["quarter_id"])
    out = out.sort_values(["scope_id", "project_id", "quarter_sort"]).reset_index(drop=True)
    grouped = out.groupby(["scope_id", "project_id"], group_keys=False)
    out["prior_current_top_driver"] = grouped["current_top_driver"].shift(1)
    out["prior_previous_action_type"] = grouped["previous_action_type"].shift(1)

    out["repeated_risk_flag"] = (
        out["current_top_driver"].notna()
        & out["prior_current_top_driver"].notna()
        & (out["current_top_driver"] == out["prior_current_top_driver"])
    )
    out["repeated_action_flag"] = (
        out["previous_action_type"].notna()
        & out["prior_previous_action_type"].notna()
        & (out["previous_action_type"] == out["prior_previous_action_type"])
    )
    out["repeated_delay_flag"] = (
        out["carry_over_flag"].astype(bool)
        & out["previous_action_type"].isin(DEFER_DELAY_ACTIONS)
    )

    out["confidence_adjustment_signal"] = 0.0
    out.loc[out["repeated_risk_flag"], "confidence_adjustment_signal"] -= 0.10
    out.loc[out["repeated_action_flag"], "confidence_adjustment_signal"] -= 0.05
    out.loc[out["repeated_delay_flag"], "confidence_adjustment_signal"] -= 0.05
    out.loc[out["previous_confidence"].fillna("") == "low", "confidence_adjustment_signal"] -= 0.05
    out["confidence_adjustment_signal"] = out["confidence_adjustment_signal"].clip(-0.25, 0.0)

    notes = []
    for row in out.itertuples(index=False):
        parts = [
            f"repeat_risk={bool(row.repeated_risk_flag)}",
            f"repeat_action={bool(row.repeated_action_flag)}",
            f"repeat_delay={bool(row.repeated_delay_flag)}",
            f"confidence_signal={row.confidence_adjustment_signal:.2f}",
            f"base_probability_score={float(row.probability_score) if pd.notna(row.probability_score) else 0.0:.2f}",
        ]
        if pd.notna(row.current_top_driver):
            parts.append(f"current_top_driver={row.current_top_driver}")
        if pd.notna(row.previous_action_type):
            parts.append(f"previous_action={row.previous_action_type}")
        parts.append("learning_mode=deterministic_rollforward_signal")
        notes.append("; ".join(parts))
    out["explanation_note"] = notes

    cols = [
        "scope_id",
        "quarter_id",
        "project_id",
        "repeated_risk_flag",
        "repeated_action_flag",
        "repeated_delay_flag",
        "confidence_adjustment_signal",
        "explanation_note",
    ]
    return out[cols].drop_duplicates(["scope_id", "quarter_id", "project_id"]).reset_index(drop=True)


def build_fact_quarter_rollforward_inputs(
    fact_decision_history: pd.DataFrame,
    dim_project_priority: pd.DataFrame,
    fact_quarter_learning_signals: pd.DataFrame,
) -> pd.DataFrame:
    history = fact_decision_history.copy()
    if history.empty:
        return pd.DataFrame(
            columns=[
                "scope_id",
                "from_quarter",
                "to_quarter",
                "project_id",
                "carry_over_probability_adjustment",
                "carry_over_priority_adjustment",
                "unresolved_action_penalty",
                "deferred_project_flag",
                "rollforward_note",
            ]
        )

    priority = dim_project_priority[["project_id", "priority_band", "priority_score", "probability_score"]].drop_duplicates("project_id")
    out = history.merge(
        fact_quarter_learning_signals,
        on=["scope_id", "quarter_id", "project_id"],
        how="left",
    ).merge(priority, on="project_id", how="left")

    out["quarter_sort"] = _quarter_sort(out["quarter_id"])
    out = out.sort_values(["scope_id", "project_id", "quarter_sort"]).reset_index(drop=True)
    grouped = out.groupby(["scope_id", "project_id"], group_keys=False)
    out["from_quarter"] = grouped["quarter_id"].shift(1)
    out["from_quarter_sort"] = grouped["quarter_sort"].shift(1)
    out["is_consecutive"] = out["from_quarter"].notna() & ((out["quarter_sort"] - out["from_quarter_sort"]) == 1)
    out = out[out["is_consecutive"]].copy()

    out["unresolved_action_penalty"] = (
        ((out["action_outcome_status"] == "pending_outcome_synth") & out["carry_over_flag"].astype(bool)).astype(float) * 0.15
    )
    out["deferred_project_flag"] = out["previous_action_type"].isin(["wait", "reschedule"])
    out["carry_over_probability_adjustment"] = pd.to_numeric(
        out["confidence_adjustment_signal"], errors="coerce"
    ).fillna(0.0).clip(-0.25, 0.0)

    priority_weight = out["priority_band"].map(PRIORITY_WEIGHT).fillna(1.0)
    out["carry_over_priority_adjustment"] = (
        (
            out["repeated_risk_flag"].astype(float) * 0.10
            + out["repeated_action_flag"].astype(float) * 0.07
            + out["unresolved_action_penalty"]
            + out["deferred_project_flag"].astype(float) * 0.05
        ) * priority_weight
    ).clip(0.0, 0.30)

    notes = []
    for row in out.itertuples(index=False):
        parts = [
            f"from={row.from_quarter}",
            f"to={row.quarter_id}",
            f"probability_adjustment_signal={row.carry_over_probability_adjustment:.2f}",
            f"priority_adjustment_signal={row.carry_over_priority_adjustment:.2f}",
            f"unresolved_penalty={row.unresolved_action_penalty:.2f}",
            f"deferred_project={bool(row.deferred_project_flag)}",
            "base_probability_unchanged=true",
        ]
        if pd.notna(row.previous_action_type):
            parts.append(f"previous_action={row.previous_action_type}")
        if pd.notna(row.priority_band):
            parts.append(f"priority_band={row.priority_band}")
        notes.append("; ".join(parts))
    out["rollforward_note"] = notes

    result = out.rename(columns={"quarter_id": "to_quarter"})[
        [
            "scope_id",
            "from_quarter",
            "to_quarter",
            "project_id",
            "carry_over_probability_adjustment",
            "carry_over_priority_adjustment",
            "unresolved_action_penalty",
            "deferred_project_flag",
            "rollforward_note",
        ]
    ]
    return result.drop_duplicates(["scope_id", "from_quarter", "to_quarter", "project_id"]).reset_index(drop=True)
