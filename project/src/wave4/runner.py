"""
runner.py
=========
Wave 4 Lara orchestrator: loads all inputs, builds fact_planner_actions,
saves outputs, and writes planner_actions_report.md.

Usage:
  python -m project.src.wave4.runner
  python -m project.src.wave4.runner --processed path/to/processed/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave4.action_engine import build_fact_planner_actions

DEFAULT_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
REPORT_PATH = _REPO_ROOT / "planner_actions_report.md"


def _load_inputs(processed: Path) -> dict[str, pd.DataFrame]:
    def _read(name: str) -> pd.DataFrame:
        path = processed / f"{name}.csv"
        if not path.exists():
            print(f"      WARN: {path} not found — using empty DataFrame")
            return pd.DataFrame()
        return pd.read_csv(path)

    return {
        "risk": _read("fact_integrated_risk_base"),
        "policy": _read("dim_action_policy"),
        "bottleneck": _read("fact_capacity_bottleneck_summary"),
        "quality_flags": _read("fact_data_quality_flags"),
        "resilience": _read("fact_scenario_resilience_impact"),
    }


def _save(df: pd.DataFrame, name: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / f"{name}.csv", index=False)
    try:
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    except Exception:
        df.to_pickle(out_dir / f"{name}.pkl")
    print(f"      Saved: {out_dir / name}.csv")


def _build_report(actions: pd.DataFrame) -> str:
    n_total = len(actions)
    by_action = actions["action_type"].value_counts().to_dict() if not actions.empty else {}
    by_confidence = actions["confidence"].value_counts().to_dict() if not actions.empty else {}
    by_scenario = actions.groupby("scenario")["action_score"].mean().round(4).to_dict() if not actions.empty else {}

    top20 = ""
    if not actions.empty:
        top = actions.head(20)[
            ["scenario", "action_type", "action_score", "project_id",
             "plant", "material_or_wc", "confidence", "reason"]
        ]
        top20 = top.to_string(index=False)

    lines = [
        "# Planner Actions Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Inputs",
        "",
        "- `fact_integrated_risk_base` (Luigi Wave 3)",
        "- `dim_action_policy` (Carolina Wave 3)",
        "- `fact_capacity_bottleneck_summary` (Lara Wave 2)",
        "- `fact_data_quality_flags` (Carolina Wave 3)",
        "- `fact_scenario_resilience_impact` (Lara Wave 3)",
        "",
        "## Output Summary",
        "",
        f"- total action rows: `{n_total}`",
        f"- action type distribution: `{by_action}`",
        f"- confidence distribution: `{by_confidence}`",
        f"- mean action_score by scenario: `{by_scenario}`",
        "",
        "## Top 20 Actions (by action_score)",
        "",
        "```",
        top20,
        "```",
        "",
        "## Action Logic",
        "",
        "- buy_now: sourcing_risk ≥ 0.70 AND priority ≥ 0.30 AND risk_base ≥ 0.60",
        "- wait: risk_base < 0.30 AND priority < 0.40",
        "- reroute: logistics_risk ≥ 0.50 AND priority ≥ 0.40",
        "- upshift: capacity_risk ≥ 0.80 AND priority ≥ 0.30",
        "- expedite_shipping: logistics_risk ≥ 0.60 AND priority ≥ 0.50",
        "- reschedule: capacity_risk ≥ 0.60 AND priority < 0.50",
        "- escalate: action_score_base ≥ 0.80 AND top_driver ∈ {capacity_risk, sourcing_risk} AND priority ≥ 0.70",
        "- hedge_inventory: sourcing_risk ≥ 0.50 AND priority ≥ 0.20",
        "- split_production: capacity_risk ≥ 0.70 AND priority ≥ 0.40",
        "",
        "## Quality Penalty Application",
        "",
        "- weaken flags → action_score reduced by penalty × 0.20",
        "- block flags → confidence forced to low",
        "- flag_only → shown with warning, score unaffected",
        "- disruption_risk from Wave 3 adds up to 10% boost to action_score",
        "",
        "## Validation",
        "",
        "- every action row carries explanation_trace with full driver breakdown",
        "- recommended_target_plant set only for reroute and split_production",
        "- top 20 actions readable by product owners (see table above)",
        "- no black-box logic — all triggers are explicit boolean thresholds",
    ]
    return "\n".join(lines) + "\n"


def run(
    processed_dir: str | Path = DEFAULT_PROCESSED,
) -> dict[str, pd.DataFrame]:
    processed = Path(processed_dir)

    print("=" * 60)
    print("Wave 4 — Lara: Planner Action Engine")
    print("=" * 60)

    print("\n[1/3] Loading inputs …")
    inputs = _load_inputs(processed)
    risk = inputs["risk"]
    print(f"      fact_integrated_risk_base: {len(risk):,} rows")
    print(f"      dim_action_policy: {len(inputs['policy'])} action types")
    print(f"      fact_capacity_bottleneck_summary: {len(inputs['bottleneck']):,} rows")
    print(f"      fact_data_quality_flags: {len(inputs['quality_flags']):,} rows")
    print(f"      fact_scenario_resilience_impact: {len(inputs['resilience']):,} rows")

    print("\n[2/3] Building fact_planner_actions …")
    actions = build_fact_planner_actions(
        risk=inputs["risk"],
        policy=inputs["policy"],
        bottleneck=inputs["bottleneck"],
        quality_flags=inputs["quality_flags"],
        resilience=inputs["resilience"],
    )
    print(f"      Total action rows: {len(actions):,}")
    if not actions.empty:
        print(f"      Action distribution: {actions['action_type'].value_counts().to_dict()}")
        print(f"      Confidence mix: {actions['confidence'].value_counts().to_dict()}")
        print(f"      Mean action_score: {actions['action_score'].mean():.4f}")
    _save(actions, "fact_planner_actions", processed)

    print("\n[3/3] Writing planner_actions_report.md …")
    REPORT_PATH.write_text(_build_report(actions), encoding="utf-8")
    print(f"      Report: {REPORT_PATH}")

    print("\n" + "=" * 60)
    print("Wave 4 complete. Outputs in:", processed)
    print("=" * 60)

    return {"fact_planner_actions": actions}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wave 4 Lara runner")
    parser.add_argument("--processed", default=str(DEFAULT_PROCESSED))
    args = parser.parse_args()
    run(processed_dir=args.processed)
