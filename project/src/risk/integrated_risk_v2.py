"""Wave 7 Luigi: scope-aware, quarter-aware, learning-aware integrated risk v2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from clarix.engine import quarter_label


DELIVERY_CAUTION_MAP = {
    "low": 0.05,
    "medium": 0.35,
    "high": 0.65,
}

V2_DRIVER_ORDER = [
    "capacity_risk_score",
    "sourcing_risk_score",
    "logistics_risk_score",
    "disruption_risk_score",
    "delivery_risk_score",
    "maintenance_risk_score",
    "quarter_learning_driver",
]


@dataclass(frozen=True)
class IntegratedRiskV2Validation:
    row_count: int
    duplicate_key_count: int
    bounded_risk_violations: int
    bounded_action_violations: int
    nonzero_delivery_rows: int
    nonzero_maintenance_rows: int
    nonzero_learning_rows: int


def load_wave7_inputs(base_dir: str | Path) -> dict[str, pd.DataFrame]:
    base = Path(base_dir)
    return {
        "fact_integrated_risk": pd.read_csv(base / "fact_integrated_risk.csv"),
        "fact_quarter_rollforward_inputs": pd.read_csv(base / "fact_quarter_rollforward_inputs.csv"),
        "fact_quarter_learning_signals": pd.read_csv(base / "fact_quarter_learning_signals.csv"),
        "fact_delivery_risk_rollforward": pd.read_csv(base / "fact_delivery_risk_rollforward.csv"),
        "fact_maintenance_impact_summary": pd.read_csv(base / "fact_maintenance_impact_summary.csv"),
    }


def _quarter_from_week(week: pd.Series) -> pd.Series:
    return week.map(
        lambda value: quarter_label(int(str(value).split("-W")[0]), int(str(value).split("-W")[1]))
    )


def _scoped_risk_base(
    fact_integrated_risk: pd.DataFrame,
    fact_quarter_learning_signals: pd.DataFrame,
) -> pd.DataFrame:
    risk = fact_integrated_risk.copy()
    risk["quarter_id"] = _quarter_from_week(risk["week"])
    scope_keys = fact_quarter_learning_signals[["scope_id", "quarter_id", "project_id"]].drop_duplicates()
    return scope_keys.merge(risk, on=["quarter_id", "project_id"], how="inner")


def _delivery_scores(fact_delivery_risk_rollforward: pd.DataFrame) -> pd.DataFrame:
    if fact_delivery_risk_rollforward.empty:
        return pd.DataFrame(columns=["quarter_id", "project_id", "delivery_risk_score", "delivery_note"])

    out = fact_delivery_risk_rollforward.copy()
    out["quarter_id"] = out["carry_forward_quarter_id"]
    out["delivery_risk_score"] = out["recommended_caution_level"].map(DELIVERY_CAUTION_MAP).fillna(0.0)
    out["delivery_note"] = (
        "delivery_caution="
        + out["recommended_caution_level"].astype(str)
        + "; prior_service_violation_risk="
        + out["prior_service_violation_risk"].round(3).astype(str)
    )
    return out[["quarter_id", "project_id", "delivery_risk_score", "delivery_note"]].drop_duplicates(
        ["quarter_id", "project_id"]
    )


def _maintenance_scores(fact_maintenance_impact_summary: pd.DataFrame) -> pd.DataFrame:
    if fact_maintenance_impact_summary.empty:
        return pd.DataFrame(columns=["plant", "maintenance_risk_score", "maintenance_note"])

    agg = (
        fact_maintenance_impact_summary.groupby("plant", as_index=False)
        .agg(
            maintenance_risk_score=("pct_capacity_lost_to_maintenance", "max"),
            maintenance_worst_severity=("impact_severity", lambda s: sorted(set(map(str, s)))[-1]),
        )
    )
    agg["maintenance_risk_score"] = pd.to_numeric(agg["maintenance_risk_score"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    agg["maintenance_note"] = (
        "maintenance_scope=mvp_3plant; worst_pct_capacity_lost="
        + agg["maintenance_risk_score"].round(3).astype(str)
        + "; impact_severity="
        + agg["maintenance_worst_severity"].astype(str)
    )
    return agg[["plant", "maintenance_risk_score", "maintenance_note"]]


def _quarter_learning_adjustment(
    scoped_risk: pd.DataFrame,
    fact_quarter_rollforward_inputs: pd.DataFrame,
    fact_quarter_learning_signals: pd.DataFrame,
) -> pd.DataFrame:
    roll = fact_quarter_rollforward_inputs.rename(columns={"to_quarter": "quarter_id"}).copy()
    learn = fact_quarter_learning_signals.copy()

    out = scoped_risk.merge(
        learn[["scope_id", "quarter_id", "project_id", "confidence_adjustment_signal"]],
        on=["scope_id", "quarter_id", "project_id"],
        how="left",
    )
    out = out.merge(
        roll[
            [
                "scope_id",
                "quarter_id",
                "project_id",
                "carry_over_priority_adjustment",
                "carry_over_probability_adjustment",
                "unresolved_action_penalty",
                "deferred_project_flag",
            ]
        ],
        on=["scope_id", "quarter_id", "project_id"],
        how="left",
    )
    out["carry_over_priority_adjustment"] = pd.to_numeric(out["carry_over_priority_adjustment"], errors="coerce").fillna(0.0)
    out["carry_over_probability_adjustment"] = pd.to_numeric(out["carry_over_probability_adjustment"], errors="coerce").fillna(0.0)
    out["confidence_adjustment_signal"] = pd.to_numeric(out["confidence_adjustment_signal"], errors="coerce").fillna(0.0)
    out["unresolved_action_penalty"] = pd.to_numeric(out["unresolved_action_penalty"], errors="coerce").fillna(0.0)
    out["deferred_project_flag"] = out["deferred_project_flag"].infer_objects(copy=False)
    out["deferred_project_flag"] = out["deferred_project_flag"].where(out["deferred_project_flag"].notna(), False).astype(bool)

    out["quarter_learning_penalty_or_boost"] = (
        out["carry_over_priority_adjustment"] + out["carry_over_probability_adjustment"]
    )
    no_rollforward = (out["carry_over_priority_adjustment"] == 0.0) & (out["carry_over_probability_adjustment"] == 0.0)
    out.loc[no_rollforward, "quarter_learning_penalty_or_boost"] = out.loc[no_rollforward, "confidence_adjustment_signal"]
    out["quarter_learning_penalty_or_boost"] = out["quarter_learning_penalty_or_boost"].clip(-0.25, 0.30)
    return out


def _top_driver(df: pd.DataFrame) -> pd.Series:
    def pick(row: pd.Series) -> str:
        best = max(V2_DRIVER_ORDER, key=lambda col: float(row[col]))
        if best == "quarter_learning_driver":
            return "quarter_learning"
        return best.replace("_score", "")

    return df.apply(pick, axis=1)


def _build_explainability(df: pd.DataFrame) -> pd.Series:
    notes = []
    for row in df.itertuples(index=False):
        parts = [
            f"scope={row.scope_id}",
            f"scenario={row.scenario}",
            f"quarter={row.quarter_id}",
            f"v1_risk={row.risk_score:.3f}",
            f"v2_risk={row.risk_score_v2:.3f}",
            f"capacity={row.capacity_risk_score:.3f}",
            f"sourcing={row.sourcing_risk_score:.3f}",
            f"logistics={row.logistics_risk_score:.3f}",
            f"disruption={row.disruption_risk_score:.3f}",
            f"delivery={row.delivery_risk_score:.3f}",
            f"maintenance={row.maintenance_risk_score:.3f}",
            f"quarter_learning={row.quarter_learning_penalty_or_boost:.3f}",
            f"top_driver={row.top_driver}",
        ]
        if row.delivery_note:
            parts.append(row.delivery_note)
        if row.maintenance_note:
            parts.append(row.maintenance_note)
        notes.append("; ".join(parts))
    return pd.Series(notes, index=df.index, dtype="object")


def build_fact_integrated_risk_v2(
    fact_integrated_risk: pd.DataFrame,
    fact_quarter_rollforward_inputs: pd.DataFrame,
    fact_quarter_learning_signals: pd.DataFrame,
    fact_delivery_risk_rollforward: pd.DataFrame,
    fact_maintenance_impact_summary: pd.DataFrame,
) -> pd.DataFrame:
    scoped = _scoped_risk_base(fact_integrated_risk, fact_quarter_learning_signals)
    if scoped.empty:
        return pd.DataFrame(
            columns=[
                "scope_id",
                "scenario",
                "quarter_id",
                "project_id",
                "plant",
                "week",
                "priority_score",
                "capacity_risk_score",
                "sourcing_risk_score",
                "logistics_risk_score",
                "disruption_risk_score",
                "delivery_risk_score",
                "maintenance_risk_score",
                "quarter_learning_penalty_or_boost",
                "risk_score_v2",
                "action_score_v2",
                "top_driver",
                "explainability_note",
            ]
        )

    scoped = _quarter_learning_adjustment(scoped, fact_quarter_rollforward_inputs, fact_quarter_learning_signals)
    delivery = _delivery_scores(fact_delivery_risk_rollforward)
    maintenance = _maintenance_scores(fact_maintenance_impact_summary)
    out = scoped.merge(delivery, on=["quarter_id", "project_id"], how="left")
    out = out.merge(maintenance, on="plant", how="left")

    out["delivery_risk_score"] = pd.to_numeric(out["delivery_risk_score"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out["maintenance_risk_score"] = pd.to_numeric(out["maintenance_risk_score"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out["quarter_learning_penalty_or_boost"] = pd.to_numeric(
        out["quarter_learning_penalty_or_boost"], errors="coerce"
    ).fillna(0.0).clip(-0.25, 0.30)
    out["quarter_learning_driver"] = out["quarter_learning_penalty_or_boost"].clip(lower=0.0)
    out["risk_score_v2"] = (
        out["risk_score"]
        + 0.10 * out["delivery_risk_score"]
        + 0.05 * out["maintenance_risk_score"]
        + 0.10 * out["quarter_learning_driver"]
    ).clip(0.0, 1.0)
    adjusted_priority = (
        pd.to_numeric(out["priority_score"], errors="coerce").fillna(0.0)
        + out["quarter_learning_penalty_or_boost"]
    ).clip(0.0, 1.0)
    out["action_score_v2"] = (adjusted_priority * out["risk_score_v2"]).clip(0.0, 1.0)

    out["delivery_note"] = out["delivery_note"].fillna("")
    out["maintenance_note"] = out["maintenance_note"].fillna("")
    out["top_driver"] = _top_driver(out)
    out["explainability_note"] = _build_explainability(out)

    cols = [
        "scope_id",
        "scenario",
        "quarter_id",
        "project_id",
        "plant",
        "week",
        "priority_score",
        "capacity_risk_score",
        "sourcing_risk_score",
        "logistics_risk_score",
        "disruption_risk_score",
        "delivery_risk_score",
        "maintenance_risk_score",
        "quarter_learning_penalty_or_boost",
        "risk_score_v2",
        "action_score_v2",
        "top_driver",
        "explainability_note",
    ]
    return out[cols].drop_duplicates(["scope_id", "scenario", "quarter_id", "project_id", "plant", "week"]).reset_index(drop=True)


def validate_fact_integrated_risk_v2(df: pd.DataFrame) -> IntegratedRiskV2Validation:
    if df.empty:
        return IntegratedRiskV2Validation(0, 0, 0, 0, 0, 0, 0)

    return IntegratedRiskV2Validation(
        row_count=int(len(df)),
        duplicate_key_count=int(df.duplicated(["scope_id", "scenario", "quarter_id", "project_id", "plant", "week"]).sum()),
        bounded_risk_violations=int(((df["risk_score_v2"] < 0) | (df["risk_score_v2"] > 1)).sum()),
        bounded_action_violations=int(((df["action_score_v2"] < 0) | (df["action_score_v2"] > 1)).sum()),
        nonzero_delivery_rows=int((df["delivery_risk_score"] > 0).sum()),
        nonzero_maintenance_rows=int((df["maintenance_risk_score"] > 0).sum()),
        nonzero_learning_rows=int((df["quarter_learning_penalty_or_boost"] != 0).sum()),
    )
