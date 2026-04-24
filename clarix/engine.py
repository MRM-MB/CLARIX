"""
clarix.engine
=============
Pure-pandas engines on top of the canonical tables.

Public functions
----------------
build_demand_by_wc_week(data, scenario, *, status_filter=None, plant=None)
build_utilization(data, scenario, *, plant=None)
detect_bottlenecks(util_df, *, warn=0.85, crit=1.00)
sourcing_recommendations(data, scenario, *, top_n=20)
explain_constraint(data, work_center, year=None, week=None)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from .data_loader import CanonicalData


# -----------------------------------------------------------------------------
# Scenarios
# -----------------------------------------------------------------------------
SCENARIOS = {
    "all_in":         {"label": "All-in",          "desc": "100% of pipeline (worst case load)"},
    "expected":       {"label": "Expected value",  "desc": "qty x probability (planning baseline)"},
    "high_confidence": {"label": "High-confidence", "desc": "Only projects with probability >= 70%"},
    "monte_carlo":    {"label": "Monte Carlo light", "desc": "Stochastic draw, P50 of 200 trials"},
}


def _apply_scenario(pipe: pd.DataFrame, scenario: str, *, n_trials: int = 200, seed: int = 42) -> pd.DataFrame:
    """Return pipeline rows with a 'demand_qty' column reflecting the scenario."""
    df = pipe.copy()
    if scenario == "all_in":
        df["demand_qty"] = df["qty"]
    elif scenario == "expected":
        df["demand_qty"] = df["expected_qty"]
    elif scenario == "high_confidence":
        df["demand_qty"] = np.where(df["probability_frac"] >= 0.70, df["qty"], 0.0)
    elif scenario == "monte_carlo":
        rng = np.random.default_rng(seed)
        # Draw at the project x month level: each project either lands (prob) or doesn't.
        # P50 across n trials.
        prob = df["probability_frac"].to_numpy()
        qty = df["qty"].to_numpy()
        # Per-row median of a Bernoulli(prob) * qty over n_trials. For Bernoulli the
        # median equals qty if prob > 0.5 else 0.  Use the full sample for stability.
        draws = (rng.random((n_trials, len(prob))) < prob).astype(np.float32)
        df["demand_qty"] = (draws.mean(axis=0) * qty)
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
    return df


# -----------------------------------------------------------------------------
# Demand-to-capacity rollups
# -----------------------------------------------------------------------------
def _month_to_weeks(year: int, month: int) -> list[tuple[int, int]]:
    """Return ISO (year, week) tuples that fall inside the calendar month."""
    start = pd.Timestamp(year=year, month=month, day=1)
    end = (start + pd.offsets.MonthEnd(0))
    days = pd.date_range(start, end, freq="D")
    iso = [(int(d.isocalendar().year), int(d.isocalendar().week)) for d in days]
    seen = set()
    out = []
    for y, w in iso:
        if (y, w) not in seen:
            seen.add((y, w))
            out.append((y, w))
    return out


def build_demand_by_wc_week(
    data: CanonicalData,
    scenario: str = "expected",
    *,
    status_filter: Optional[Iterable[str]] = None,
    plant: Optional[str] = None,
) -> pd.DataFrame:
    """Return long df: (work_center, plant, year, week, demand_hours, demand_qty)."""
    pipe = data.fact_pipeline_monthly.copy()
    if pipe.empty:
        return pd.DataFrame()
    if status_filter:
        pipe = pipe[pipe["status"].isin(status_filter)]
    if plant:
        pipe = pipe[pipe["plant"] == plant]

    pipe = _apply_scenario(pipe, scenario)
    pipe = pipe[pipe["demand_qty"] > 0].copy()
    if pipe.empty:
        return pd.DataFrame(columns=["work_center", "plant", "year", "week",
                                      "demand_qty", "demand_hours"])

    # cycle time is in minutes per piece -> convert to hours per piece
    pipe["hours_per_piece"] = pd.to_numeric(pipe["cycle_time_min"], errors="coerce").fillna(0.0) / 60.0
    pipe["demand_hours_month"] = pipe["demand_qty"] * pipe["hours_per_piece"]

    # Spread monthly load evenly across the ISO weeks that overlap the month.
    expanded = []
    for (y, m), grp in pipe.groupby(["year", "month"], sort=False):
        weeks = _month_to_weeks(int(y), int(m))
        n = len(weeks)
        if n == 0:
            continue
        share = 1.0 / n
        per = grp[["work_center_full", "plant", "demand_qty", "demand_hours_month"]].copy()
        for (yy, ww) in weeks:
            tmp = per.copy()
            tmp["year"] = yy
            tmp["week"] = ww
            tmp["demand_qty"] = tmp["demand_qty"] * share
            tmp["demand_hours"] = tmp["demand_hours_month"] * share
            expanded.append(tmp)
    if not expanded:
        return pd.DataFrame()
    out = pd.concat(expanded, ignore_index=True)
    out = (out.groupby(["work_center_full", "plant", "year", "week"], as_index=False)
              [["demand_qty", "demand_hours"]].sum())
    out = out.rename(columns={"work_center_full": "work_center"})
    return out


def build_utilization(
    data: CanonicalData,
    scenario: str = "expected",
    *,
    plant: Optional[str] = None,
    status_filter: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Return (work_center, plant, year, week, demand_hours, available_hours, utilization)."""
    cap = data.fact_wc_capacity_weekly.copy()
    if cap.empty:
        return pd.DataFrame()
    if plant:
        cap = cap[cap["plant"] == plant]
    cap_grp = (cap.groupby(["work_center", "plant", "year", "week", "week_start"], as_index=False)
                  ["available_hours"].first())

    dem = build_demand_by_wc_week(data, scenario, status_filter=status_filter, plant=plant)
    if dem.empty:
        cap_grp["demand_hours"] = 0.0
        cap_grp["demand_qty"] = 0.0
    else:
        cap_grp = cap_grp.merge(dem, on=["work_center", "plant", "year", "week"], how="left")
        cap_grp["demand_hours"] = cap_grp["demand_hours"].fillna(0.0)
        cap_grp["demand_qty"] = cap_grp["demand_qty"].fillna(0.0)

    cap_grp["utilization"] = np.where(
        cap_grp["available_hours"] > 0,
        cap_grp["demand_hours"] / cap_grp["available_hours"],
        0.0,
    )
    cap_grp["status"] = pd.cut(
        cap_grp["utilization"],
        bins=[-1, 0.85, 1.00, np.inf],
        labels=["ok", "warn", "critical"],
    ).astype(str)
    return cap_grp


