"""Materialize Luigi Wave 5 outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.canonical.quarter_business_state import (
    build_dim_region_scope,
    build_fact_decision_history,
    build_fact_pipeline_quarterly,
    build_fact_quarter_business_snapshot,
    load_wave5_inputs,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_PATH = PROJECT_ROOT / "wave5_luigi_report.md"


def _write_table(df: pd.DataFrame, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base_path.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base_path.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(base_path.with_suffix(".pkl"))


def _build_report(
    dim_region_scope: pd.DataFrame,
    fact_pipeline_quarterly: pd.DataFrame,
    fact_quarter_business_snapshot: pd.DataFrame,
    fact_decision_history: pd.DataFrame,
) -> str:
    active_scopes = dim_region_scope[dim_region_scope["active_flag"] == True]["scope_id"].tolist()
    scope_summary = dim_region_scope[["scope_id", "region_name", "included_plants", "scope_rule", "active_flag"]].to_string(index=False)
    quarter_summary = (
        fact_quarter_business_snapshot[["scope_id", "quarter_id", "total_projects", "total_expected_value"]]
        .sort_values(["scope_id", "quarter_id"])
        .to_string(index=False)
        if not fact_quarter_business_snapshot.empty
        else ""
    )
    carry_over = int(fact_decision_history["carry_over_flag"].sum()) if not fact_decision_history.empty else 0
    blockers = [
        "- `fact_planner_actions` has no week grain, so Wave 5 uses a documented adapter that selects prior-quarter actions from the expected-value action catalog plus prior-quarter top driver.",
        "- realized outcomes are still unavailable; `action_outcome_status` remains explicitly labeled as pending synthetic history.",
        "- Wave 6 should add persisted planner run ids or action timestamps so decision history no longer relies on quarter adapters.",
    ]
    lines = [
        "# Wave 5 Luigi Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Region-Scope Logic",
        "",
        "- scopes are explicit business filters over plants and are reproducible from `scope_rule` plus `included_plants`.",
        f"- active scopes: `{active_scopes}`",
        "",
        "```text",
        scope_summary,
        "```",
        "",
        "## Quarter Aggregation Logic",
        "",
        "- `fact_pipeline_quarterly` aggregates `fact_pipeline_monthly` by `scope_id x quarter_id x project_id x plant x material`.",
        "- quarter ids come from the monthly `period_date`, while decision continuity uses `clarix.engine.quarter_label()` over weekly risk rows.",
        "- `fact_quarter_business_snapshot` rolls project-quarter demand into business KPIs and counts high-confidence / strategic projects with explicit deterministic rules.",
        "",
        "```text",
        quarter_summary,
        "```",
        "",
        "## Decision-History Assumptions",
        "",
        "- business continuity uses the `expected_value` scenario as the baseline quarter-state view.",
        "- prior-quarter `top_driver` comes from the highest action-score risk row in the prior quarter.",
        "- prior-quarter `previous_action_type` comes from the planner-action catalog for the same project and plant, constrained by the prior-quarter dominant driver when possible.",
        f"- carry-over rows materialized: `{carry_over}`",
        "",
        "## Blockers For Wave 6",
        "",
        *blockers,
    ]
    return "\n".join(lines) + "\n"


def materialize_wave5_luigi() -> dict[str, pd.DataFrame]:
    inputs = load_wave5_inputs(PROCESSED_DIR)
    dim_region_scope = build_dim_region_scope(inputs["fact_pipeline_monthly"])
    fact_pipeline_quarterly = build_fact_pipeline_quarterly(inputs["fact_pipeline_monthly"], dim_region_scope)
    fact_quarter_business_snapshot = build_fact_quarter_business_snapshot(
        inputs["fact_pipeline_monthly"],
        inputs["dim_project_priority"],
        dim_region_scope,
    )
    fact_decision_history = build_fact_decision_history(
        inputs["fact_pipeline_monthly"],
        inputs["fact_integrated_risk"],
        inputs["fact_planner_actions"],
        dim_region_scope,
    )

    _write_table(dim_region_scope, PROCESSED_DIR / "dim_region_scope")
    _write_table(fact_pipeline_quarterly, PROCESSED_DIR / "fact_pipeline_quarterly")
    _write_table(fact_quarter_business_snapshot, PROCESSED_DIR / "fact_quarter_business_snapshot")
    _write_table(fact_decision_history, PROCESSED_DIR / "fact_decision_history")
    REPORT_PATH.write_text(
        _build_report(
            dim_region_scope,
            fact_pipeline_quarterly,
            fact_quarter_business_snapshot,
            fact_decision_history,
        ),
        encoding="utf-8",
    )

    return {
        "dim_region_scope": dim_region_scope,
        "fact_pipeline_quarterly": fact_pipeline_quarterly,
        "fact_quarter_business_snapshot": fact_quarter_business_snapshot,
        "fact_decision_history": fact_decision_history,
    }


if __name__ == "__main__":
    materialize_wave5_luigi()
