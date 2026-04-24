"""Materialize Wave 1 outputs for Luigi."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from project.src.canonical.pipeline_demand import (
    build_fact_pipeline_monthly,
    validate_fact_pipeline_monthly,
)
from project.src.canonical.project_priority import (
    build_dim_project_priority,
    validate_dim_project_priority,
)
from project.src.legacy_adapters.legacy_loader import load_legacy_canonical
from project.src.scenarios.demand_qualification import build_scenario_project_demand_seed


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
ROOT_REPORT_PATH = PROJECT_ROOT / "wave1_luigi_report.md"


def _write_table(df: pd.DataFrame, path_without_suffix: Path) -> None:
    path_without_suffix.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path_without_suffix.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(path_without_suffix.with_suffix(".parquet"), index=False)
    except ImportError:
        df.to_pickle(path_without_suffix.with_suffix(".pkl"))


def _build_report(
    fact_pipeline_monthly: pd.DataFrame,
    dim_project_priority: pd.DataFrame,
    scenario_seed: pd.DataFrame,
) -> str:
    fact_val = validate_fact_pipeline_monthly(fact_pipeline_monthly)
    priority_val = validate_dim_project_priority(dim_project_priority)
    unresolved_summary = (
        fact_pipeline_monthly["reason_code"].value_counts(dropna=False).sort_values(ascending=False).to_dict()
    )

    lines = [
        "# Wave 1 Luigi Report",
        "",
        "Date: 2026-04-18",
        "",
        "## Legacy Component Decisions",
        "",
        "`clarix.data_loader` | canonical workbook ingestion and monthly unpivot | action=KEEP | reused directly through `project/src/legacy_adapters/legacy_loader.py` because it already normalizes 1_1, 1_2, and 1_3 reliably",
        "",
        "`CanonicalData.fact_pipeline_monthly` | legacy monthly pipeline fact | action=ADAPT | reused as the Wave 1 base and reshaped to the shared contract with explicit mapping flags and de-duplication at `(project_id, plant, material, month)` grain",
        "",
        "`CanonicalData.dim_project` | legacy project metadata dimension | action=ADAPT | reused as the seed for `dim_project_priority` and value/date metadata enrichment",
        "",
        "`clarix.engine._apply_scenario()` | legacy scenario transform pattern | action=ADAPT | logic concept preserved, but Wave 1 emits explicit `scenario_project_demand_seed` rows instead of relying on UI-time transforms",
        "",
        "`notebooks/starter_notebook.ipynb` | exploratory notebook | action=DEPRECATE | not used in Wave 1 because downstream agents need stable contracts, not notebook state",
        "",
        "## New Modules Created",
        "",
        "- `project/src/legacy_adapters/legacy_loader.py`",
        "- `project/src/canonical/pipeline_demand.py`",
        "- `project/src/canonical/project_priority.py`",
        "- `project/src/scenarios/demand_qualification.py`",
        "- `project/src/loaders/materialize_wave1.py`",
        "",
        "## Schema Compliance",
        "",
        f"- `fact_pipeline_monthly` rows: `{fact_val.row_count}`",
        f"- duplicate `(project_id, plant, material, month)` keys: `{fact_val.duplicate_key_count}`",
        f"- invalid probabilities: `{fact_val.invalid_probability_count}`",
        f"- unresolved mappings: `{fact_val.unresolved_count}`",
        f"- `dim_project_priority` rows: `{priority_val.row_count}`",
        f"- priority score bounds: `{priority_val.priority_min:.4f}` to `{priority_val.priority_max:.4f}`",
        f"- scenario seed rows: `{len(scenario_seed)}`",
        "",
        "## Edge Cases",
        "",
        f"- Legacy pipeline contained unresolved route/material rows; Wave 1 preserves them with explicit reason codes instead of dropping them. Summary: `{unresolved_summary}`",
        "- Legacy pipeline contained duplicate null-key rows across plate/gasket unresolved records; Wave 1 aggregates them to contract grain and recomputes deterministic quantities.",
        "- Requested date exists for all current projects, so urgency scoring is deterministic for this dataset snapshot dated 2026-04-18.",
        "",
        "## Blockers For Wave 2",
        "",
        "- Month-to-week translation still depends on a future calendar bridge from sheet `2_4 Model Calendar`.",
        "- Logistics, disruption, and integrated risk layers still require new contracts and synthetic enrichment inputs.",
        "- `mapping_ready_flag` currently captures missing route and material mapping, but Wave 2 may need a more granular routing-exception table.",
    ]
    return "\n".join(lines) + "\n"


def materialize_wave1() -> dict[str, pd.DataFrame]:
    """Build, persist, and report all Wave 1 Luigi outputs."""

    legacy = load_legacy_canonical()
    fact_pipeline_monthly = build_fact_pipeline_monthly()
    dim_project_priority = build_dim_project_priority(legacy.dim_project)
    scenario_project_demand_seed = build_scenario_project_demand_seed(fact_pipeline_monthly)

    _write_table(fact_pipeline_monthly, PROCESSED_DIR / "fact_pipeline_monthly")
    _write_table(dim_project_priority, PROCESSED_DIR / "dim_project_priority")
    _write_table(scenario_project_demand_seed, INTERIM_DIR / "scenario_project_demand_seed")

    report_text = _build_report(fact_pipeline_monthly, dim_project_priority, scenario_project_demand_seed)
    ROOT_REPORT_PATH.write_text(report_text, encoding="utf-8")

    return {
        "fact_pipeline_monthly": fact_pipeline_monthly,
        "dim_project_priority": dim_project_priority,
        "scenario_project_demand_seed": scenario_project_demand_seed,
    }


if __name__ == "__main__":
    materialize_wave1()