# -----------------------------------------------------------------------------
# Bottleneck detection
# -----------------------------------------------------------------------------
def detect_bottlenecks(util: pd.DataFrame, *, warn: float = 0.85, crit: float = 1.00) -> pd.DataFrame:
    if util.empty:
        return util
    bad = util[util["utilization"] >= warn].copy()
    if bad.empty:
        return bad
    agg = (bad.groupby(["work_center", "plant"], as_index=False)
              .agg(weeks_warn=("utilization", lambda s: int((s >= warn).sum())),
                   weeks_crit=("utilization", lambda s: int((s >= crit).sum())),
                   peak_util=("utilization", "max"),
                   total_overload_hours=(
                       "demand_hours",
                       lambda s: float(np.maximum(0, s - util.loc[s.index, "available_hours"]).sum()),
                   )))
    agg = agg.sort_values(["peak_util", "weeks_crit"], ascending=False).reset_index(drop=True)
    return agg


# -----------------------------------------------------------------------------
# Sourcing / MRP recommendations
# -----------------------------------------------------------------------------
def sourcing_recommendations(
    data: CanonicalData,
    scenario: str = "expected",
    *,
    top_n: int = 20,
    plant: Optional[str] = None,
) -> pd.DataFrame:
    """For each component: gross requirement vs ATP -> recommend purchase qty + order-by date."""
    pipe = data.fact_pipeline_monthly.copy()
    if pipe.empty:
        return pd.DataFrame()
    if plant:
        pipe = pipe[pipe["plant"] == plant]
    pipe = _apply_scenario(pipe, scenario)
    pipe = pipe[pipe["demand_qty"] > 0]
    if pipe.empty:
        return pd.DataFrame()

    # gross requirement of finished material per month
    fin = (pipe.groupby(["plant", "material", "year", "month", "period_date"], as_index=False)
               ["demand_qty"].sum()
               .rename(columns={"material": "header_material", "demand_qty": "fg_demand_qty"}))

    bom = data.fact_finished_to_component.copy()
    if bom.empty:
        return pd.DataFrame()
    if "qty_per_effective" in bom.columns:
        bom = bom.drop(columns=[c for c in ["qty_per"] if c in bom.columns])
        bom = bom.rename(columns={"qty_per_effective": "qty_per"})

    comp_req = fin.merge(bom, on=["plant", "header_material"], how="inner")
    comp_req["component_demand_qty"] = comp_req["fg_demand_qty"] * comp_req["qty_per"].fillna(0.0)

    # Aggregate per component+month
    agg = (comp_req.groupby(
        ["plant", "component_material", "component_description", "lead_time_weeks",
         "year", "month", "period_date"], as_index=False)
        ["component_demand_qty"].sum())

    # ATP: take latest snapshot per component
    inv = data.fact_inventory_snapshot.copy()
    if not inv.empty:
        inv = (inv.sort_values("snapshot_date")
                  .groupby(["plant", "material"], as_index=False)
                  .tail(1)
                  .rename(columns={"material": "component_material",
                                   "atp_qty": "atp_today",
                                   "safety_stock_qty": "safety_stock"}))
        agg = agg.merge(inv[["plant", "component_material", "atp_today", "safety_stock"]],
                        on=["plant", "component_material"], how="left")
    else:
        agg["atp_today"] = 0.0
        agg["safety_stock"] = 0.0

    agg["atp_today"] = agg["atp_today"].fillna(0.0)
    agg["safety_stock"] = agg["safety_stock"].fillna(0.0)
    agg["lead_time_weeks"] = pd.to_numeric(agg["lead_time_weeks"], errors="coerce").fillna(0.0)

    # Running inventory by component along time
    agg = agg.sort_values(["plant", "component_material", "period_date"]).reset_index(drop=True)
    agg["cumulative_demand"] = agg.groupby(["plant", "component_material"])["component_demand_qty"].cumsum()
    agg["projected_atp"] = agg["atp_today"] - agg["cumulative_demand"]
    agg["shortfall"] = np.maximum(0.0, agg["safety_stock"] - agg["projected_atp"])
    agg["order_by"] = agg["period_date"] - pd.to_timedelta(agg["lead_time_weeks"] * 7, unit="D")

    rec = agg[agg["shortfall"] > 0].copy()
    if rec.empty:
        return rec
    rec = rec.sort_values(["order_by", "shortfall"], ascending=[True, False])
    return rec.head(top_n).reset_index(drop=True)


