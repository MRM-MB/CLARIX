"""Wave 4 Luigi: final integrated risk engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


FINAL_DRIVER_ORDER = [
    "capacity_risk_score",
    "sourcing_risk_score",
    "logistics_risk_score",
    "disruption_risk_score",
    "lead_time_risk_score",
    "data_quality_penalty",
]


@dataclass(frozen=True)
class FinalIntegratedRiskValidation:
    row_count: int
    duplicate_key_count: int
    bounded_risk_violations: int
    bounded_action_violations: int
    disruption_nonzero_rows: int
    qa_nonzero_rows: int


def load_wave4_inputs(base_dir: str | Path) -> dict[str, pd.DataFrame]:
    base = Path(base_dir)
    return {
        "fact_integrated_risk_base": pd.read_csv(base / "fact_integrated_risk_base.csv"),
        "fact_scenario_resilience_impact": pd.read_csv(base / "fact_scenario_resilience_impact.csv"),
        "fact_data_quality_flags": pd.read_csv(base / "fact_data_quality_flags.csv"),
    }


def _aggregate_disruption_impacts(impact: pd.DataFrame) -> pd.DataFrame:
    if impact.empty:
        return pd.DataFrame(
            columns=[
                "scenario",
                "project_id",
                "plant",
                "week",
                "delta_capacity_risk",
                "delta_sourcing_risk",
                "delta_logistics_risk",
                "disruption_risk_score",
                "dominant_disruption_branch",
                "disruption_note",
            ]
        )

    tmp = impact.rename(columns={"project_id_if_available": "project_id"}).copy()
    key_cols = ["scenario", "project_id", "plant", "week"]
    tmp["branch_rank"] = tmp.groupby(key_cols)["disruption_risk_score"].rank(
        method="first",
        ascending=False,
    )

    summary = (
        tmp.groupby(key_cols, as_index=False)
        .agg(
            delta_capacity_risk=("delta_capacity_risk", "sum"),
            delta_sourcing_risk=("delta_sourcing_risk", "sum"),
            delta_logistics_risk=("delta_logistics_risk", "sum"),
            disruption_risk_score=("disruption_risk_score", "sum"),
            disruption_branch_count=("affected_branch", "nunique"),
        )
    )
    for col in [
        "delta_capacity_risk",
        "delta_sourcing_risk",
        "delta_logistics_risk",
        "disruption_risk_score",
    ]:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").fillna(0.0).clip(0.0, 1.0)

    dominant = tmp[tmp["branch_rank"] == 1][key_cols + ["affected_branch", "explanation_note"]].copy()
    dominant = dominant.rename(
        columns={
            "affected_branch": "dominant_disruption_branch",
            "explanation_note": "disruption_note",
        }
    )
    return summary.merge(dominant, on=key_cols, how="left")


def _aggregate_qa_penalties(flags: pd.DataFrame) -> pd.DataFrame:
    if flags.empty:
        return pd.DataFrame(
            columns=[
                "scenario",
                "project_id",
                "plant",
                "week",
                "data_quality_penalty",
                "qa_issue_summary",
            ]
        )

    work = flags.copy()
    key_parts = work["entity_key"].astype(str).str.split("|", expand=True)
    work["key_1"] = key_parts[0]
    work["key_2"] = key_parts[1]
    work["key_3"] = key_parts[2]
    work["key_4"] = key_parts[3] if key_parts.shape[1] > 3 else None

    exact = work[work["entity_type"].isin(["risk_row", "logistics_row"])].copy()
    exact["scenario"] = exact["key_1"]
    exact["project_id"] = exact["key_2"]
    exact["plant"] = exact["key_3"]
    exact["week"] = exact["key_4"]
    exact_agg = (
        exact.groupby(["scenario", "project_id", "plant", "week"], as_index=False)
        .agg(
            exact_penalty=("penalty_score", "sum"),
            exact_issue_types=("issue_type", lambda s: ",".join(sorted(set(map(str, s))))),
        )
    )

    sourcing = work[work["entity_type"] == "sourcing_row"].copy()
    sourcing["scenario"] = sourcing["key_1"]
    sourcing["plant"] = sourcing["key_2"]
    sourcing["week"] = sourcing["key_4"]
    sourcing_agg = (
        sourcing.groupby(["scenario", "plant", "week"], as_index=False)
        .agg(
            sourcing_penalty=("penalty_score", "max"),
            sourcing_issue_types=("issue_type", lambda s: ",".join(sorted(set(map(str, s))))),
        )
    )

    bottleneck = work[work["entity_type"] == "bottleneck_row"].copy()
    bottleneck["scenario"] = bottleneck["key_1"]
    bottleneck["plant"] = bottleneck["key_2"]
    bottleneck_agg = (
        bottleneck.groupby(["scenario", "plant"], as_index=False)
        .agg(
            bottleneck_penalty=("penalty_score", "max"),
            bottleneck_issue_types=("issue_type", lambda s: ",".join(sorted(set(map(str, s))))),
        )
    )

    out = exact_agg.merge(sourcing_agg, on=["scenario", "plant", "week"], how="left")
    out = out.merge(bottleneck_agg, on=["scenario", "plant"], how="left")
    for col in ["exact_penalty", "sourcing_penalty", "bottleneck_penalty"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    for col in ["exact_issue_types", "sourcing_issue_types", "bottleneck_issue_types"]:
        out[col] = out[col].fillna("")

    out["data_quality_penalty"] = (
        out["exact_penalty"] + out["sourcing_penalty"] + out["bottleneck_penalty"]
    ).clip(0.0, 1.0)

    summaries = []
    for row in out.itertuples(index=False):
        parts = []
        if row.exact_issue_types:
            parts.append(f"row={row.exact_issue_types}")
        if row.sourcing_issue_types:
            parts.append(f"sourcing={row.sourcing_issue_types}")
        if row.bottleneck_issue_types:
            parts.append(f"bottleneck={row.bottleneck_issue_types}")
        summaries.append("; ".join(parts))
    out["qa_issue_summary"] = summaries

    return out[
        [
            "scenario",
            "project_id",
            "plant",
            "week",
            "data_quality_penalty",
            "qa_issue_summary",
        ]
    ]


def _top_driver(df: pd.DataFrame) -> pd.Series:
    def pick(row: pd.Series) -> str:
        best = max(FINAL_DRIVER_ORDER, key=lambda col: float(row[col]))
        return best.replace("_score", "")

    return df.apply(pick, axis=1)


def _build_explainability_note(df: pd.DataFrame) -> pd.Series:
    notes = []
    for row in df.itertuples(index=False):
        parts = [
            f"priority={row.priority_score:.3f}",
            f"capacity={row.capacity_risk_score:.3f}",
            f"sourcing={row.sourcing_risk_score:.3f}",
            f"logistics={row.logistics_risk_score:.3f}",
            f"disruption={row.disruption_risk_score:.3f}",
            f"lead_time={row.lead_time_risk_score:.3f}",
            f"qa_penalty={row.data_quality_penalty:.3f}",
            f"risk={row.risk_score:.3f}",
            f"action={row.action_score:.3f}",
            f"top_driver={row.top_driver}",
        ]
        if row.dominant_disruption_branch:
            parts.append(f"disruption_branch={row.dominant_disruption_branch}")
        if row.qa_issue_summary:
            parts.append(f"qa={row.qa_issue_summary}")
        notes.append("; ".join(parts))
    return pd.Series(notes, index=df.index, dtype="object")


def build_fact_integrated_risk(
    fact_integrated_risk_base: pd.DataFrame,
    fact_scenario_resilience_impact: pd.DataFrame,
    fact_data_quality_flags: pd.DataFrame,
) -> pd.DataFrame:
    base = fact_integrated_risk_base.copy()
    disruption = _aggregate_disruption_impacts(fact_scenario_resilience_impact)
    qa = _aggregate_qa_penalties(fact_data_quality_flags)
    key_cols = ["scenario", "project_id", "plant", "week"]

    out = base.merge(disruption, on=key_cols, how="left")
    out = out.merge(qa, on=key_cols, how="left")

    numeric_fill = {
        "delta_capacity_risk": 0.0,
        "delta_sourcing_risk": 0.0,
        "delta_logistics_risk": 0.0,
        "disruption_risk_score": 0.0,
        "data_quality_penalty": 0.0,
    }
    for col, default in numeric_fill.items():
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(default)

    out["capacity_risk_score"] = (
        pd.to_numeric(out["capacity_risk_score"], errors="coerce").fillna(0.0)
        + out["delta_capacity_risk"]
    ).clip(0.0, 1.0)
    out["sourcing_risk_score"] = (
        pd.to_numeric(out["sourcing_risk_score"], errors="coerce").fillna(0.0)
        + out["delta_sourcing_risk"]
    ).clip(0.0, 1.0)
    out["logistics_risk_score"] = (
        pd.to_numeric(out["logistics_risk_score"], errors="coerce").fillna(0.0)
        + out["delta_logistics_risk"]
    ).clip(0.0, 1.0)
    out["disruption_risk_score"] = out["disruption_risk_score"].clip(0.0, 1.0)
    out["lead_time_risk_score"] = pd.to_numeric(out["lead_time_risk_score"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out["priority_score"] = pd.to_numeric(out["priority_score"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out["scenario_confidence"] = pd.to_numeric(out["scenario_confidence"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out["data_quality_penalty"] = out["data_quality_penalty"].clip(0.0, 1.0)

    out["risk_score"] = (
        0.30 * out["capacity_risk_score"]
        + 0.25 * out["sourcing_risk_score"]
        + 0.20 * out["logistics_risk_score"]
        + 0.10 * out["disruption_risk_score"]
        + 0.10 * out["lead_time_risk_score"]
        + 0.05 * out["data_quality_penalty"]
    ).clip(0.0, 1.0)
    out["action_score"] = (
        out["priority_score"] * out["risk_score"] * out["scenario_confidence"]
    ).clip(0.0, 1.0)
    out["top_driver"] = _top_driver(out)

    string_fill = {
        "dominant_disruption_branch": "",
        "disruption_note": "",
        "qa_issue_summary": "",
    }
    for col, default in string_fill.items():
        out[col] = out[col].fillna(default)
    out["explainability_note"] = _build_explainability_note(out)

    cols = [
        "scenario",
        "project_id",
        "plant",
        "week",
        "priority_score",
        "capacity_risk_score",
        "sourcing_risk_score",
        "logistics_risk_score",
        "disruption_risk_score",
        "lead_time_risk_score",
        "data_quality_penalty",
        "risk_score",
        "action_score",
        "top_driver",
        "explainability_note",
        "scenario_confidence",
    ]
    return out[cols].drop_duplicates(key_cols).reset_index(drop=True)


def validate_fact_integrated_risk(df: pd.DataFrame) -> FinalIntegratedRiskValidation:
    if df.empty:
        return FinalIntegratedRiskValidation(0, 0, 0, 0, 0, 0)

    return FinalIntegratedRiskValidation(
        row_count=int(len(df)),
        duplicate_key_count=int(df.duplicated(["scenario", "project_id", "plant", "week"]).sum()),
        bounded_risk_violations=int(((df["risk_score"] < 0) | (df["risk_score"] > 1)).sum()),
        bounded_action_violations=int(((df["action_score"] < 0) | (df["action_score"] > 1)).sum()),
        disruption_nonzero_rows=int((df["disruption_risk_score"] > 0).sum()),
        qa_nonzero_rows=int((df["data_quality_penalty"] > 0).sum()),
    )
