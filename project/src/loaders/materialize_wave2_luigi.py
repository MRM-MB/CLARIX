"""Materialize Luigi Wave 2 outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.scenarios.weekly_translation import (
    DEFAULT_SEED,
    DEFAULT_TRIALS,
    build_fact_translated_project_demand_weekly,
    load_wave2_inputs,
    validate_fact_translated_project_demand_weekly,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "scenario_generation_report.md"


def _write_table(df: pd.DataFrame, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base_path.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base_path.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(base_path.with_suffix(".pkl"))


def _build_report(df: pd.DataFrame) -> str:
    validation = validate_fact_translated_project_demand_weekly(df)
    scenario_summary = df.groupby("scenario")["expected_weekly_qty"].sum().round(2).to_dict() if not df.empty else {}
    unmapped_summary = df[df["mapping_status"] == "UNMAPPED"]["reason_code"].value_counts().to_dict() if not df.empty else {}
    lines = [
        "# Scenario Generation Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Inputs Used",
        "",
        "- `fact_pipeline_monthly`",
        "- `dim_project_priority`",
        "- `bridge_material_tool_wc`",
        "- `bridge_month_week_calendar`",
        "",
        "## Scenario Logic",
        "",
        "- `all_in`: weekly raw demand allocated from monthly `raw_qty`; `scenario_confidence = 1.0`.",
        "- `expected_value`: weekly expected demand allocated from monthly `expected_qty`; `scenario_confidence = probability`.",
        "- `high_confidence`: uses raw weekly qty only for rows with `probability >= 0.70`; otherwise `expected_weekly_qty = 0`; confidence is `0.90` for included rows and `0.60` otherwise.",
        f"- `monte_carlo_light`: seeded Bernoulli simulation with `seed={DEFAULT_SEED}` and `n_trials={DEFAULT_TRIALS}`; weekly qty is monthly seeded mean allocation and confidence is derived from sampling error.",
        "",
        "## Validation",
        "",
        f"- rows: `{validation.row_count}`",
        f"- scenarios: `{validation.scenario_count}`",
        f"- duplicate `(scenario, project_id, plant, material, week)` keys: `{validation.duplicate_key_count}`",
        f"- unmapped rows retained: `{validation.unmapped_row_count}`",
        f"- demand by scenario: `{scenario_summary}`",
        f"- unmapped reason codes: `{unmapped_summary}`",
        "",
        "## Notes",
        "",
        "- Weekly allocation uses `bridge_month_week_calendar` and the month-level `month_week_weight`.",
        "- `week` is stored as `YYYY-Www` to avoid collisions across years while preserving the prompt’s single `week` column.",
        "- Unmapped rows are kept via left join to routing and flagged with `mapping_status = UNMAPPED`.",
    ]
    return "\n".join(lines) + "\n"


def materialize_wave2_luigi() -> pd.DataFrame:
    inputs = load_wave2_inputs(PROCESSED_DIR)
    fact = build_fact_translated_project_demand_weekly(**inputs)
    _write_table(fact, PROCESSED_DIR / "fact_translated_project_demand_weekly")
    REPORT_PATH.write_text(_build_report(fact), encoding="utf-8")
    return fact


if __name__ == "__main__":
    materialize_wave2_luigi()
