"""
runner.py
=========
Wave 1 orchestrator: builds all 4 outputs, validates, and saves.

Usage:
  python -m project.src.wave1.runner
  python -m project.src.wave1.runner --xlsx path/to/data.xlsx --out project/data/wave1/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Ensure repo root importable
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave1.operational_mapping import (
    build_bridge_material_tool_wc,
    summarise_mapping_gaps,
)
from project.src.wave1.capacity_baseline import (
    build_fact_wc_capacity_weekly,
    validate_capacity,
)
from project.src.wave1.calendar_bridge import (
    build_bridge_month_week_calendar,
    validate_calendar_bridge,
)
from project.src.wave1.scenario_limits import build_dim_wc_scenario_limits


DEFAULT_OUT = _REPO_ROOT / "project" / "data" / "wave1"


def run(
    xlsx_path: str | Path | None = None,
    out_dir: str | Path = DEFAULT_OUT,
    *,
    save_parquet: bool = True,
    save_csv: bool = False,
) -> dict[str, pd.DataFrame]:
    """Build all Wave 1 outputs, validate, and optionally save."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Wave 1 — Lara: Operational Spine & Capacity Foundation")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. bridge_material_tool_wc
    # ------------------------------------------------------------------
    print("\n[1/4] Building bridge_material_tool_wc …")
    bridge = build_bridge_material_tool_wc(xlsx_path)
    gap_summary = summarise_mapping_gaps(bridge) if not bridge.empty else {}
    print(f"      Rows: {len(bridge):,}  |  Gaps: {json.dumps(gap_summary, indent=None)}")
    _save(bridge, "bridge_material_tool_wc", out_dir, save_parquet, save_csv)

    # ------------------------------------------------------------------
    # 2. fact_wc_capacity_weekly
    # ------------------------------------------------------------------
    print("\n[2/4] Building fact_wc_capacity_weekly …")
    capacity = build_fact_wc_capacity_weekly(xlsx_path)
    cap_val = validate_capacity(capacity) if not capacity.empty else {}
    unique_ok = cap_val.get("unique_by_plant_wc_week", 0)
    print(f"      Rows: {len(capacity):,}  |  Unique(plant,wc,week): {bool(unique_ok)}  "
          f"|  Overloaded WC-weeks: {cap_val.get('overloaded_wc_weeks', '?')}")
    if not unique_ok:
        print(f"      WARNING: {cap_val.get('duplicate_rows')} duplicate (plant,wc,week) rows!")
    _save(capacity, "fact_wc_capacity_weekly", out_dir, save_parquet, save_csv)

    # ------------------------------------------------------------------
    # 3. bridge_month_week_calendar
    # ------------------------------------------------------------------
    print("\n[3/4] Building bridge_month_week_calendar …")
    calendar = build_bridge_month_week_calendar(xlsx_path)
    cal_val = validate_calendar_bridge(calendar) if not calendar.empty else {}
    print(f"      Rows: {len(calendar):,}  |  Version: {cal_val.get('bridge_version', '?')}  "
          f"|  Weights valid: {cal_val.get('valid', False)}  "
          f"|  Max weight error: {cal_val.get('max_allocation_weight_error', '?')}")
    _save(calendar, "bridge_month_week_calendar", out_dir, save_parquet, save_csv)

    # ------------------------------------------------------------------
    # 4. dim_wc_scenario_limits
    # ------------------------------------------------------------------
    print("\n[4/4] Building dim_wc_scenario_limits …")
    limits = build_dim_wc_scenario_limits(xlsx_path)
    limit_levels = limits["scenario_limit_name"].value_counts().to_dict() if not limits.empty else {}
    print(f"      Rows: {len(limits):,}  |  Levels: {limit_levels}")
    _save(limits, "dim_wc_scenario_limits", out_dir, save_parquet, save_csv)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Wave 1 complete. Outputs in:", out_dir)
    print("=" * 60)

    return {
        "bridge_material_tool_wc": bridge,
        "fact_wc_capacity_weekly": capacity,
        "bridge_month_week_calendar": calendar,
        "dim_wc_scenario_limits": limits,
        "_validation": {
            "mapping_gaps": gap_summary,
            "capacity": cap_val,
            "calendar": cal_val,
        },
    }


def _save(
    df: pd.DataFrame,
    name: str,
    out_dir: Path,
    parquet: bool,
    csv: bool,
) -> None:
    if df.empty:
        print(f"      WARN: {name} is empty — skipping save")
        return
    if parquet:
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    if csv:
        df.to_csv(out_dir / f"{name}.csv", index=False)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wave 1 Lara runner")
    parser.add_argument("--xlsx", default=None, help="Path to hackathon_dataset.xlsx")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory")
    parser.add_argument("--csv", action="store_true", help="Also save CSV")
    args = parser.parse_args()
    run(xlsx_path=args.xlsx, out_dir=args.out, save_csv=args.csv)
