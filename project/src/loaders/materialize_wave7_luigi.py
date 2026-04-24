"""Materialize Luigi Wave 7 outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.risk.integrated_risk_v2 import (
    build_fact_integrated_risk_v2,
    load_wave7_inputs,
    validate_fact_integrated_risk_v2,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "integrated_risk_v2_report.md"


def _write_table(df: pd.DataFrame, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base_path.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base_path.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(base_path.with_suffix(".pkl"))


def _build_report(df: pd.DataFrame, v1: pd.DataFrame) -> str:
    val = validate_fact_integrated_risk_v2(df)
    top = df["top_driver"].value_counts().to_dict() if not df.empty else {}
    compare = {}
    mean_abs_diff = 0.0
    if not df.empty:
        merged = df.merge(
            v1[["scenario", "project_id", "plant", "week", "risk_score", "action_score"]],
            on=["scenario", "project_id", "plant", "week"],
            how="left",
        )
        compare = {
            "v1_mean_risk": round(float(merged["risk_score"].mean()), 4),
            "v2_mean_risk": round(float(merged["risk_score_v2"].mean()), 4),
            "v1_mean_action": round(float(merged["action_score"].mean()), 4),
            "v2_mean_action": round(float(merged["action_score_v2"].mean()), 4),
        }
        mean_abs_diff = float((merged["risk_score_v2"] - merged["risk_score"]).abs().mean())
    top20 = (
        df.sort_values("action_score_v2", ascending=False)
        .head(20)[["scope_id", "scenario", "quarter_id", "project_id", "plant", "risk_score_v2", "action_score_v2", "top_driver"]]
        .to_string(index=False)
        if not df.empty
        else ""
    )
    lines = [
        "# Integrated Risk V2 Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Inputs",
        "",
        "- `fact_integrated_risk`",
        "- `fact_quarter_rollforward_inputs`",
        "- `fact_quarter_learning_signals`",
        "- `fact_delivery_risk_rollforward`",
        "- `fact_maintenance_impact_summary` (supplemental Wave 6 Lara output used to satisfy maintenance-risk requirement)",
        "",
        "## What Changed From V1",
        "",
        "- v1 was project-week risk without explicit scope or quarter context.",
        "- v2 adds `scope_id` and `quarter_id` so the same project-week can be evaluated inside different business scopes.",
        "- v2 adds explicit `delivery_risk_score`, `maintenance_risk_score`, and signed `quarter_learning_penalty_or_boost`.",
        "- v2 keeps v1 risk drivers intact and uses additive adjustments so scores remain comparable to v1 rather than being fully re-based.",
        "",
        "## V2 Formula",
        "",
        "- `risk_score_v2 = risk_score_v1 + 0.10*delivery_risk_score + 0.05*maintenance_risk_score + 0.10*max(quarter_learning_penalty_or_boost, 0)`",
        "- `action_score_v2 = clip(priority_score + quarter_learning_penalty_or_boost, 0, 1) * risk_score_v2`",
        "- negative learning values reduce business weight in `action_score_v2` but do not hide the original v1 risk signal.",
        "",
        "## Validation",
        "",
        f"- rows: `{val.row_count}`",
        f"- duplicate grain rows: `{val.duplicate_key_count}`",
        f"- bounded risk violations: `{val.bounded_risk_violations}`",
        f"- bounded action violations: `{val.bounded_action_violations}`",
        f"- non-zero delivery rows: `{val.nonzero_delivery_rows}`",
        f"- non-zero maintenance rows: `{val.nonzero_maintenance_rows}`",
        f"- non-zero learning rows: `{val.nonzero_learning_rows}`",
        f"- mean absolute risk delta vs v1: `{mean_abs_diff:.4f}`",
        f"- score comparison summary: `{compare}`",
        f"- top drivers: `{top}`",
        "",
        "## Scope Note",
        "",
        "- Luigi business scopes are `global_reference` and `denmark_demo`.",
        "- delivery and maintenance feeds come from `mvp_3plant` assets built by other agents, so Wave 7 uses project-quarter delivery joins and plant-level maintenance joins as explicit adapters instead of pretending the scope models already match.",
        "",
        "## Top 20 V2 Rows",
        "",
        top20,
    ]
    return "\n".join(lines) + "\n"


def materialize_wave7_luigi() -> pd.DataFrame:
    inputs = load_wave7_inputs(PROCESSED_DIR)
    fact = build_fact_integrated_risk_v2(**inputs)
    _write_table(fact, PROCESSED_DIR / "fact_integrated_risk_v2")
    REPORT_PATH.write_text(_build_report(fact, inputs["fact_integrated_risk"]), encoding="utf-8")
    return fact


if __name__ == "__main__":
    materialize_wave7_luigi()
