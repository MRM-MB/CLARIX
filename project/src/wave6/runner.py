"""
runner.py
=========
Wave 6 orchestrators — two entry points:

  Carolina: Delivery Commitment & Service Memory
    python -m project.src.wave6.runner --carolina
    python -m project.src.wave6.runner --carolina --processed path/to/processed/ --synth path/to/synth/

  Lara: Maintenance & Downtime Simulation Engine
    python -m project.src.wave6.runner
    python -m project.src.wave6.runner --processed path/to/processed/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Carolina imports
from project.src.wave6.delivery_commitment import build_fact_delivery_commitment_weekly
from project.src.wave6.service_memory import build_fact_quarter_service_memory
from project.src.wave6.risk_rollforward import build_fact_delivery_risk_rollforward

# Lara imports
from project.src.wave6.maintenance_catalog import build_dim_maintenance_policy_synth
from project.src.wave6.downtime_calendar import build_fact_maintenance_downtime_calendar, MAINTENANCE_SCENARIOS
from project.src.wave6.effective_capacity import (
    build_fact_effective_capacity_weekly_v2,
    build_fact_maintenance_impact_summary,
)

DEFAULT_PROCESSED = _REPO_ROOT / "project" / "data" / "processed"
DEFAULT_SYNTH = _REPO_ROOT / "processed"
REPORT_PATH = _REPO_ROOT / "wave6_lara_report.md"


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


# ---------------------------------------------------------------------------
# Carolina: Delivery Commitment & Service Memory
# ---------------------------------------------------------------------------

def run_carolina_wave6(
    real_processed_dir: str | Path = DEFAULT_PROCESSED,
    synth_processed_dir: str | Path = DEFAULT_SYNTH,
) -> dict[str, pd.DataFrame]:
    processed = Path(real_processed_dir)
    synth = Path(synth_processed_dir)

    print("=" * 60)
    print("Wave 6 — Carolina: Delivery Commitment & Service Memory")
    print("=" * 60)

    print("\n[1/5] Loading inputs ...")
    scoped_logistics = _read(processed, "fact_scoped_logistics_weekly")
    material_decision_history = _read(processed, "fact_material_decision_history")
    logistics_snapshot = _read(processed, "fact_logistics_quarterly_snapshot")
    dim_service = _read(synth, "dim_service_level_policy_synth")
    project_priority = _read(processed, "dim_project_priority")

    print(f"      fact_scoped_logistics_weekly:       {len(scoped_logistics):,} rows")
    print(f"      fact_material_decision_history:     {len(material_decision_history):,} rows")
    print(f"      fact_logistics_quarterly_snapshot:  {len(logistics_snapshot):,} rows")
    print(f"      dim_service_level_policy_synth:     {len(dim_service):,} rows")
    print(f"      dim_project_priority:               {len(project_priority):,} rows")

    print("\n[2/5] Building fact_delivery_commitment_weekly ...")
    delivery_commitment = build_fact_delivery_commitment_weekly(
        scoped_logistics=scoped_logistics,
        service_policy=dim_service,
        project_priority=project_priority,
    )
    _save(delivery_commitment, "fact_delivery_commitment_weekly", processed)
    if not delivery_commitment.empty:
        risk_mean = delivery_commitment["service_violation_risk"].mean()
        feasible_pct = delivery_commitment["on_time_feasible_flag"].mean() * 100
        print(f"      avg service_violation_risk: {risk_mean:.3f}")
        print(f"      on_time_feasible_flag: {feasible_pct:.1f}% of rows")

    print("\n[3/5] Building fact_quarter_service_memory ...")
    service_memory = build_fact_quarter_service_memory(
        scoped_logistics=scoped_logistics,
        delivery_commitment=delivery_commitment,
    )
    _save(service_memory, "fact_quarter_service_memory", processed)
    if not service_memory.empty:
        qtrs = sorted(service_memory["quarter_id"].unique())
        caution_count = service_memory["carry_over_service_caution_flag"].sum()
        total = len(service_memory)
        print(f"      quarters: {qtrs}")
        print(f"      carry_over_service_caution_flag: {caution_count}/{total} "
              f"({100 * caution_count / max(total, 1):.1f}%)")
        note_dist = service_memory["explanation_note"].value_counts().head(3).to_dict()
        for note, cnt in note_dist.items():
            print(f"        [{cnt:4d}] {note[:80]}")

    print("\n[4/5] Building fact_delivery_risk_rollforward (each quarter -> next) ...")
    risk_rollforward = build_fact_delivery_risk_rollforward(
        service_memory=service_memory,
        logistics_snapshot=logistics_snapshot,
    )
    _save(risk_rollforward, "fact_delivery_risk_rollforward", processed)
    if not risk_rollforward.empty:
        level_dist = risk_rollforward["recommended_caution_level"].value_counts().to_dict()
        print(f"      caution level distribution: {level_dist}")

    print("\n[5/5] Summary")
    outputs = {
        "fact_delivery_commitment_weekly": delivery_commitment,
        "fact_quarter_service_memory": service_memory,
        "fact_delivery_risk_rollforward": risk_rollforward,
    }
    for name, df in outputs.items():
        print(f"      {name}: {len(df):,} rows, {len(df.columns)} cols")

    print("\n" + "=" * 60)
    print("Wave 6 Carolina complete. Outputs in:", processed)
    print("=" * 60)

    return outputs


# ---------------------------------------------------------------------------
# Lara: Maintenance & Downtime Simulation Engine
# ---------------------------------------------------------------------------

def _build_report(
    policy: pd.DataFrame,
    calendar: pd.DataFrame,
    effective: pd.DataFrame,
    impact: pd.DataFrame,
) -> str:
    n_policy = len(policy)
    n_calendar = len(calendar)
    n_effective = len(effective)
    n_impact = len(impact)

    trigger_dist = policy["maintenance_trigger_type"].value_counts().to_dict() if not policy.empty else {}
    scenario_dist = calendar["scenario"].value_counts().to_dict() if not calendar.empty else {}

    avg_pct_lost: dict = {}
    if not impact.empty:
        avg_pct_lost = impact.groupby("scenario")["pct_capacity_lost_to_maintenance"].mean().round(4).to_dict()

    max_delta: dict = {}
    if not impact.empty:
        max_delta = impact.groupby("scenario")["delta_avg_overload_hours"].max().to_dict()

    lines = [
        "# Wave 6 Lara Report — Maintenance & Downtime Simulation Engine",
        "",
        "Date: 2026-04-18",
        "",
        "## Inputs",
        "",
        "- `fact_scoped_capacity_weekly` (Lara Wave 5)",
        "- `fact_capacity_state_history` (Lara Wave 5)",
        "- `bridge_material_tool_wc` (Lara Wave 1)",
        "",
        "## Maintenance Scenarios",
        "",
    ]
    for name, profile in MAINTENANCE_SCENARIOS.items():
        lines.append(f"- **{name}**: {profile['description']}")
    lines += [
        "",
        "## Outputs",
        "",
        f"- `dim_maintenance_policy_synth`: {n_policy} rows",
        f"  - trigger type distribution: `{trigger_dist}`",
        f"- `fact_maintenance_downtime_calendar`: {n_calendar:,} rows",
        f"  - scenario distribution: `{scenario_dist}`",
        f"- `fact_effective_capacity_weekly_v2`: {n_effective:,} rows",
        f"- `fact_maintenance_impact_summary`: {n_impact:,} rows",
        "",
        "## Impact Analysis",
        "",
        f"- mean pct capacity lost by scenario: `{avg_pct_lost}`",
        f"- max additional avg overload hours by scenario: `{max_delta}`",
        "",
        "## Validation",
        "",
        "- effective_available_capacity_hours ≤ nominal_available_capacity_hours (enforced by clip)",
        "- every downtime event references a policy_id with explicit interval and duration",
        "- all synthetic maintenance assumptions carry synthetic_flag=True",
        "- before/after comparison available in fact_maintenance_impact_summary",
        "- phase offsets are seeded and deterministic — reproducible on re-run",
    ]
    return "\n".join(lines) + "\n"


def run(
    processed_dir: str | Path = DEFAULT_PROCESSED,
) -> dict[str, pd.DataFrame]:
    processed = Path(processed_dir)

    print("=" * 60)
    print("Wave 6 — Lara: Maintenance & Downtime Simulation Engine")
    print("=" * 60)

    print("\n[1/5] Loading inputs …")
    scoped = _read(processed, "fact_scoped_capacity_weekly")
    bridge = _read(processed, "bridge_material_tool_wc")
    print(f"      fact_scoped_capacity_weekly: {len(scoped):,} rows")
    print(f"      bridge_material_tool_wc: {len(bridge):,} rows")

    print("\n[2/5] Building dim_maintenance_policy_synth …")
    policy = build_dim_maintenance_policy_synth(scoped, bridge)
    triggers = policy["maintenance_trigger_type"].value_counts().to_dict() if not policy.empty else {}
    print(f"      WC policies: {len(policy)} | Triggers: {triggers}")
    _save(policy, "dim_maintenance_policy_synth", processed)

    print("\n[3/5] Building fact_maintenance_downtime_calendar …")
    calendar = build_fact_maintenance_downtime_calendar(scoped, policy)
    scenarios = calendar["scenario"].unique().tolist() if not calendar.empty else []
    print(f"      Rows: {len(calendar):,} | Scenarios: {scenarios}")
    _save(calendar, "fact_maintenance_downtime_calendar", processed)

    print("\n[4/5] Building fact_effective_capacity_weekly_v2 …")
    effective = build_fact_effective_capacity_weekly_v2(scoped, calendar)
    if not effective.empty:
        avg_loss = (effective["nominal_available_capacity_hours"] - effective["effective_available_capacity_hours"]).mean()
        print(f"      Rows: {len(effective):,} | Mean downtime reduction: {avg_loss:.2f}h/WC-week")
    _save(effective, "fact_effective_capacity_weekly_v2", processed)

    print("\n[5/5] Building fact_maintenance_impact_summary …")
    impact = build_fact_maintenance_impact_summary(effective, scoped)
    if not impact.empty:
        sev = impact["impact_severity"].value_counts().to_dict()
        print(f"      Rows: {len(impact):,} | Severity: {sev}")
    _save(impact, "fact_maintenance_impact_summary", processed)

    report = _build_report(policy, calendar, effective, impact)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\n      Report: {REPORT_PATH}")

    print("\n" + "=" * 60)
    print("Wave 6 Lara complete. Outputs in:", processed)
    print("=" * 60)

    return {
        "dim_maintenance_policy_synth": policy,
        "fact_maintenance_downtime_calendar": calendar,
        "fact_effective_capacity_weekly_v2": effective,
        "fact_maintenance_impact_summary": impact,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wave 6 runner")
    parser.add_argument("--processed", default=str(DEFAULT_PROCESSED))
    parser.add_argument("--synth", default=str(DEFAULT_SYNTH))
    parser.add_argument("--carolina", action="store_true", help="Run Carolina's wave 6 runner")
    args = parser.parse_args()
    if args.carolina:
        run_carolina_wave6(real_processed_dir=args.processed, synth_processed_dir=args.synth)
    else:
        run(processed_dir=args.processed)
