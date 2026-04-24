"""
src/carolina/wave2_pipeline.py

Carolina Wave 2 pipeline entry point.
Orchestrates sourcing_engine and logistics_engine, writes output CSVs,
and prints summary statistics.

Usage:
    python -m src.carolina.wave2_pipeline
    python -m src.carolina.wave2_pipeline --processed-dir /path/to/processed
"""

import argparse
import os
import sys

import pandas as pd

from src.carolina.sourcing_engine import run_sourcing_engine
from src.carolina.logistics_engine import run_logistics_engine


def run_carolina_wave2_pipeline(
    real_processed_dir: str = "project/data/processed",
    synth_processed_dir: str = "processed",
) -> dict:
    """
    Run the full Carolina Wave 2 pipeline.

    Parameters
    ----------
    real_processed_dir : str
        Directory with Luigi/Lara W1+2 outputs. Outputs are also written here.
    synth_processed_dir : str
        Directory with Carolina W1 synthetic dimension tables.

    Returns
    -------
    dict with keys:
        "fact_scenario_sourcing_weekly"  -> pd.DataFrame
        "fact_scenario_logistics_weekly" -> pd.DataFrame
    """
    print("=" * 60)
    print("Carolina Wave 2 Pipeline")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Sourcing engine
    # ------------------------------------------------------------------
    print("\n[1/2] Running sourcing engine...")
    sourcing_df = run_sourcing_engine(
        real_processed_dir=real_processed_dir,
        synth_processed_dir=synth_processed_dir,
    )
    sourcing_out = os.path.join(real_processed_dir, "fact_scenario_sourcing_weekly.csv")
    sourcing_df.to_csv(sourcing_out, index=False)
    print(f"      Saved {len(sourcing_df):,} rows -> {sourcing_out}")

    # Sourcing summary
    print("\n  -- Sourcing Summary --")
    print(f"  Total rows          : {len(sourcing_df):,}")
    scenario_counts = sourcing_df["scenario"].value_counts().to_dict()
    for sc, cnt in sorted(scenario_counts.items()):
        print(f"  Scenario {sc:<20}: {cnt:,} rows")
    shortage_count = int(sourcing_df["shortage_flag"].sum())
    print(f"  Shortage rows       : {shortage_count:,}")
    avg_risk = sourcing_df["sourcing_risk_score"].mean()
    print(f"  Avg sourcing risk   : {avg_risk:.4f}")

    # ------------------------------------------------------------------
    # Logistics engine
    # ------------------------------------------------------------------
    print("\n[2/2] Running logistics engine...")
    logistics_df = run_logistics_engine(
        real_processed_dir=real_processed_dir,
        synth_processed_dir=synth_processed_dir,
    )
    logistics_out = os.path.join(real_processed_dir, "fact_scenario_logistics_weekly.csv")
    logistics_df.to_csv(logistics_out, index=False)
    print(f"      Saved {len(logistics_df):,} rows -> {logistics_out}")

    # Logistics summary
    print("\n  -- Logistics Summary --")
    print(f"  Total rows            : {len(logistics_df):,}")
    scenario_counts_l = logistics_df["scenario"].value_counts().to_dict()
    for sc, cnt in sorted(scenario_counts_l.items()):
        print(f"  Scenario {sc:<20}: {cnt:,} rows")
    avg_risk_l = logistics_df["logistics_risk_score"].mean()
    print(f"  Avg logistics risk    : {avg_risk_l:.4f}")
    synth_pct = logistics_df["synthetic_dependency_flag"].mean() * 100
    print(f"  Synthetic flag (%)    : {synth_pct:.1f}%")

    print("\n" + "=" * 60)
    print("Wave 2 pipeline complete.")
    print("=" * 60)

    return {
        "fact_scenario_sourcing_weekly": sourcing_df,
        "fact_scenario_logistics_weekly": logistics_df,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(description="Carolina Wave 2 Pipeline")
    parser.add_argument(
        "--real-processed-dir",
        default="project/data/processed",
        help="Directory with Luigi/Lara W1+2 outputs (default: project/data/processed)",
    )
    parser.add_argument(
        "--synth-processed-dir",
        default="processed",
        help="Directory with Carolina W1 synthetic outputs (default: processed)",
    )
    args = parser.parse_args()
    run_carolina_wave2_pipeline(
        real_processed_dir=args.real_processed_dir,
        synth_processed_dir=args.synth_processed_dir,
    )


if __name__ == "__main__":
    _main()
