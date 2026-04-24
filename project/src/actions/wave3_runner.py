"""Wave 3 Carolina: orchestrator.

Run with:
    python -m project.src.actions.wave3_runner
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .action_policy import build_dim_action_policy
from .qa_guardrails import build_fact_data_quality_flags


def run_carolina_wave3(
    real_processed_dir: str | Path = "project/data/processed",
    synth_processed_dir: str | Path = "processed",
) -> dict[str, pd.DataFrame]:
    """Build and persist dim_action_policy and fact_data_quality_flags.

    Parameters
    ----------
    real_processed_dir:
        Directory containing Wave 2 CSVs (written by previous waves).
    synth_processed_dir:
        Directory containing Wave 1 synthetic CSVs.

    Returns
    -------
    dict with keys 'dim_action_policy' and 'fact_data_quality_flags'.
    """
    real = Path(real_processed_dir)
    real.mkdir(parents=True, exist_ok=True)

    # --- dim_action_policy ---------------------------------------------------
    print("Building dim_action_policy ...")
    policy = build_dim_action_policy()
    policy_path = real / "dim_action_policy.csv"
    policy.to_csv(policy_path, index=False)
    print(f"  Saved {len(policy)} rows -> {policy_path}")

    # --- fact_data_quality_flags ---------------------------------------------
    print("Building fact_data_quality_flags ...")
    flags = build_fact_data_quality_flags(real, synth_processed_dir)
    flags_path = real / "fact_data_quality_flags.csv"
    flags.to_csv(flags_path, index=False)
    print(f"  Saved {len(flags)} rows -> {flags_path}")

    # --- Summary -------------------------------------------------------------
    print("\n=== Wave 3 Carolina Summary ===")
    print(f"  dim_action_policy rows      : {len(policy)}")
    print(f"  fact_data_quality_flags rows: {len(flags)}")

    if len(flags) > 0:
        print("\n  Issue type breakdown:")
        issue_counts = flags["issue_type"].value_counts()
        for issue, count in issue_counts.items():
            print(f"    {issue:<40} {count:>6}")

        print("\n  Severity breakdown:")
        sev_counts = flags["severity"].value_counts()
        for sev, count in sev_counts.items():
            print(f"    {sev:<12} {count:>6}")
    else:
        print("  No quality flags detected.")

    return {
        "dim_action_policy": policy,
        "fact_data_quality_flags": flags,
    }


if __name__ == "__main__":
    run_carolina_wave3()
