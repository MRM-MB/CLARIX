"""Materialize the unified Wave 2 prerequisite tables into project/data."""

from __future__ import annotations

from calendar import monthrange
from pathlib import Path

import pandas as pd

from project.src.canonical.pipeline_demand import build_fact_pipeline_monthly
from project.src.canonical.project_priority import build_dim_project_priority
from project.src.legacy_adapters.legacy_loader import get_canonical
from project.src.logistics.synthetic_dimensions import (
    build_dim_country_cost_index_synth,
    build_dim_service_level_policy_synth,
    build_dim_shipping_lane_synth,
)
from project.src.sourcing.procurement_logic import build_dim_procurement_logic
from project.src.wave1.calendar_bridge import build_bridge_month_week_calendar
from project.src.wave1.capacity_baseline import build_fact_wc_capacity_weekly
from project.src.wave1.operational_mapping import build_bridge_material_tool_wc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
REPORT_PATH = PROJECT_ROOT / "outputs" / "wave2_readiness_check.md"


def _write_table(df: pd.DataFrame, base_path: Path) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base_path.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base_path.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(base_path.with_suffix(".pkl"))


def _harmonize_bridge_material_tool_wc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(
        columns={
            "tool_no": "tool",
            "cycle_time": "cycle_time_min",
            "mapping_status": "material_status",
        }
    )
    out["work_center_full"] = out["work_center"]
    out["routing_source"] = "legacy_tool_master"
    cols = [
        "plant",
        "material",
        "tool",
        "work_center",
        "work_center_full",
        "cycle_time_min",
        "material_status",
        "routing_source",
        "reason_code",
        "revision",
    ]
    return out[cols].copy()


def _harmonize_fact_wc_capacity_weekly(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(
        columns={
            "available_capacity_hours": "available_hours",
            "planned_load_hours": "baseline_demand_qty",
        }
    )
    out["source_system"] = "clarix_legacy_capacity"
    out["reason_code"] = "READY"
    cols = [
        "plant",
        "work_center",
        "year",
        "week",
        "week_start",
        "available_hours",
        "baseline_demand_qty",
        "remaining_capacity_hours",
        "missing_capacity_hours",
        "source_system",
        "reason_code",
    ]
    return out[cols].copy()


def _harmonize_bridge_month_week_calendar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["period_date"] = pd.to_datetime(
        out["year"].astype(int).astype(str) + "-" + out["month"].astype(int).astype(str).str.zfill(2) + "-01"
    )
    out["month_number"] = out["month"].astype(int)
    out["month_week_weight"] = pd.to_numeric(out["allocation_weight"], errors="coerce").fillna(0.0)
    out["days_in_month_week_overlap"] = out.apply(
        lambda r: int(round(r["month_week_weight"] * monthrange(int(r["period_date"].year), int(r["month_number"]))[1])),
        axis=1,
    )
    out["week_start"] = pd.to_datetime(
        out["year"].astype(int).astype(str) + "-W" + out["week"].astype(int).astype(str).str.zfill(2) + "-1",
        format="%G-W%V-%u",
        errors="coerce",
    )
    out["calendar_source"] = out["bridge_version"]
    cols = [
        "plant",
        "period_date",
        "year",
        "week",
        "month_number",
        "days_in_month_week_overlap",
        "month_week_weight",
        "week_start",
        "calendar_source",
        "working_day_weight",
    ]
    return out[cols].copy()


def _harmonize_fact_finished_to_component(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["reason_code"] = "READY"
    return out


def _harmonize_fact_inventory_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["reason_code"] = "READY"
    return out


def _build_report(results: dict[str, pd.DataFrame]) -> str:
    required = [
        "fact_pipeline_monthly",
        "dim_project_priority",
        "bridge_material_tool_wc",
        "fact_wc_capacity_weekly",
        "bridge_month_week_calendar",
        "fact_finished_to_component",
        "fact_inventory_snapshot",
        "dim_procurement_logic",
        "dim_country_cost_index_synth",
        "dim_shipping_lane_synth",
        "dim_service_level_policy_synth",
    ]
    lines = [
        "# Wave 2 Readiness Check",
        "",
        "Unified source-of-truth code lives under `project/src`.",
        "",
        "## Required tables",
        "",
    ]
    for name in required:
        df = results.get(name)
        status = "READY" if df is not None and not df.empty else "MISSING"
        rows = 0 if df is None else len(df)
        lines.append(f"- `{name}`: {status} ({rows} rows)")
    lines.extend(
        [
            "",
            "## Unification",
            "",
            "- Root-level `src/` was legacy Wave 1 code and has been superseded by `project/src/`.",
            "- All materializers now target `project/data/processed/` or `project/data/synthetic/`.",
            "- Downstream Wave 2 work should import only from `project.src.*`.",
        ]
    )
    return "\n".join(lines) + "\n"


def materialize_wave2_prereqs() -> dict[str, pd.DataFrame]:
    legacy = get_canonical()

    results = {
        "fact_pipeline_monthly": build_fact_pipeline_monthly(),
        "dim_project_priority": build_dim_project_priority(legacy.dim_project),
        "bridge_material_tool_wc": _harmonize_bridge_material_tool_wc(build_bridge_material_tool_wc()),
        "fact_wc_capacity_weekly": _harmonize_fact_wc_capacity_weekly(build_fact_wc_capacity_weekly()),
        "bridge_month_week_calendar": _harmonize_bridge_month_week_calendar(build_bridge_month_week_calendar()),
        "fact_finished_to_component": _harmonize_fact_finished_to_component(legacy.fact_finished_to_component),
        "fact_inventory_snapshot": _harmonize_fact_inventory_snapshot(legacy.fact_inventory_snapshot),
        "dim_procurement_logic": build_dim_procurement_logic(),
        "dim_country_cost_index_synth": build_dim_country_cost_index_synth(),
        "dim_shipping_lane_synth": build_dim_shipping_lane_synth(),
        "dim_service_level_policy_synth": build_dim_service_level_policy_synth(),
    }

    for name, df in results.items():
        target_dir = SYNTHETIC_DIR if name.endswith("_synth") else PROCESSED_DIR
        _write_table(df, target_dir / name)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_build_report(results), encoding="utf-8")
    return results


if __name__ == "__main__":
    materialize_wave2_prereqs()
