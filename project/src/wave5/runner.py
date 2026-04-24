"""
runner.py
=========
Wave 5 Carolina orchestrator: loads all inputs, builds all wave 5 outputs,
saves CSVs, and returns a dict of DataFrames.

Usage:
  python -m project.src.wave5.runner
  python -m project.src.wave5.runner --processed path/to/processed/ --synth path/to/synth/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from project.src.wave5.scoped_filter import filter_sourcing, filter_logistics, DEFAULT_SCOPE
from project.src.wave5.quarterly_snapshot import (
    build_sourcing_quarterly_snapshot,
    build_logistics_quarterly_snapshot,
)
from project.src.wave5.decision_history import build_material_decision_history

DEFAULT_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
DEFAULT_SYNTH = _REPO_ROOT / "processed"


def _read(path: Path, name: str) -> pd.DataFrame:
    full = path / f"{name}.csv"
    if not full.exists():
        print(f"      WARN: {full} not found — using empty DataFrame")
        return pd.DataFrame()
    return pd.read_csv(full)


def _save(df: pd.DataFrame, name: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / f"{name}.csv", index=False)
    print(f"      Saved: {out_dir / name}.csv  ({len(df):,} rows)")


def run_carolina_wave5(
    real_processed_dir: str | Path = DEFAULT_PROCESSED,
    synth_processed_dir: str | Path = DEFAULT_SYNTH,
) -> dict[str, pd.DataFrame]:
    processed = Path(real_processed_dir)
    synth = Path(synth_processed_dir)

    print("=" * 60)
    print("Wave 5 — Carolina: Scoped Sourcing & Quarter History")
    print("=" * 60)

    # ------------------------------------------------------------------
    # [1/5] Load inputs
    # ------------------------------------------------------------------
    print("\n[1/5] Loading inputs ...")

    fact_sourcing = _read(processed, "fact_scenario_sourcing_weekly")
    fact_logistics = _read(processed, "fact_scenario_logistics_weekly")
    fact_inventory = _read(processed, "fact_inventory_snapshot")
    dim_procurement = _read(processed, "dim_procurement_logic")

    dim_country = _read(synth, "dim_country_cost_index_synth")
    dim_shipping = _read(synth, "dim_shipping_lane_synth")
    dim_service = _read(synth, "dim_service_level_policy_synth")

    print(f"      fact_scenario_sourcing_weekly:  {len(fact_sourcing):,} rows")
    print(f"      fact_scenario_logistics_weekly: {len(fact_logistics):,} rows")
    print(f"      fact_inventory_snapshot:        {len(fact_inventory):,} rows")
    print(f"      dim_procurement_logic:          {len(dim_procurement):,} rows")
    print(f"      dim_country_cost_index_synth:   {len(dim_country):,} rows")
    print(f"      dim_shipping_lane_synth:        {len(dim_shipping):,} rows")
    print(f"      dim_service_level_policy_synth: {len(dim_service):,} rows")

    # ------------------------------------------------------------------
    # [2/5] Scoped filter
    # ------------------------------------------------------------------
    print(f"\n[2/5] Applying scoped filter — scope: {DEFAULT_SCOPE['scope_id']} "
          f"plants={DEFAULT_SCOPE['plants']} ...")

    scoped_sourcing = filter_sourcing(fact_sourcing)
    scoped_logistics = filter_logistics(fact_logistics)

    _save(scoped_sourcing, "fact_scoped_sourcing_weekly", processed)
    _save(scoped_logistics, "fact_scoped_logistics_weekly", processed)

    print(f"      Sourcing filter: {len(fact_sourcing):,} -> {len(scoped_sourcing):,} rows")
    print(f"      Logistics filter: {len(fact_logistics):,} -> {len(scoped_logistics):,} rows")

    # ------------------------------------------------------------------
    # [3/5] Quarterly snapshots
    # ------------------------------------------------------------------
    print("\n[3/5] Building quarterly snapshots ...")

    sourcing_snapshot = build_sourcing_quarterly_snapshot(scoped_sourcing)
    logistics_snapshot = build_logistics_quarterly_snapshot(scoped_logistics)

    _save(sourcing_snapshot, "fact_sourcing_quarterly_snapshot", processed)
    _save(logistics_snapshot, "fact_logistics_quarterly_snapshot", processed)

    if not sourcing_snapshot.empty:
        qtrs = sorted(sourcing_snapshot["quarter_id"].unique())
        print(f"      Sourcing snapshot quarters: {qtrs}")
    if not logistics_snapshot.empty:
        qtrs = sorted(logistics_snapshot["quarter_id"].unique())
        print(f"      Logistics snapshot quarters: {qtrs}")

    # ------------------------------------------------------------------
    # [4/5] Decision history
    # ------------------------------------------------------------------
    print("\n[4/5] Building material decision history (Q1 -> Q2) ...")

    decision_history = build_material_decision_history(sourcing_snapshot, logistics_snapshot)
    _save(decision_history, "fact_material_decision_history", processed)

    if not decision_history.empty:
        risk_count = decision_history["carry_over_material_risk_flag"].sum()
        total = len(decision_history)
        print(f"      carry_over risk materials: {risk_count}/{total} "
              f"({100 * risk_count / max(total, 1):.1f}%)")
        note_dist = decision_history["learning_note"].value_counts().to_dict()
        for note, cnt in note_dist.items():
            print(f"        [{cnt:4d}] {note}")

    # ------------------------------------------------------------------
    # [5/5] Summary
    # ------------------------------------------------------------------
    print("\n[5/5] Summary")
    outputs = {
        "fact_scoped_sourcing_weekly": scoped_sourcing,
        "fact_scoped_logistics_weekly": scoped_logistics,
        "fact_sourcing_quarterly_snapshot": sourcing_snapshot,
        "fact_logistics_quarterly_snapshot": logistics_snapshot,
        "fact_material_decision_history": decision_history,
    }
    for name, df in outputs.items():
        print(f"      {name}: {len(df):,} rows, {len(df.columns)} cols")

    print("\n" + "=" * 60)
    print("Wave 5 complete. Outputs in:", processed)
    print("=" * 60)

    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wave 5 Carolina runner")
    parser.add_argument("--processed", default=str(DEFAULT_PROCESSED))
    parser.add_argument("--synth", default=str(DEFAULT_SYNTH))
    args = parser.parse_args()
    run_carolina_wave5(
        real_processed_dir=args.processed,
        synth_processed_dir=args.synth,
    )
