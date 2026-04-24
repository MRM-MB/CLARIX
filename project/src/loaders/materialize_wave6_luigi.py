"""Materialize Luigi Wave 6 outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.canonical.quarter_learning import (
    build_fact_quarter_learning_signals,
    build_fact_quarter_rollforward_inputs,
    load_wave6_inputs,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "wave6_luigi_report.md"


def _write_table(df: pd.DataFrame, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base_path.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base_path.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(base_path.with_suffix(".pkl"))


def _build_report(
    fact_quarter_rollforward_inputs: pd.DataFrame,
    fact_quarter_learning_signals: pd.DataFrame,
) -> str:
    repeat_risk = int(fact_quarter_learning_signals["repeated_risk_flag"].sum()) if not fact_quarter_learning_signals.empty else 0
    repeat_action = int(fact_quarter_learning_signals["repeated_action_flag"].sum()) if not fact_quarter_learning_signals.empty else 0
    repeat_delay = int(fact_quarter_learning_signals["repeated_delay_flag"].sum()) if not fact_quarter_learning_signals.empty else 0
    signal_dist = (
        fact_quarter_learning_signals["confidence_adjustment_signal"].value_counts().sort_index().to_dict()
        if not fact_quarter_learning_signals.empty
        else {}
    )
    top_rollforward = (
        fact_quarter_rollforward_inputs.sort_values("carry_over_priority_adjustment", ascending=False)
        .head(20)[["scope_id", "from_quarter", "to_quarter", "project_id", "carry_over_priority_adjustment", "carry_over_probability_adjustment"]]
        .to_string(index=False)
        if not fact_quarter_rollforward_inputs.empty
        else ""
    )
    lines = [
        "# Wave 6 Luigi Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Objective",
        "",
        "- built deterministic quarter-learning signals and quarter-to-quarter roll-forward inputs for the demand-side business layer.",
        "- probability adjustments remain explicit signals only; no source probability values are overwritten.",
        "",
        "## Inputs Used",
        "",
        "- `fact_pipeline_quarterly`",
        "- `fact_decision_history`",
        "- `dim_project_priority`",
        "- `fact_integrated_risk`",
        "",
        "## Learning Logic",
        "",
        "- `repeated_risk_flag`: current quarter top driver matches the prior quarter top driver within the same scope/project.",
        "- `repeated_action_flag`: the inherited previous action type repeats across consecutive quarters.",
        "- `repeated_delay_flag`: the inherited action is a delay-style action (`wait`, `reschedule`, `reroute`, `expedite_shipping`) and still carries over.",
        "- `confidence_adjustment_signal`: deterministic non-positive signal derived from repeated risk/action/delay plus low inherited confidence.",
        "",
        "## Roll-Forward Logic",
        "",
        "- `carry_over_probability_adjustment` reuses the confidence signal and stays separate from business-priority changes.",
        "- `carry_over_priority_adjustment` increases planner attention for unresolved actions, repeated risks, repeated actions, and deferred projects, weighted by current priority band.",
        "- `unresolved_action_penalty` is explicit and synthetic-labeled through the inherited `pending_outcome_synth` status from Wave 5.",
        "",
        "## Validation Summary",
        "",
        f"- learning rows: `{len(fact_quarter_learning_signals):,}`",
        f"- roll-forward rows: `{len(fact_quarter_rollforward_inputs):,}`",
        f"- repeated risk rows: `{repeat_risk}`",
        f"- repeated action rows: `{repeat_action}`",
        f"- repeated delay rows: `{repeat_delay}`",
        f"- confidence adjustment distribution: `{signal_dist}`",
        "",
        "## Cross-Wave Note",
        "",
        "- Wave 5 Luigi uses `denmark_demo` and `global_reference`, while Wave 5 Lara/Carolina use `mvp_3plant`. Wave 6 therefore only materializes learning on the Luigi business scopes provided by its declared inputs.",
        "- Wave 7 should unify scope identifiers across business, capacity, and material learning layers if a single integrated roll-forward policy is required.",
        "",
        "## Top Roll-Forward Inputs",
        "",
        top_rollforward,
    ]
    return "\n".join(lines) + "\n"


def materialize_wave6_luigi() -> dict[str, pd.DataFrame]:
    inputs = load_wave6_inputs(PROCESSED_DIR)
    learning = build_fact_quarter_learning_signals(**inputs)
    rollforward = build_fact_quarter_rollforward_inputs(
        inputs["fact_decision_history"],
        inputs["dim_project_priority"],
        learning,
    )
    _write_table(rollforward, PROCESSED_DIR / "fact_quarter_rollforward_inputs")
    _write_table(learning, PROCESSED_DIR / "fact_quarter_learning_signals")
    REPORT_PATH.write_text(_build_report(rollforward, learning), encoding="utf-8")
    return {
        "fact_quarter_rollforward_inputs": rollforward,
        "fact_quarter_learning_signals": learning,
    }


if __name__ == "__main__":
    materialize_wave6_luigi()
