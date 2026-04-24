"""
runner.py
=========
Wave 2 orchestrator: builds all outputs, validates, and saves.

Usage:
  python -m project.src.wave2.runner
  python -m project.src.wave2.runner --xlsx path/to/data.xlsx --out project/data/wave2/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave2.demand_translation import build_fact_translated_project_demand_weekly
from project.src.wave2.capacity_overlay import (
    build_fact_scenario_capacity_weekly,
    validate_scenario_capacity,
)
from project.src.wave2.bottleneck_engine import build_fact_capacity_bottleneck_summary

DEFAULT_OUT = _REPO_ROOT / "project" / "data" / "wave2"


def run(
    xlsx_path: str | Path | None = None,
    out_dir: str | Path = DEFAULT_OUT,
    *,
    save_parquet: bool = True,
    save_csv: bool = False,
) -> dict[str, pd.DataFrame]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Wave 2 — Lara: Capacity Overlay & Bottleneck Engine")
    print("=" * 60)

    # 1. Demand translation
    print("\n[1/3] Building fact_translated_project_demand_weekly …")
    demand = build_fact_translated_project_demand_weekly(xlsx_path)
    n_scenarios = demand["scenario_name"].nunique() if not demand.empty else 0
    print(f"      Rows: {len(demand):,}  |  Scenarios: {n_scenarios}  "
          f"|  WCs covered: {demand['work_center'].nunique() if not demand.empty else 0}")
    _save(demand, "fact_translated_project_demand_weekly", out_dir, save_parquet, save_csv)

    # 2. Capacity overlay
    print("\n[2/3] Building fact_scenario_capacity_weekly …")
    cap = build_fact_scenario_capacity_weekly(demand, xlsx_path)
    val = validate_scenario_capacity(cap)
    print(f"      Rows: {len(cap):,}  |  Unique at grain: {bool(val.get('unique_at_grain'))}  "
          f"|  Bottleneck WC-weeks: {val.get('bottleneck_wc_weeks', 0)}  "
          f"|  Total overload hrs: {val.get('overload_hours_total', 0)}")
    if not val.get("unique_at_grain"):
        print(f"      WARNING: {val.get('duplicate_rows')} duplicate grain rows!")
    _save(cap, "fact_scenario_capacity_weekly", out_dir, save_parquet, save_csv)

    # 3. Bottleneck summary
    print("\n[3/3] Building fact_capacity_bottleneck_summary …")
    bn = build_fact_capacity_bottleneck_summary(cap, demand, xlsx_path)
    if not bn.empty:
        sev = bn["bottleneck_severity"].value_counts().to_dict()
        print(f"      Rows: {len(bn):,}  |  Severity: {sev}")
    else:
        print("      No bottlenecks detected (or no data)")
    _save(bn, "fact_capacity_bottleneck_summary", out_dir, save_parquet, save_csv)

    print("\n" + "=" * 60)
    print("Wave 2 complete. Outputs in:", out_dir)
    print("=" * 60)

    return {
        "fact_translated_project_demand_weekly": demand,
        "fact_scenario_capacity_weekly": cap,
        "fact_capacity_bottleneck_summary": bn,
        "_validation": val,
    }


def _save(df, name, out_dir, parquet, csv):
    if df.empty:
        print(f"      WARN: {name} is empty — skipping save")
        return
    if parquet:
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    if csv:
        df.to_csv(out_dir / f"{name}.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wave 2 Lara runner")
    parser.add_argument("--xlsx", default=None)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args()
    run(xlsx_path=args.xlsx, out_dir=args.out, save_csv=args.csv)