# -----------------------------------------------------------------------------
# Explain a single constraint (used by Claude tool)
# -----------------------------------------------------------------------------
def explain_constraint(
    data: CanonicalData,
    work_center: str,
    *,
    scenario: str = "expected",
    year: Optional[int] = None,
    week: Optional[int] = None,
) -> dict:
    util = build_utilization(data, scenario)
    if util.empty:
        return {"error": "no utilization data"}
    sub = util[util["work_center"] == work_center]
    if year:
        sub = sub[sub["year"] == year]
    if week:
        sub = sub[sub["week"] == week]
    if sub.empty:
        return {"error": f"work_center {work_center} not found"}
    row = sub.sort_values("utilization", ascending=False).iloc[0]

    # Contributing projects in that month
    pipe = _apply_scenario(data.fact_pipeline_monthly, scenario)
    pipe = pipe[(pipe["work_center_full"] == work_center) & (pipe["year"] == int(row["year"]))]
    pipe["hours"] = pipe["demand_qty"] * pd.to_numeric(pipe["cycle_time_min"], errors="coerce").fillna(0) / 60.0
    contrib = (pipe.groupby(["project_name", "material", "material_description"], as_index=False)
                   ["hours"].sum()
                   .sort_values("hours", ascending=False)
                   .head(5))

    return {
        "work_center": work_center,
        "plant": str(row["plant"]),
        "year": int(row["year"]),
        "week": int(row["week"]),
        "available_hours": float(row["available_hours"]),
        "demand_hours": float(row["demand_hours"]),
        "utilization": float(row["utilization"]),
        "status": str(row["status"]),
        "top_projects": contrib.to_dict(orient="records"),
    }


