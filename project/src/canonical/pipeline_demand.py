"""Wave 1 canonical pipeline-demand layer builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from project.src.canonical.project_priority import build_dim_project_priority
from project.src.legacy_adapters.legacy_loader import load_legacy_canonical


REQUIRED_FACT_COLUMNS = [
    "project_id",
    "plant",
    "material",
    "month",
    "raw_qty",
    "probability",
    "expected_qty",
    "requested_date",
    "revenue_tier",
    "customer_segment",
    "project_value",
    "expected_value",
    "priority_score",
    "mapping_ready_flag",
    "reason_code",
]


@dataclass(frozen=True)
class PipelineValidation:
    row_count: int
    duplicate_key_count: int
    unresolved_count: int
    invalid_probability_count: int


def _first_non_null(values: Iterable[object]) -> object:
    for value in values:
        if pd.notna(value):
            text = str(value).strip()
            if text and text.lower() != "nan":
                return value
    return np.nan


def _combine_unique(values: pd.Series) -> object:
    cleaned = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if not text or text.lower() == "nan":
            continue
        cleaned.append(text)
    unique = sorted(set(cleaned))
    if not unique:
        return np.nan
    if len(unique) == 1:
        return unique[0]
    return "|".join(unique)


def _mapping_reason(row: pd.Series) -> tuple[str, str, bool]:
    missing_plant = pd.isna(row["plant"])
    missing_material = pd.isna(row["material"])
    missing_wc = pd.isna(row["work_center"]) or str(row["work_center"]).startswith("Missing")
    missing_tool = pd.isna(row["tool"]) or str(row["tool"]).startswith("Missing")
    invalid_probability = pd.isna(row["probability"]) or not (0.0 <= float(row["probability"]) <= 1.0)
    missing_project = pd.isna(row["project_id"])

    reasons = []
    if missing_project:
        reasons.append("MISSING_PROJECT_METADATA")
    if missing_plant and missing_material:
        reasons.append("MISSING_PLANT_MATERIAL_MAPPING")
    if missing_plant:
        reasons.append("MISSING_PLANT_MAPPING")
    if missing_material:
        reasons.append("MISSING_MATERIAL_MAPPING")
    if missing_wc:
        reasons.append("MISSING_WC_MAPPING")
    if missing_tool:
        reasons.append("MISSING_TOOL_MAPPING")
    if invalid_probability:
        reasons.append("INVALID_PROBABILITY")

    if not reasons:
        return "READY", "", True

    primary = reasons[0]
    detail = "|".join(reasons)
    return primary, detail, False


def _aggregate_fact_rows(df: pd.DataFrame) -> pd.DataFrame:
    group_keys = ["project_id", "plant", "material", "month"]
    grouped = (
        df.groupby(group_keys, dropna=False, as_index=False)
        .agg(
            period_date=("period_date", "first"),
            year=("year", "first"),
            month_num=("month_num", "first"),
            project_name=("project_name", _first_non_null),
            status=("status", _combine_unique),
            material_description=("material_description", _first_non_null),
            source_type=("source_type", _combine_unique),
            raw_qty=("raw_qty", "sum"),
            probability=("probability", "max"),
            requested_date=("requested_date", _first_non_null),
            revenue_tier=("revenue_tier", _first_non_null),
            customer_segment=("customer_segment", _first_non_null),
            project_value=("project_value", "max"),
            tool=("tool", _combine_unique),
            work_center=("work_center", _combine_unique),
            work_center_full=("work_center_full", _combine_unique),
            plant_name=("plant_name", _first_non_null),
        )
    )
    grouped["expected_qty"] = grouped["raw_qty"] * grouped["probability"]
    grouped["expected_value"] = grouped["project_value"] * grouped["probability"]
    return grouped


def build_fact_pipeline_monthly() -> pd.DataFrame:
    """Build the Wave 1 canonical pipeline-demand table from reusable legacy assets."""

    legacy = load_legacy_canonical()
    pipe = legacy.fact_pipeline_monthly.copy()
    proj = legacy.dim_project.copy()
    priority = build_dim_project_priority(proj)

    project_meta = proj.rename(
        columns={
            "requested_delivery": "requested_date",
            "segment": "customer_segment",
            "total_eur": "project_value",
            "status": "project_status",
        }
    )[
        [
            "project_id",
            "project_name",
            "requested_date",
            "customer_segment",
            "project_value",
            "owner",
            "project_status",
        ]
    ].copy()

    df = pipe.copy()
    df = df.drop(columns=["probability"], errors="ignore")
    df = df.rename(
        columns={
            "qty": "raw_qty",
            "probability_frac": "probability",
            "type": "source_type",
        }
    ).copy()
    df["month"] = pd.to_datetime(df["period_date"], errors="coerce")
    df["month_num"] = df["month"].dt.month
    df = df.merge(project_meta, on=["project_id", "project_name"], how="left")
    df["requested_date"] = pd.to_datetime(df["requested_date"], errors="coerce")
    df["project_value"] = pd.to_numeric(df["project_value"], errors="coerce").fillna(0.0)
    df["probability"] = pd.to_numeric(df["probability"], errors="coerce").clip(0.0, 1.0)

    aggregated = _aggregate_fact_rows(df)
    aggregated = aggregated.merge(
        priority[["project_id", "priority_score", "score_version"]],
        on="project_id",
        how="left",
    )

    reasons = aggregated.apply(_mapping_reason, axis=1, result_type="expand")
    reasons.columns = ["reason_code", "reason_code_detail", "mapping_ready_flag"]
    out = pd.concat([aggregated, reasons], axis=1)

    out["source_system"] = "clarix_legacy_loader"
    out["project_value"] = out["project_value"].fillna(0.0)
    out["expected_value"] = out["project_value"] * out["probability"]
    out["expected_qty"] = out["raw_qty"] * out["probability"]
    out["priority_score"] = out["priority_score"].fillna(0.0).clip(0.0, 1.0)

    ordered = REQUIRED_FACT_COLUMNS + [
        "project_name",
        "period_date",
        "year",
        "month_num",
        "status",
        "material_description",
        "tool",
        "work_center",
        "work_center_full",
        "plant_name",
        "source_type",
        "score_version",
        "reason_code_detail",
        "source_system",
    ]
    out = out[ordered].sort_values(["project_id", "month", "plant", "material"], na_position="last")
    return out.reset_index(drop=True)


def validate_fact_pipeline_monthly(fact_pipeline_monthly: pd.DataFrame) -> PipelineValidation:
    """Validate the Wave 1 fact table against Wave 1 rules."""

    if fact_pipeline_monthly.empty:
        return PipelineValidation(0, 0, 0, 0)

    duplicate_count = int(
        fact_pipeline_monthly.duplicated(["project_id", "plant", "material", "month"]).sum()
    )
    invalid_probability_count = int(
        (~fact_pipeline_monthly["probability"].between(0.0, 1.0)).sum()
    )
    unresolved_count = int((~fact_pipeline_monthly["mapping_ready_flag"]).sum())
    return PipelineValidation(
        row_count=int(len(fact_pipeline_monthly)),
        duplicate_key_count=duplicate_count,
        unresolved_count=unresolved_count,
        invalid_probability_count=invalid_probability_count,
    )
