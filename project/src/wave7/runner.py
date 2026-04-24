"""
runner.py
=========
Wave 7 Lara runner: build fact_planner_actions_v2.

Usage:
    python -m project.src.wave7.runner
    python -m project.src.wave7.runner --processed path/to/processed/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave7.planner_actions_v2 import build_fact_planner_actions_v2

DEFAULT_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
REPORT_PATH = _REPO_ROOT / "planner_actions_v2_report.md"


def _read(path: Path, name: str) -> pd.DataFrame:
    full = path / f"{name}.csv"
    if not full.exists():
        print(f"      WARN: {full} not found — using empty DataFrame")
        return pd.DataFrame()
    return pd.read_csv(full)


def _save(df: pd.DataFrame, name: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / f"{name}.csv", index=False)
    try:
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    except Exception:
        pass
    print(f"      Saved: {out_dir / name}.csv  ({len(df):,} rows)")


def _build_report(actions: pd.DataFrame) -> str:
    n = len(actions)
    scopes = sorted(actions["scope_id"].dropna().unique().tolist()) if not actions.empty else []
    scenarios = sorted(actions["scenario"].dropna().unique().tolist()) if not actions.empty else []
    quarters = sorted(actions["quarter_id"].dropna().unique().tolist()) if not actions.empty else []
    act_dist = actions["action_type"].value_counts().to_dict() if not actions.empty else {}
    avg_score = round(float(actions["action_score"].mean()), 4) if not actions.empty else 0.0
    avg_conf = round(float(actions["confidence"].mean()), 4) if not actions.empty else 0.0
    maint_actions = int(actions["action_type"].isin(["shift_maintenance", "protect_capacity_window"]).sum()) if not actions.empty else 0

    lines = [
        "# planner_actions_v2_report.md",
        "",
        "Wave 7 Lara — Maintenance-aware, region-scoped, quarter-aware planner action engine",
        "",
        "Date: 2026-04-18",
        "",
        "## Inputs",
        "",
        "- `fact_integrated_risk` (Wave 5)",
        "- `fact_effective_capacity_weekly_v2` (Wave 6 Lara)",
        "- `fact_maintenance_impact_summary` (Wave 6 Lara)",
        "- `dim_region_scope` (Wave 1)",
        "- `dim_action_policy` (Wave 3)",
        "- `fact_quarter_service_memory` (Wave 6 Carolina)",
        "",
        "## Action Families",
        "",
        "| Action | Description |",
        "|--------|-------------|",
        "| buy_now | Order immediately — sourcing risk above threshold |",
        "| hedge_inventory | Add safety stock buffer — moderate sourcing risk |",
        "| upshift | Increase shift hours — capacity risk detected |",
        "| reschedule | Defer/spread production — manageable risk level |",
        "| split_production | Distribute load across plants/weeks — critical capacity |",
        "| escalate | Escalate to management — risk above safe operating range |",
        "| reroute | Switch shipping lane — high logistics risk |",
        "| expedite_shipping | Expedite freight — logistics pressure |",
        "| shift_maintenance | Move maintenance to lower-load window — maintenance conflicts high-load period |",
        "| protect_capacity_window | Defer maintenance — bottleneck WC has scheduled downtime |",
        "| wait | No action — risk within acceptable range |",
        "",
        "## Output",
        "",
        f"- `fact_planner_actions_v2`: {n:,} rows",
        f"  - scope_ids: `{scopes}`",
        f"  - scenarios: `{scenarios}`",
        f"  - quarters: `{quarters}`",
        f"  - action type distribution: `{act_dist}`",
        f"  - avg action_score: {avg_score}",
        f"  - avg confidence: {avg_conf}",
        f"  - maintenance-specific actions (shift_maintenance + protect_capacity_window): {maint_actions}",
        "",
        "## Design Decisions",
        "",
        "- **Grain:** (scope_id, scenario, quarter_id, project_id, plant) — one action per combination",
        "- **Risk aggregation:** integrated_risk weekly rows aggregated to quarter by mean; mode of top_driver",
        "- **Scope assignment:** plant → region via dim_region_scope.included_plants; fallback to global_reference",
        "- **Maintenance context:** derived from fact_maintenance_impact_summary (worst WC per plant)",
        "- **Protect opportunity:** detected when effective_capacity has bottleneck_flag=True AND scheduled_maintenance_hours>0 in same WC-week",
        "- **Caution carry-over:** service_memory carry_over_service_caution_flag boosts action_score by 5%",
        "- **Reroute target:** plant with lowest avg capacity_risk in same scope+scenario+quarter",
        "- **Deterministic:** seeded inputs, no randomness",
        "",
        "## Validation",
        "",
        "- Every action maps to a visible driver (top_driver in explanation_trace)",
        "- maintenance-related actions carry maint_severity and has_protect_opportunity in trace",
        "- action_score ∈ [0, 1]",
        "- confidence ∈ [0, 1]",
        "- No null scope_id, scenario, quarter_id, project_id, plant",
        "- Unique on natural key (scope_id, scenario, quarter_id, project_id, plant)",
    ]
    return "\n".join(lines) + "\n"


def run(processed_dir: str | Path = DEFAULT_PROCESSED) -> dict[str, pd.DataFrame]:
    processed = Path(processed_dir)

    print("=" * 60)
    print("Wave 7 — Lara: Planner Actions v2")
    print("=" * 60)

    print("\n[1/4] Loading inputs ...")
    integrated_risk = _read(processed, "fact_integrated_risk")
    effective_capacity = _read(processed, "fact_effective_capacity_weekly_v2")
    maintenance_impact = _read(processed, "fact_maintenance_impact_summary")
    region_scope = _read(processed, "dim_region_scope")
    action_policy = _read(processed, "dim_action_policy")
    service_memory = _read(processed, "fact_quarter_service_memory")

    print(f"      fact_integrated_risk:              {len(integrated_risk):,} rows")
    print(f"      fact_effective_capacity_weekly_v2: {len(effective_capacity):,} rows")
    print(f"      fact_maintenance_impact_summary:   {len(maintenance_impact):,} rows")
    print(f"      dim_region_scope:                  {len(region_scope):,} rows")
    print(f"      dim_action_policy:                 {len(action_policy):,} rows")
    print(f"      fact_quarter_service_memory:       {len(service_memory):,} rows")

    print("\n[2/4] Building fact_planner_actions_v2 ...")
    actions = build_fact_planner_actions_v2(
        integrated_risk=integrated_risk,
        effective_capacity=effective_capacity,
        maintenance_impact=maintenance_impact,
        region_scope=region_scope,
        action_policy=action_policy,
        service_memory=service_memory,
    )

    if not actions.empty:
        act_dist = actions["action_type"].value_counts().to_dict()
        maint_cnt = int(actions["action_type"].isin(["shift_maintenance", "protect_capacity_window"]).sum())
        scopes = sorted(actions["scope_id"].dropna().unique().tolist())
        print(f"      Rows: {len(actions):,}")
        print(f"      Action distribution: {act_dist}")
        print(f"      Maintenance actions: {maint_cnt}")
        print(f"      Scopes: {scopes}")

    print("\n[3/4] Saving outputs ...")
    _save(actions, "fact_planner_actions_v2", processed)

    print("\n[4/4] Writing report ...")
    report = _build_report(actions)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"      Report: {REPORT_PATH}")

    print("\n" + "=" * 60)
    print("Wave 7 Lara complete. Outputs in:", processed)
    print("=" * 60)

    return {"fact_planner_actions_v2": actions}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wave 7 Lara runner")
    parser.add_argument("--processed", default=str(DEFAULT_PROCESSED))
    args = parser.parse_args()
    run(processed_dir=args.processed)
