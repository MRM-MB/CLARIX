"""Materialize Luigi Wave 3 outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.risk.integrated_risk_base import (
    build_fact_integrated_risk_base,
    load_wave3_inputs,
    validate_fact_integrated_risk_base,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "integrated_risk_base_report.md"


def _write_table(df: pd.DataFrame, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base_path.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base_path.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(base_path.with_suffix(".pkl"))


def _build_report(df: pd.DataFrame) -> str:
    val = validate_fact_integrated_risk_base(df)
    top = df["top_driver"].value_counts().to_dict() if not df.empty else {}
    by_scenario = df.groupby("scenario")["risk_score_base"].mean().round(4).to_dict() if not df.empty else {}
    lines = [
        "# Integrated Risk Base Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Inputs",
        "",
        "- `dim_project_priority`",
        "- `fact_scenario_capacity_weekly`",
        "- `fact_scenario_sourcing_weekly`",
        "- `fact_scenario_logistics_weekly`",
        "",
        "## Merge Logic",
        "",
        "- base grain comes from `fact_scenario_logistics_weekly` because it already carries `scenario x project_id x plant x week`.",
        "- capacity risk is aggregated to `scenario x plant x week` and joined onto project rows.",
        "- sourcing and lead-time risk are aggregated to `scenario x plant x week` and joined onto project rows.",
        "- `monte_carlo_light` uses `expected_value` capacity as explicit fallback because capacity Wave 2 did not materialize Monte Carlo rows.",
        "- disruption and QA penalties remain explicit zero-value placeholders for Wave 4.",
        "",
        "## Validation",
        "",
        f"- rows: `{val.row_count}`",
        f"- duplicate grain rows: `{val.duplicate_key_count}`",
        f"- non-zero disruption placeholders: `{val.placeholder_disruption_nonzero}`",
        f"- non-zero QA placeholders: `{val.placeholder_quality_nonzero}`",
        f"- top drivers: `{top}`",
        f"- average risk by scenario: `{by_scenario}`",
    ]
    return "\n".join(lines) + "\n"


def materialize_wave3_luigi() -> pd.DataFrame:
    inputs = load_wave3_inputs(PROCESSED_DIR)
    fact = build_fact_integrated_risk_base(**inputs)
    _write_table(fact, PROCESSED_DIR / "fact_integrated_risk_base")
    REPORT_PATH.write_text(_build_report(fact), encoding="utf-8")
    return fact


if __name__ == "__main__":
    materialize_wave3_luigi()
