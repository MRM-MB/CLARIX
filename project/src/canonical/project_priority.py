"""Wave 1 project-priority dimension builder."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


SCORE_VERSION = "priority_score_v1_2026_04_18"
DEFAULT_AS_OF_DATE = pd.Timestamp("2026-04-18")

REVENUE_TIER_SCORES = {
    "Small": 0.25,
    "Medium": 0.50,
    "Large": 0.75,
    "Strategic": 1.00,
}

STRATEGIC_SEGMENT_SCORES = {
    "Data Center": 1.00,
    "Pharma": 0.95,
    "District Heating": 0.90,
    "Refrigeration": 0.80,
    "Marine": 0.70,
    "Oil & Gas": 0.65,
    "Industrial": 0.60,
    "Food & Beverage": 0.55,
}


@dataclass(frozen=True)
class ProjectPriorityValidation:
    row_count: int
    priority_min: float
    priority_max: float
    missing_requested_date: int
    missing_revenue_tier: int


def _normalize_rank(series: pd.Series) -> pd.Series:
    if series.empty:
        return series.astype(float)
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if numeric.nunique(dropna=False) <= 1:
        return pd.Series(np.where(numeric > 0, 1.0, 0.0), index=series.index, dtype=float)
    return numeric.rank(method="average", pct=True).clip(0.0, 1.0)


def _score_urgency(requested_date: pd.Series, *, as_of_date: pd.Timestamp) -> pd.Series:
    days = (pd.to_datetime(requested_date, errors="coerce") - as_of_date).dt.days
    score = np.select(
        [
            days.isna(),
            days <= 30,
            days <= 90,
            days <= 180,
            days <= 365,
        ],
        [
            0.50,
            1.00,
            0.80,
            0.60,
            0.40,
        ],
        default=0.20,
    )
    return pd.Series(score, index=requested_date.index, dtype=float)


def _score_revenue_tier(revenue_tier: pd.Series) -> pd.Series:
    return revenue_tier.map(REVENUE_TIER_SCORES).fillna(0.50).astype(float)


def _score_strategic_segment(segment: pd.Series) -> pd.Series:
    return segment.map(STRATEGIC_SEGMENT_SCORES).fillna(0.50).astype(float)


def _priority_band(priority_score: pd.Series) -> pd.Series:
    band = np.select(
        [
            priority_score >= 0.85,
            priority_score >= 0.70,
            priority_score >= 0.50,
        ],
        ["critical", "high", "medium"],
        default="low",
    )
    return pd.Series(band, index=priority_score.index, dtype="object")


def _priority_reason_code(df: pd.DataFrame) -> pd.Series:
    conditions = [
        df["project_id"].isna(),
        df["requested_delivery"].isna(),
        df["revenue_tier"].isna(),
        df["total_eur"].isna(),
    ]
    codes = [
        "MISSING_PROJECT_ID",
        "MISSING_REQUESTED_DATE",
        "MISSING_REVENUE_TIER",
        "MISSING_PROJECT_VALUE",
    ]
    return pd.Series(np.select(conditions, codes, default="READY"), index=df.index, dtype="object")


def build_dim_project_priority(
    dim_project: pd.DataFrame,
    *,
    as_of_date: pd.Timestamp = DEFAULT_AS_OF_DATE,
) -> pd.DataFrame:
    """Build the Wave 1 project-priority contract from legacy project metadata."""

    if dim_project.empty:
        columns = [
            "project_id",
            "project_name",
            "owner",
            "region",
            "segment",
            "requested_delivery",
            "revenue_tier",
            "project_value",
            "expected_value",
            "probability_score",
            "urgency_score",
            "revenue_tier_score",
            "expected_value_score",
            "strategic_segment_score",
            "priority_score",
            "priority_band",
            "score_version",
            "reason_code",
        ]
        return pd.DataFrame(columns=columns)

    df = dim_project.copy()
    df["project_value"] = pd.to_numeric(df["total_eur"], errors="coerce").fillna(0.0)
    df["probability"] = pd.to_numeric(df["probability_frac"], errors="coerce").clip(0.0, 1.0)
    df["expected_value"] = df["project_value"] * df["probability"]
    df["probability_score"] = df["probability"]
    df["urgency_score"] = _score_urgency(df["requested_delivery"], as_of_date=as_of_date)
    df["revenue_tier_score"] = _score_revenue_tier(df["revenue_tier"])
    df["expected_value_score"] = _normalize_rank(df["expected_value"])
    df["strategic_segment_score"] = _score_strategic_segment(df["segment"])
    df["priority_score"] = (
        0.35 * df["probability_score"]
        + 0.20 * df["urgency_score"]
        + 0.20 * df["revenue_tier_score"]
        + 0.15 * df["expected_value_score"]
        + 0.10 * df["strategic_segment_score"]
    ).clip(0.0, 1.0)
    df["priority_band"] = _priority_band(df["priority_score"])
    df["score_version"] = SCORE_VERSION
    df["reason_code"] = _priority_reason_code(df)

    out = df[
        [
            "project_id",
            "project_name",
            "owner",
            "region",
            "segment",
            "requested_delivery",
            "revenue_tier",
            "project_value",
            "expected_value",
            "probability_score",
            "urgency_score",
            "revenue_tier_score",
            "expected_value_score",
            "strategic_segment_score",
            "priority_score",
            "priority_band",
            "score_version",
            "reason_code",
        ]
    ].copy()
    return out.sort_values("project_id").reset_index(drop=True)


def validate_dim_project_priority(dim_project_priority: pd.DataFrame) -> ProjectPriorityValidation:
    """Return a compact validation summary for reporting and tests."""

    if dim_project_priority.empty:
        return ProjectPriorityValidation(0, 0.0, 0.0, 0, 0)

    return ProjectPriorityValidation(
        row_count=int(len(dim_project_priority)),
        priority_min=float(dim_project_priority["priority_score"].min()),
        priority_max=float(dim_project_priority["priority_score"].max()),
        missing_requested_date=int(dim_project_priority["requested_delivery"].isna().sum()),
        missing_revenue_tier=int(dim_project_priority["revenue_tier"].isna().sum()),
    )
