"""Materialize Luigi Wave 4 outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.risk.integrated_risk_final import (
    build_fact_integrated_risk,
    load_wave4_inputs,
    validate_fact_integrated_risk,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "integrated_risk_final_report.md"


def _write_table(df: pd.DataFrame, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base_path.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base_path.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(base_path.with_suffix(".pkl"))


def _build_report(df: pd.DataFrame) -> str:
    val = validate_fact_integrated_risk(df)
    top = df["top_driver"].value_counts().to_dict() if not df.empty else {}
    by_scenario = df.groupby("scenario")["risk_score"].mean().round(4).to_dict() if not df.empty else {}
    top20 = (
        df.sort_values("action_score", ascending=False)
        .head(20)[["scenario", "project_id", "plant", "week", "risk_score", "action_score", "top_driver"]]
        .to_string(index=False)
        if not df.empty
        else ""
    )
    lines = [
        "# Integrated Risk Final Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Inputs",
        "",
        "- `fact_integrated_risk_base`",
        "- `fact_scenario_resilience_impact`",
        "- `fact_data_quality_flags`",
        "",
        "## Merge Logic",
        "",
        "- disruption impacts are aggregated at `scenario x project_id x plant x week`, summed per row, and clipped to preserve bounded scores.",
        "- the highest-impact disruption branch is retained only in explainability text so the final table stays planner-ready at the declared grain.",
        "- exact QA flags (`risk_row`, `logistics_row`) are summed at row grain; multi-grain sourcing and bottleneck QA flags are collapsed with max-penalty adapters before joining to project rows.",
        "- final `risk_score` and `action_score` follow the Wave 4 contract formulas exactly.",
        "",
        "## Validation",
        "",
        f"- rows: `{val.row_count}`",
        f"- duplicate grain rows: `{val.duplicate_key_count}`",
        f"- bounded risk violations: `{val.bounded_risk_violations}`",
        f"- bounded action violations: `{val.bounded_action_violations}`",
        f"- rows with disruption effect: `{val.disruption_nonzero_rows}`",
        f"- rows with QA penalty: `{val.qa_nonzero_rows}`",
        f"- top drivers: `{top}`",
        f"- average risk by scenario: `{by_scenario}`",
        "",
        "## Top 20 Action Rows",
        "",
        top20,
        "",
        "## Notes",
        "",
        "- `qa_guardrails_report.md` suggests subtracting penalties from `action_score_base`, but Wave 4 uses the canonical contract formula: QA enters through `data_quality_penalty` inside `risk_score`.",
        "- all scores remain deterministic and bounded to `0..1`.",
    ]
    return "\n".join(lines) + "\n"


def materialize_wave4_luigi() -> pd.DataFrame:
    inputs = load_wave4_inputs(PROCESSED_DIR)
    fact = build_fact_integrated_risk(**inputs)
    _write_table(fact, PROCESSED_DIR / "fact_integrated_risk")
    REPORT_PATH.write_text(_build_report(fact), encoding="utf-8")
    return fact


if __name__ == "__main__":
    materialize_wave4_luigi()
