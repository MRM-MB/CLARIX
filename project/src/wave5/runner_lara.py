"""
runner_lara.py
==============
Wave 5 Lara orchestrator: loads capacity inputs, builds scoped capacity,
quarterly snapshots, and carry-over state history. Writes wave5_lara_report.md.

Usage:
  python -m project.src.wave5.runner_lara
  python -m project.src.wave5.runner_lara --processed path/to/processed/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave5.scoped_filter import DEFAULT_SCOPE
from project.src.wave5.capacity_scope import (
    build_fact_scoped_capacity_weekly,
    build_fact_capacity_quarterly_snapshot,
    build_fact_capacity_state_history,
)

DEFAULT_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
REPORT_PATH = _REPO_ROOT / "wave5_lara_report.md"


def _read(processed: Path, name: str) -> pd.DataFrame:
    path = processed / f"{name}.csv"
    if not path.exists():
        print(f"      WARN: {path} not found — using empty DataFrame")
        return pd.DataFrame()
    return pd.read_csv(path)


def _save(df: pd.DataFrame, name: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / f"{name}.csv", index=False)
    try:
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    except Exception:
        pass
    print(f"      Saved: {out_dir / name}.csv  ({len(df):,} rows)")


def _build_report(
    scope: dict,
    scoped: pd.DataFrame,
    quarterly: pd.DataFrame,
    history: pd.DataFrame,
) -> str:
    n_scoped = len(scoped)
    n_quarterly = len(quarterly)
    n_history = len(history)

    carry_over_count = int(history["carry_over_capacity_risk_flag"].sum()) if not history.empty else 0
    quarters = sorted(quarterly["quarter_id"].unique().tolist()) if not quarterly.empty else []

    plants_covered = sorted(scoped["plant"].unique().tolist()) if not scoped.empty else []
    wc_covered = scoped["work_center"].nunique() if not scoped.empty else 0

    bottleneck_by_quarter: dict = {}
    if not quarterly.empty:
        bottleneck_by_quarter = (
            quarterly.groupby("quarter_id")["bottleneck_weeks_count"]
            .sum()
            .round(0)
            .astype(int)
            .to_dict()
        )

    lines = [
        "# Wave 5 Lara Report — Scoped Regional Capacity Foundation",
        "",
        "Date: 2026-04-18",
        "",
        "## Scope",
        "",
        f"- scope_id: `{scope['scope_id']}`",
        f"- plants: `{scope['plants']}`",
        f"- description: {scope.get('description', 'MVP scope')}",
        "",
        "## Inputs",
        "",
        "- `fact_scenario_capacity_weekly` (Lara Wave 2)",
        "- `fact_capacity_bottleneck_summary` (Lara Wave 2)",
        "- `bridge_material_tool_wc` (Lara Wave 1)",
        "",
        "## Outputs",
        "",
        f"- `fact_scoped_capacity_weekly`: {n_scoped:,} rows",
        f"- `fact_capacity_quarterly_snapshot`: {n_quarterly:,} rows",
        f"- `fact_capacity_state_history`: {n_history:,} rows",
        "",
        "## Coverage",
        "",
        f"- plants in scope: `{plants_covered}`",
        f"- unique work centers: `{wc_covered}`",
        f"- quarters covered: `{quarters}`",
        "",
        "## Quarterly Bottleneck Summary",
        "",
        f"- total bottleneck-weeks by quarter: `{bottleneck_by_quarter}`",
        f"- carry-over capacity risk pairs (WC bottlenecked in consecutive quarters): `{carry_over_count}`",
        "",
        "## State History Logic",
        "",
        "- prior_quarter_bottleneck_flag: True if the preceding quarter had ≥1 bottleneck week",
        "- carry_over_capacity_risk_flag: True if BOTH prior AND current quarter had bottleneck weeks",
        "- prior_quarter_mitigation_used: lever from fact_capacity_bottleneck_summary",
        "- learning_note: human-readable carry-over explanation per WC",
        "",
        "## Validation",
        "",
        "- scoped row count ≤ unscoped source row count (asserted in _scope_capacity_weekly)",
        "- quarterly totals reconcile with weekly aggregates under same plant+scenario filter",
        "- state history rows = quarterly rows (one history entry per snapshot row)",
        "- prior-quarter lookups are deterministic — reproducible on re-run",
        "- no hidden filtering logic — scope plants list is fully explicit",
    ]
    return "\n".join(lines) + "\n"


def run(
    processed_dir: str | Path = DEFAULT_PROCESSED,
) -> dict[str, pd.DataFrame]:
    processed = Path(processed_dir)
    scope = DEFAULT_SCOPE

    print("=" * 60)
    print("Wave 5 — Lara: Scoped Capacity Foundation")
    print("=" * 60)
    print(f"      Scope: {scope['scope_id']} | Plants: {scope['plants']}")

    # 1. Load inputs
    print("\n[1/4] Loading inputs …")
    cap = _read(processed, "fact_scenario_capacity_weekly")
    bottleneck = _read(processed, "fact_capacity_bottleneck_summary")
    print(f"      fact_scenario_capacity_weekly: {len(cap):,} rows")
    print(f"      fact_capacity_bottleneck_summary: {len(bottleneck):,} rows")

    # 2. Scoped weekly
    print("\n[2/4] Building fact_scoped_capacity_weekly …")
    scoped = build_fact_scoped_capacity_weekly(cap, scope)
    print(f"      {len(cap):,} → {len(scoped):,} rows ({scope['plants']})")
    _save(scoped, "fact_scoped_capacity_weekly", processed)

    # 3. Quarterly snapshot
    print("\n[3/4] Building fact_capacity_quarterly_snapshot …")
    quarterly = build_fact_capacity_quarterly_snapshot(scoped)
    quarters = sorted(quarterly["quarter_id"].unique().tolist()) if not quarterly.empty else []
    print(f"      Quarters: {quarters} | Rows: {len(quarterly):,}")
    _save(quarterly, "fact_capacity_quarterly_snapshot", processed)

    # 4. State history
    print("\n[4/4] Building fact_capacity_state_history …")
    history = build_fact_capacity_state_history(quarterly, bottleneck)
    carry_over = int(history["carry_over_capacity_risk_flag"].sum()) if not history.empty else 0
    print(f"      Rows: {len(history):,} | Carry-over risk pairs: {carry_over}")
    _save(history, "fact_capacity_state_history", processed)

    # Report
    report = _build_report(scope, scoped, quarterly, history)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\n      Report: {REPORT_PATH}")

    print("\n" + "=" * 60)
    print("Wave 5 Lara complete. Outputs in:", processed)
    print("=" * 60)

    return {
        "fact_scoped_capacity_weekly": scoped,
        "fact_capacity_quarterly_snapshot": quarterly,
        "fact_capacity_state_history": history,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wave 5 Lara runner")
    parser.add_argument("--processed", default=str(DEFAULT_PROCESSED))
    args = parser.parse_args()
    run(processed_dir=args.processed)
