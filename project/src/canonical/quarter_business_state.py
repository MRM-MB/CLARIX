"""Wave 5 Luigi: regional scoping and quarter-state business foundations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from clarix.engine import quarter_label


EXPECTED_VALUE_SCENARIO = "expected_value"
DENMARK_DEMO_PLANTS = ["NW08", "NW09", "NW10"]
DRIVER_ACTION_MAP = {
    "capacity_risk": ["upshift", "split_production", "reschedule", "escalate"],
    "sourcing_risk": ["buy_now", "hedge_inventory", "escalate"],
    "logistics_risk": ["reroute", "expedite_shipping"],
    "disruption_risk": ["reroute", "expedite_shipping", "escalate"],
    "lead_time_risk": ["buy_now", "expedite_shipping", "reschedule"],
    "data_quality_penalty": ["wait", "escalate"],
}
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}


def load_wave5_inputs(base_dir: str | Path) -> dict[str, pd.DataFrame]:
    base = Path(base_dir)
    return {
        "fact_pipeline_monthly": pd.read_csv(base / "fact_pipeline_monthly.csv"),
        "dim_project_priority": pd.read_csv(base / "dim_project_priority.csv"),
        "fact_integrated_risk": pd.read_csv(base / "fact_integrated_risk.csv"),
        "fact_planner_actions": pd.read_csv(base / "fact_planner_actions.csv"),
    }


def _quarter_id_from_date(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce")
    return dt.dt.year.astype("Int64").astype(str) + "-Q" + dt.dt.quarter.astype("Int64").astype(str)


def _quarter_order(quarter_id: pd.Series) -> pd.Series:
    year = quarter_id.str.slice(0, 4).astype(int)
    quarter = quarter_id.str.extract(r"Q(\d)").astype(int)[0]
    return year * 4 + quarter


def _quarter_id_from_week(series: pd.Series) -> pd.Series:
    def convert(value: str) -> str:
        year_str, week_str = str(value).split("-W")
        return quarter_label(int(year_str), int(week_str))

    return series.map(convert)


def _scope_to_plants(dim_region_scope: pd.DataFrame) -> dict[str, list[str]]:
    scopes: dict[str, list[str]] = {}
    for row in dim_region_scope.itertuples(index=False):
        scopes[row.scope_id] = [plant for plant in str(row.included_plants).split(",") if plant]
    return scopes


def _scope_filter(df: pd.DataFrame, scope_id: str, plants: list[str]) -> pd.DataFrame:
    if scope_id == "global_reference":
        return df.copy()
    return df[df["plant"].isin(plants)].copy()


def build_dim_region_scope(fact_pipeline_monthly: pd.DataFrame) -> pd.DataFrame:
    plants = sorted(fact_pipeline_monthly["plant"].dropna().astype(str).unique().tolist())
    denmark_scope = [plant for plant in DENMARK_DEMO_PLANTS if plant in plants]
    rows = [
        {
            "scope_id": "global_reference",
            "region_name": "Global Reference",
            "included_plants": ",".join(plants),
            "included_factories_note": "All plants retained as unfiltered reference scope.",
            "scope_rule": "plant in ALL_PLANTS",
            "active_flag": False,
        },
        {
            "scope_id": "denmark_demo",
            "region_name": "Denmark Demo",
            "included_plants": ",".join(denmark_scope),
            "included_factories_note": (
                "Explicit MVP scope limited to NW08,NW09,NW10; business label only, "
                "not an ERP geography master."
            ),
            "scope_rule": "plant in ['NW08','NW09','NW10']",
            "active_flag": True,
        },
    ]
    return pd.DataFrame(rows)


def build_fact_pipeline_quarterly(
    fact_pipeline_monthly: pd.DataFrame,
    dim_region_scope: pd.DataFrame,
) -> pd.DataFrame:
    monthly = fact_pipeline_monthly.copy()
    monthly["quarter_id"] = _quarter_id_from_date(monthly["period_date"])
    monthly["requested_date"] = pd.to_datetime(monthly["requested_date"], errors="coerce")
    scoped_frames: list[pd.DataFrame] = []

    for scope_id, plants in _scope_to_plants(dim_region_scope).items():
        subset = _scope_filter(monthly, scope_id, plants)
        if subset.empty:
            continue
        agg = (
            subset.groupby(["quarter_id", "project_id", "plant", "material"], as_index=False, dropna=False)
            .agg(
                raw_qty_quarter=("raw_qty", "sum"),
                expected_qty_quarter=("expected_qty", "sum"),
                expected_value_quarter=("expected_value", "sum"),
                priority_score=("priority_score", "max"),
                requested_date_min=("requested_date", "min"),
                requested_date_max=("requested_date", "max"),
            )
        )
        agg.insert(0, "scope_id", scope_id)
        scoped_frames.append(agg)

    if not scoped_frames:
        return pd.DataFrame(
            columns=[
                "scope_id",
                "quarter_id",
                "project_id",
                "plant",
                "material",
                "raw_qty_quarter",
                "expected_qty_quarter",
                "expected_value_quarter",
                "priority_score",
                "requested_date_min",
                "requested_date_max",
            ]
        )

    out = pd.concat(scoped_frames, ignore_index=True)
    for col in ["requested_date_min", "requested_date_max"]:
        out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return out.sort_values(["scope_id", "quarter_id", "project_id", "plant", "material"]).reset_index(drop=True)


def build_fact_quarter_business_snapshot(
    fact_pipeline_monthly: pd.DataFrame,
    dim_project_priority: pd.DataFrame,
    dim_region_scope: pd.DataFrame,
) -> pd.DataFrame:
    monthly = fact_pipeline_monthly.copy()
    monthly["quarter_id"] = _quarter_id_from_date(monthly["period_date"])
    priority = dim_project_priority[
        ["project_id", "probability_score", "revenue_tier", "strategic_segment_score", "priority_score"]
    ].drop_duplicates("project_id")
    monthly = monthly.merge(priority, on="project_id", how="left", suffixes=("", "_priority"))
    monthly["project_priority_score"] = monthly["priority_score_priority"].fillna(monthly["priority_score"])
    monthly["is_high_confidence"] = monthly["probability_score"].fillna(0.0) >= 0.70
    monthly["is_strategic_project"] = (
        monthly["revenue_tier_priority"].fillna(monthly["revenue_tier"]).eq("Strategic")
        | (monthly["strategic_segment_score"].fillna(0.0) >= 0.80)
    )

    frames: list[pd.DataFrame] = []
    for scope_id, plants in _scope_to_plants(dim_region_scope).items():
        subset = _scope_filter(monthly, scope_id, plants)
        if subset.empty:
            continue
        project_quarter = (
            subset.groupby(["quarter_id", "project_id"], as_index=False)
            .agg(
                expected_qty_quarter=("expected_qty", "sum"),
                expected_value_quarter=("expected_value", "sum"),
                priority_score=("project_priority_score", "max"),
                is_high_confidence=("is_high_confidence", "max"),
                is_strategic_project=("is_strategic_project", "max"),
            )
        )
        snap = (
            project_quarter.groupby("quarter_id", as_index=False)
            .agg(
                total_projects=("project_id", "nunique"),
                total_expected_qty=("expected_qty_quarter", "sum"),
                total_expected_value=("expected_value_quarter", "sum"),
                avg_priority_score=("priority_score", "mean"),
                high_confidence_project_count=("is_high_confidence", "sum"),
                strategic_project_count=("is_strategic_project", "sum"),
            )
        )
        snap.insert(0, "scope_id", scope_id)
        frames.append(snap)

    if not frames:
        return pd.DataFrame(
            columns=[
                "scope_id",
                "quarter_id",
                "total_projects",
                "total_expected_qty",
                "total_expected_value",
                "avg_priority_score",
                "high_confidence_project_count",
                "strategic_project_count",
            ]
        )

    return pd.concat(frames, ignore_index=True).sort_values(["scope_id", "quarter_id"]).reset_index(drop=True)


def _build_project_action_catalog(fact_planner_actions: pd.DataFrame) -> pd.DataFrame:
    actions = fact_planner_actions[fact_planner_actions["scenario"] == EXPECTED_VALUE_SCENARIO].copy()
    if actions.empty:
        return pd.DataFrame(columns=["project_id", "plant", "action_type", "action_score", "previous_confidence"])

    actions["_confidence_rank"] = actions["confidence"].map(CONFIDENCE_RANK).fillna(0)
    catalog = (
        actions.groupby(["project_id", "plant", "action_type"], as_index=False)
        .agg(
            action_score=("action_score", "max"),
            confidence_rank=("_confidence_rank", "max"),
        )
    )
    catalog["previous_confidence"] = catalog["confidence_rank"].map({v: k for k, v in CONFIDENCE_RANK.items()})
    return catalog.drop(columns=["confidence_rank"])


def _choose_action_type(project_id: str, plant: str, top_driver: str, catalog: pd.DataFrame) -> tuple[object, object, object]:
    subset = catalog[(catalog["project_id"] == project_id) & (catalog["plant"] == plant)].copy()
    if subset.empty:
        return None, None, None

    preferred = DRIVER_ACTION_MAP.get(top_driver, [])
    preferred_subset = subset[subset["action_type"].isin(preferred)].copy()
    choice_pool = preferred_subset if not preferred_subset.empty else subset
    choice = choice_pool.sort_values(["action_score", "action_type"], ascending=[False, True]).iloc[0]
    return choice["action_type"], float(choice["action_score"]), choice["previous_confidence"]


def build_fact_decision_history(
    fact_pipeline_monthly: pd.DataFrame,
    fact_integrated_risk: pd.DataFrame,
    fact_planner_actions: pd.DataFrame,
    dim_region_scope: pd.DataFrame,
) -> pd.DataFrame:
    pipeline = fact_pipeline_monthly.copy()
    pipeline["quarter_id"] = _quarter_id_from_date(pipeline["period_date"])
    project_scope_quarter = (
        pipeline.groupby(["project_id", "plant", "quarter_id"], as_index=False, dropna=False)
        .agg(expected_value_quarter=("expected_value", "sum"))
    )

    risk = fact_integrated_risk[fact_integrated_risk["scenario"] == EXPECTED_VALUE_SCENARIO].copy()
    risk["quarter_id"] = _quarter_id_from_week(risk["week"])
    risk = risk.sort_values(["scenario", "project_id", "plant", "quarter_id", "action_score"], ascending=[True, True, True, True, False])
    risk_peak = risk.drop_duplicates(["project_id", "plant", "quarter_id"], keep="first")[
        ["project_id", "plant", "quarter_id", "action_score", "top_driver", "scenario_confidence"]
    ].rename(
        columns={
            "action_score": "peak_risk_action_score",
            "top_driver": "quarter_top_driver",
            "scenario_confidence": "quarter_confidence",
        }
    )
    state = project_scope_quarter.merge(risk_peak, on=["project_id", "plant", "quarter_id"], how="left")

    catalog = _build_project_action_catalog(fact_planner_actions)
    selected_action_type = []
    selected_action_score = []
    selected_action_confidence = []
    for row in state.itertuples(index=False):
        action_type, action_score, confidence = _choose_action_type(
            row.project_id,
            row.plant,
            row.quarter_top_driver if pd.notna(row.quarter_top_driver) else "",
            catalog,
        )
        selected_action_type.append(action_type)
        selected_action_score.append(action_score)
        selected_action_confidence.append(confidence)
    state["selected_action_type"] = selected_action_type
    state["selected_action_score"] = selected_action_score
    state["selected_action_confidence"] = selected_action_confidence

    frames: list[pd.DataFrame] = []
    for scope_id, plants in _scope_to_plants(dim_region_scope).items():
        subset = _scope_filter(state, scope_id, plants)
        if subset.empty:
            continue
        subset = subset.sort_values(
            ["project_id", "quarter_id", "peak_risk_action_score", "expected_value_quarter"],
            ascending=[True, True, False, False],
        )
        best = subset.drop_duplicates(["project_id", "quarter_id"], keep="first").copy()
        best["scope_id"] = scope_id
        frames.append(best)

    if not frames:
        return pd.DataFrame(
            columns=[
                "scope_id",
                "quarter_id",
                "project_id",
                "previous_action_type",
                "previous_action_score",
                "previous_top_driver",
                "previous_confidence",
                "action_outcome_status",
                "carry_over_flag",
                "learning_note",
            ]
        )

    out = pd.concat(frames, ignore_index=True)
    out["quarter_sort"] = _quarter_order(out["quarter_id"])
    out = out.sort_values(["scope_id", "project_id", "quarter_sort"]).reset_index(drop=True)

    grouped = out.groupby(["scope_id", "project_id"], group_keys=False)
    out["prev_quarter_sort"] = grouped["quarter_sort"].shift(1)
    out["prev_quarter_id"] = grouped["quarter_id"].shift(1)
    out["previous_action_type"] = grouped["selected_action_type"].shift(1)
    out["previous_action_score"] = grouped["selected_action_score"].shift(1)
    out["previous_top_driver"] = grouped["quarter_top_driver"].shift(1)
    out["previous_confidence"] = grouped["selected_action_confidence"].shift(1)
    out["carry_over_flag"] = (
        out["prev_quarter_sort"].notna() & ((out["quarter_sort"] - out["prev_quarter_sort"]) == 1)
    )
    out["action_outcome_status"] = out["carry_over_flag"].map(
        lambda flag: "pending_outcome_synth" if flag else "no_prior_decision"
    )
    out["previous_top_driver"] = out["previous_top_driver"].where(out["previous_top_driver"].notna(), None)
    out["previous_action_type"] = out["previous_action_type"].where(out["previous_action_type"].notna(), None)
    out["previous_confidence"] = out["previous_confidence"].where(out["previous_confidence"].notna(), None)

    notes = []
    for row in out.itertuples(index=False):
        if row.carry_over_flag and row.previous_action_type:
            prior_driver = row.previous_top_driver if row.previous_top_driver else "UNSPECIFIED_DRIVER"
            notes.append(
                f"history_mode=inferred_from_expected_value; prior_quarter={row.prev_quarter_id}; "
                f"prior_action={row.previous_action_type}; prior_driver={prior_driver}; "
                "outcome_label=pending_outcome_synth"
            )
        else:
            notes.append(
                "history_mode=inferred_from_expected_value; no_prior_decision; "
                "outcome_label=no_prior_decision"
            )
    out["learning_note"] = notes

    cols = [
        "scope_id",
        "quarter_id",
        "project_id",
        "previous_action_type",
        "previous_action_score",
        "previous_top_driver",
        "previous_confidence",
        "action_outcome_status",
        "carry_over_flag",
        "learning_note",
    ]
    return out[cols].drop_duplicates(["scope_id", "quarter_id", "project_id"]).reset_index(drop=True)