# =============================================================================
# What-if planner: add hypothetical projects and re-score capacity
# =============================================================================
def quarter_label(year: int, week: int) -> str:
    """Map ISO (year, week) -> 'YYYY-Qn'."""
    try:
        d = pd.Timestamp.fromisocalendar(int(year), int(week), 1)
    except Exception:
        return f"{year}-Q?"
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def quarter_to_month(year: int, q: int) -> pd.Timestamp:
    """Quarter Q1..Q4 -> first month of quarter (Jan / Apr / Jul / Oct)."""
    return pd.Timestamp(year=int(year), month=(int(q) - 1) * 3 + 1, day=1)


def list_addable_materials(data: CanonicalData, plant: str) -> pd.DataFrame:
    """Materials that have a tool/work-center mapping at this plant."""
    br = data.bridge_material_tool_wc
    if br.empty or "plant" not in br.columns:
        return pd.DataFrame(columns=["material", "material_description"])
    sub = br[br["plant"] == plant].copy()
    if sub.empty:
        return pd.DataFrame(columns=["material", "material_description"])
    desc_col = "material_description" if "material_description" in sub.columns else None
    out = sub[["material"] + ([desc_col] if desc_col else [])].drop_duplicates("material")
    if desc_col is None:
        out["material_description"] = ""
    return out.sort_values("material").reset_index(drop=True)


def _basket_to_pipeline_rows(data: CanonicalData, basket: list[dict]) -> pd.DataFrame:
    """Expand each basket project into pipeline-shaped rows (one per matching tool/WC)."""
    if not basket:
        return pd.DataFrame()
    br = data.bridge_material_tool_wc
    if br.empty:
        return pd.DataFrame()

    rows = []
    for item in basket:
        plant = item.get("plant")
        material = item.get("material")
        period_date = pd.Timestamp(item.get("period_date"))
        qty_total = float(item.get("qty", 0))
        prob = float(item.get("probability_frac", 1.0))
        proj_name = item.get("project_name", "WHATIF")
        n_months = max(1, int(item.get("spread_months", 3)))

        match = br[(br["plant"] == plant) & (br["material"] == material)]
        if match.empty:
            continue
        per_month_qty = qty_total / n_months
        for k in range(n_months):
            month_start = (period_date + pd.offsets.MonthBegin(k))
            for _, mr in match.iterrows():
                wc = mr.get("work_center")
                wc_full = mr.get("work_center_full") or (
                    f"P01_{plant}_{wc}" if wc else None
                )
                if not wc_full:
                    continue
                rows.append({
                    "status": "Open",
                    "material": material,
                    "material_description": mr.get("material_description", ""),
                    "cycle_time_min": mr.get("cycle_time_min", 0.0),
                    "work_center": wc,
                    "tool": mr.get("tool"),
                    "project_name": proj_name,
                    "plant_name": f"P01_{plant}_WHATIF",
                    "type": item.get("type", "What-if"),
                    "qty": per_month_qty,
                    "year": int(month_start.year),
                    "month": int(month_start.month),
                    "period_date": month_start,
                    "plant": plant,
                    "work_center_full": wc_full,
                    "probability": prob * 100.0,
                    "probability_frac": prob,
                    "expected_qty": per_month_qty * prob,
                })
    return pd.DataFrame(rows)


def build_utilization_with_basket(
    data: CanonicalData,
    scenario: str,
    *,
    basket: Optional[list[dict]] = None,
    plant: Optional[str] = None,
) -> pd.DataFrame:
    """build_utilization() with extra synthetic pipeline rows merged in."""
    if not basket:
        return build_utilization(data, scenario, plant=plant)
    extra = _basket_to_pipeline_rows(data, basket)
    if extra.empty:
        return build_utilization(data, scenario, plant=plant)

    import dataclasses
    new_pipe = pd.concat([data.fact_pipeline_monthly, extra], ignore_index=True, sort=False)
    new_data = dataclasses.replace(data, fact_pipeline_monthly=new_pipe)
    return build_utilization(new_data, scenario, plant=plant)


def project_feasibility(
    data: CanonicalData,
    scenario: str,
    basket: list[dict],
    *,
    plant: Optional[str] = None,
) -> dict:
    """Run a feasibility check for a basket of projects against existing committed load."""
    if not basket:
        return {"per_project": [], "per_quarter": pd.DataFrame(), "summary": {}}

    base = build_utilization(data, scenario, plant=plant).copy()
    after = build_utilization_with_basket(data, scenario, basket=basket, plant=plant).copy()
    if after.empty:
        return {"per_project": [], "per_quarter": pd.DataFrame(), "summary": {}}

    for df in (base, after):
        df["quarter"] = [quarter_label(int(y), int(w))
                         for y, w in zip(df["year"], df["week"])]

    verdicts = []
    for item in basket:
        only = build_utilization_with_basket(
            data, scenario, basket=[item], plant=item.get("plant") or plant
        )
        proj_q_year = pd.Timestamp(item.get("period_date")).year
        proj_q_q = (pd.Timestamp(item.get("period_date")).month - 1) // 3 + 1
        proj_quarter = f"{proj_q_year}-Q{proj_q_q}"

        if only.empty:
            verdicts.append({"project": item.get("project_name"),
                             "plant": item.get("plant"),
                             "material": item.get("material"),
                             "quarter": proj_quarter,
                             "status": "no_route",
                             "peak_util_after": 0.0, "peak_util_before": 0.0,
                             "worst_wc": "n/a",
                             "headroom_h": 0.0, "marginal_h": 0.0})
            continue

        only["quarter"] = [quarter_label(int(y), int(w))
                           for y, w in zip(only["year"], only["week"])]
        target_q = set(only["quarter"].unique())
        a = after[after["quarter"].isin(target_q)]
        b = base[base["quarter"].isin(target_q)]
        if a.empty:
            verdicts.append({"project": item.get("project_name"),
                             "plant": item.get("plant"),
                             "material": item.get("material"),
                             "quarter": proj_quarter,
                             "status": "no_capacity_data",
                             "peak_util_after": 0.0, "peak_util_before": 0.0,
                             "worst_wc": "n/a",
                             "headroom_h": 0.0,
                             "marginal_h": float(only["demand_hours"].sum())})
            continue

        worst_row = a.loc[a["utilization"].idxmax()]
        worst_wc = worst_row["work_center"]
        peak_after = float(worst_row["utilization"])
        peak_before = float(b[b["work_center"] == worst_wc]["utilization"].max() or 0.0)
        marginal_h = float(only["demand_hours"].sum())
        wc_in_q = a[a["work_center"] == worst_wc]
        headroom_h = float((wc_in_q["available_hours"] - wc_in_q["demand_hours"]).clip(lower=0).sum())

        if peak_after >= 1.0:
            status = "infeasible"
        elif peak_after >= 0.85:
            status = "at_risk"
        else:
            status = "feasible"

        verdicts.append({
            "project": item.get("project_name"),
            "plant": item.get("plant"),
            "material": item.get("material"),
            "quarter": proj_quarter,
            "status": status,
            "peak_util_after": peak_after,
            "peak_util_before": peak_before,
            "worst_wc": worst_wc,
            "headroom_h": headroom_h,
            "marginal_h": marginal_h,
        })

    touched_wcs = sorted({v["worst_wc"] for v in verdicts if v.get("worst_wc") not in (None, "n/a")})
    per_quarter = pd.DataFrame()
    if touched_wcs:
        a = (after[after["work_center"].isin(touched_wcs)]
             .groupby(["work_center", "quarter"], as_index=False)["utilization"].max()
             .rename(columns={"utilization": "peak_after"}))
        b = (base[base["work_center"].isin(touched_wcs)]
             .groupby(["work_center", "quarter"], as_index=False)["utilization"].max()
             .rename(columns={"utilization": "peak_before"}))
        per_quarter = a.merge(b, on=["work_center", "quarter"], how="left").fillna(0)
        per_quarter["delta_pp"] = (per_quarter["peak_after"] - per_quarter["peak_before"]) * 100.0
        per_quarter = per_quarter.sort_values(["work_center", "quarter"]).reset_index(drop=True)

    n_feas = sum(1 for v in verdicts if v["status"] == "feasible")
    n_risk = sum(1 for v in verdicts if v["status"] == "at_risk")
    n_inf = sum(1 for v in verdicts if v["status"] in ("infeasible", "no_capacity_data", "no_route"))
    overload_added_h = float(
        (after["demand_hours"] - after["available_hours"]).clip(lower=0).sum()
        - (base["demand_hours"] - base["available_hours"]).clip(lower=0).sum()
    )

    return {
        "per_project": verdicts,
        "per_quarter": per_quarter,
        "summary": {
            "feasible": n_feas, "at_risk": n_risk, "infeasible": n_inf,
            "overload_hours_added": overload_added_h,
        },
    }

