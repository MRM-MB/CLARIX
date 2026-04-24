"""
clarix.data_loader
==================
Reads the Danfoss hackathon workbook ONCE and produces 6 canonical
long-format tables that every downstream engine consumes.

Canonical tables
----------------
fact_pipeline_monthly        : (project, plant, material, work_center, tool, month, qty, probability, status, type)
fact_wc_capacity_weekly      : (work_center, plant, week, year, available_hours, net_demand_qty)
fact_wc_limits_monthly       : (work_center, plant, month_num, year, ap_limit_hours, oee_pct)
bridge_material_tool_wc      : (plant, material, tool, work_center, cycle_time_min, type)
fact_inventory_snapshot      : (plant, material, ops_group, snapshot_date, atp_qty, safety_stock_qty, total_stock_value_eur)
fact_finished_to_component   : (plant, header_material, component_material, qty_per, lead_time_weeks, comp_class)
dim_project                  : (project_id, project_name, region, owner, probability, requested_delivery, segment, total_pcs, total_eur, tier)
dim_material_master          : (material, description, abc, in_house_wd, prod_lt_weeks, transport_lt_cd, planned_lt_cd, std_cost_eur, avg_price_eur)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_XLSX = Path(__file__).resolve().parent.parent / "data" / "hackathon_dataset.xlsx"

# Column name patterns
_MONTH_RE = re.compile(r"^\s*(\d{1,2})\s+(\d{4})\s*$")           # "1 2026"
_WEEK_RE = re.compile(r"^Week\s+(\d{1,2})\s+(\d{4})$")            # "Week 1 2026"
_MONTH_SHORT = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _detect_plant_from_wc(wc: str) -> str:
    """'P01_NW01_PRESS_1' -> 'NW01'."""
    if not isinstance(wc, str):
        return ""
    parts = wc.split("_")
    for p in parts:
        if p.startswith("NW") and len(p) <= 5:
            return p
    return ""


def _melt_monthly(df: pd.DataFrame, id_cols: list[str], value_name: str) -> pd.DataFrame:
    """Pivot wide '1 2026' columns to long (year, month, value)."""
    month_cols = [c for c in df.columns if isinstance(c, str) and _MONTH_RE.match(c)]
    if not month_cols:
        return pd.DataFrame()
    long = df[id_cols + month_cols].melt(id_vars=id_cols, var_name="period", value_name=value_name)
    parsed = long["period"].str.extract(_MONTH_RE.pattern)
    long["month"] = parsed[0].astype(int)
    long["year"] = parsed[1].astype(int)
    long["period_date"] = pd.to_datetime(
        long["year"].astype(str) + "-" + long["month"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )
    long = long.drop(columns=["period"])
    long[value_name] = pd.to_numeric(long[value_name], errors="coerce").fillna(0.0)
    return long


def _melt_weekly(df: pd.DataFrame, id_cols: list[str], value_name: str) -> pd.DataFrame:
    week_cols = [c for c in df.columns if isinstance(c, str) and _WEEK_RE.match(c)]
    if not week_cols:
        return pd.DataFrame()
    long = df[id_cols + week_cols].melt(id_vars=id_cols, var_name="period", value_name=value_name)
    parsed = long["period"].str.extract(_WEEK_RE.pattern)
    long["week"] = parsed[0].astype(int)
    long["year"] = parsed[1].astype(int)
    long = long.drop(columns=["period"])
    long[value_name] = pd.to_numeric(long[value_name], errors="coerce").fillna(0.0)
    return long


# -----------------------------------------------------------------------------
# Container
# -----------------------------------------------------------------------------
@dataclass
class CanonicalData:
    fact_pipeline_monthly: pd.DataFrame = field(default_factory=pd.DataFrame)
    fact_wc_capacity_weekly: pd.DataFrame = field(default_factory=pd.DataFrame)
    fact_wc_limits_monthly: pd.DataFrame = field(default_factory=pd.DataFrame)
    bridge_material_tool_wc: pd.DataFrame = field(default_factory=pd.DataFrame)
    fact_inventory_snapshot: pd.DataFrame = field(default_factory=pd.DataFrame)
    fact_finished_to_component: pd.DataFrame = field(default_factory=pd.DataFrame)
    dim_project: pd.DataFrame = field(default_factory=pd.DataFrame)
    dim_material_master: pd.DataFrame = field(default_factory=pd.DataFrame)

    def summary(self) -> dict:
        return {k: int(getattr(self, k).shape[0]) for k in self.__dataclass_fields__}


# -----------------------------------------------------------------------------
# Sheet builders
# -----------------------------------------------------------------------------
def _build_pipeline(plates: pd.DataFrame, gaskets: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for src_df, kind, factory_col in [
        (plates, "Plate", "Plate Factory"),
        (gaskets, "Gasket", "Gasket Factory"),
    ]:
        if src_df.empty:
            continue
        keep = ["Status", "Material number", "Material Description", "Cycle time",
                "Work center", "Tool number", "Project_name", factory_col]
        keep = [c for c in keep if c in src_df.columns]
        df = src_df[keep].copy()
        df["type"] = kind
        df = df.rename(columns={
            "Material number": "material",
            "Material Description": "material_description",
            "Cycle time": "cycle_time_min",
            "Work center": "work_center",
            "Tool number": "tool",
            "Project_name": "project_name",
            "Status": "status",
            factory_col: "plant_name",
        })
        # melt months
        month_cols = [c for c in src_df.columns if isinstance(c, str) and _MONTH_RE.match(c)]
        wide = pd.concat([df, src_df[month_cols].reset_index(drop=True)], axis=1)
        long = _melt_monthly(
            wide,
            id_cols=["status", "material", "material_description", "cycle_time_min",
                     "work_center", "tool", "project_name", "plant_name", "type"],
            value_name="qty",
        )
        # Plant name like 'P01_NW13_Northwind Andes' -> 'NW13'
        long["plant"] = long["plant_name"].astype(str).str.extract(r"(NW\d{2})")
        long["work_center_full"] = (
            "P01_" + long["plant"].fillna("") + "_" + long["work_center"].astype(str)
        )
        rows.append(long)

    pipeline = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if pipeline.empty:
        return pipeline

    # Attach probability + project metadata
    if not projects.empty and "Project name" in projects.columns:
        proj = projects.rename(columns={
            "Project name": "project_name",
            "Project ID": "project_id",
            "Probability": "probability",
            "Region": "region",
            "Customer segment": "segment",
            "Revenue tier": "revenue_tier",
        })
        cols = [c for c in ["project_name", "project_id", "probability", "region",
                             "segment", "revenue_tier", "Requested delivery date"] if c in proj.columns]
        pipeline = pipeline.merge(proj[cols], on="project_name", how="left")

    pipeline["probability"] = pd.to_numeric(pipeline.get("probability"), errors="coerce")
    # Probability: convert to fraction (sheet stores as percent like 10, 50)
    pipeline["probability_frac"] = (pipeline["probability"] / 100.0).clip(0, 1).fillna(0.5)
    pipeline["expected_qty"] = pipeline["qty"] * pipeline["probability_frac"]
    return pipeline


def _build_wc_capacity(cap_df: pd.DataFrame) -> pd.DataFrame:
    if cap_df.empty:
        return pd.DataFrame()
    # split available vs net demand
    long = _melt_weekly(cap_df, id_cols=["Work center code", "Measure"], value_name="value")
    if long.empty:
        return pd.DataFrame()
    long = long.rename(columns={"Work center code": "work_center"})
    long["plant"] = long["work_center"].map(_detect_plant_from_wc)
    avail = (long[long["Measure"].str.contains("Available", na=False)]
             .rename(columns={"value": "available_hours"})
             .drop(columns=["Measure"]))
    demand = (long[long["Measure"].str.contains("Net Demand", na=False)]
              .rename(columns={"value": "baseline_demand_qty"})
              .drop(columns=["Measure"]))
    out = avail.merge(demand, on=["work_center", "plant", "week", "year"], how="outer")
    out["available_hours"] = out["available_hours"].fillna(0.0)
    out["baseline_demand_qty"] = out["baseline_demand_qty"].fillna(0.0)
    # ISO week start date (Monday)
    out["week_start"] = pd.to_datetime(
        out["year"].astype(str) + "-W" + out["week"].astype(str).str.zfill(2) + "-1",
        format="%G-W%V-%u", errors="coerce",
    )
    return out


def _build_wc_limits(limits: pd.DataFrame) -> pd.DataFrame:
    if limits.empty:
        return pd.DataFrame()
    keep = ["WC Schedule Label", "Plant", "Plant name", "WC-Description", "OEE (in %)",
            "AP Limit time (in H)"] + _MONTH_SHORT
    keep = [c for c in keep if c in limits.columns]
    df = limits[keep].copy().rename(columns={
        "Plant": "plant",
        "Plant name": "plant_name",
        "WC-Description": "wc_description",
        "OEE (in %)": "oee_pct",
        "AP Limit time (in H)": "ap_limit_hours_default",
    })
    df["work_center_short"] = df["wc_description"]
    long = df.melt(
        id_vars=["plant", "plant_name", "work_center_short", "oee_pct", "ap_limit_hours_default"],
        value_vars=[m for m in _MONTH_SHORT if m in df.columns],
        var_name="month_label", value_name="ap_limit_hours",
    )
    long["month"] = long["month_label"].map({m: i + 1 for i, m in enumerate(_MONTH_SHORT)})
    long["ap_limit_hours"] = pd.to_numeric(long["ap_limit_hours"], errors="coerce").fillna(0.0)
    return long


def _build_tool_master(tool: pd.DataFrame) -> pd.DataFrame:
    if tool.empty:
        return pd.DataFrame()
    df = tool.rename(columns={
        "Plant": "plant",
        "Sap code": "material",
        "Type": "type",
        "Tool No.": "tool",
        "Work center": "work_center_short",
        "Cycle times Standard Value (Machine)": "cycle_time_min",
        "Material Status": "material_status",
    })
    cols = [c for c in ["plant", "material", "type", "tool", "work_center_short",
                         "cycle_time_min", "material_status"] if c in df.columns]
    return df[cols].copy()


def _build_inventory(inv: pd.DataFrame) -> pd.DataFrame:
    if inv.empty:
        return pd.DataFrame()
    df = inv.rename(columns={
        "Plant (code)": "plant",
        "Plant (name)": "plant_name",
        "Calendar day": "snapshot_date",
        "Operation Group": "ops_group",
        "Material Unique (code)": "material",
        "Material Unique (name)": "material_description",
        "Stock Qty": "stock_qty",
        "ATP Quantity": "atp_qty",
        "Safety Stock Qty": "safety_stock_qty",
        "Stock in Transit Qty": "in_transit_qty",
        "Total Stock Value (EUR)": "total_stock_value_eur",
    })
    cols = [c for c in ["plant", "plant_name", "snapshot_date", "ops_group", "material",
                         "material_description", "stock_qty", "atp_qty", "safety_stock_qty",
                         "in_transit_qty", "total_stock_value_eur"] if c in df.columns]
    df = df[cols].copy()
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
    return df


def _build_bom(bom: pd.DataFrame) -> pd.DataFrame:
    if bom.empty:
        return pd.DataFrame()
    df = bom.rename(columns={
        "Plant": "plant",
        "Header Material code": "header_material",
        "Component Material code": "component_material",
        "Effective Component Quantity": "qty_per_effective",
        "Component Quantity": "qty_per",
        "Production LT in Weeks": "lead_time_weeks",
        "Comp Plate/Gasket": "comp_class",
        "Component Description": "component_description",
        "BOM Status": "bom_status",
    })
    cols = [c for c in ["plant", "header_material", "component_material", "qty_per",
                         "qty_per_effective", "lead_time_weeks", "comp_class",
                         "component_description", "bom_status"] if c in df.columns]
    return df[cols].copy()


def _build_project_dim(projects: pd.DataFrame) -> pd.DataFrame:
    if projects.empty:
        return pd.DataFrame()
    df = projects.rename(columns={
        "Project name": "project_name",
        "Project ID": "project_id",
        "Probability": "probability_pct",
        "Region": "region",
        "Owner": "owner",
        "Requested delivery date": "requested_delivery",
        "Customer segment": "segment",
        "Total expected PCS": "total_pcs",
        "Total expected EUR": "total_eur",
        "Revenue tier": "revenue_tier",
        "Status": "status",
    })
    cols = [c for c in ["project_name", "project_id", "probability_pct", "region", "owner",
                         "requested_delivery", "segment", "total_pcs", "total_eur",
                         "revenue_tier", "status"] if c in df.columns]
    df = df[cols].copy()
    df["probability_frac"] = pd.to_numeric(df["probability_pct"], errors="coerce") / 100.0
    df["requested_delivery"] = pd.to_datetime(df["requested_delivery"], errors="coerce")
    return df


def _build_material_master(sap: pd.DataFrame) -> pd.DataFrame:
    if sap.empty:
        return pd.DataFrame()
    df = sap.rename(columns={
        "Sap code": "material",
        "Description": "description",
        "ABC (SAP)": "abc",
        "In House Production Time (WD)": "in_house_wd",
        "Production LT Weeks": "prod_lt_weeks",
        "Transportation Lanes Lead Time (CD)": "transport_lt_cd",
        "Planned Delivery Time (MARC) (CD)": "planned_lt_cd",
        "Standard Cost in EUR": "std_cost_eur",
        "Avg Sales Price in EUR": "avg_price_eur",
        "Procurement Type": "procurement_type",
    })
    cols = [c for c in ["material", "description", "abc", "in_house_wd", "prod_lt_weeks",
                         "transport_lt_cd", "planned_lt_cd", "std_cost_eur", "avg_price_eur",
                         "procurement_type"] if c in df.columns]
    return df[cols].copy()


# -----------------------------------------------------------------------------
# Public entry point
# -----------------------------------------------------------------------------
@lru_cache(maxsize=4)
def load_canonical(xlsx_path: str | Path = DEFAULT_XLSX, *, use_cache: bool = True) -> CanonicalData:
    """Load the workbook and build all canonical tables. Cached on disk as parquet."""
    xlsx_path = Path(xlsx_path)
    cache_dir = xlsx_path.parent / ".clarix_cache"
    table_names = list(CanonicalData.__dataclass_fields__.keys())

    if use_cache and cache_dir.exists() and all((cache_dir / f"{n}.parquet").exists() for n in table_names):
        if cache_dir.stat().st_mtime >= xlsx_path.stat().st_mtime:
            data = CanonicalData()
            for n in table_names:
                setattr(data, n, pd.read_parquet(cache_dir / f"{n}.parquet"))
            return data

    xl = pd.ExcelFile(xlsx_path)

    def _read(name: str) -> pd.DataFrame:
        try:
            return pd.read_excel(xl, name)
        except Exception:
            return pd.DataFrame()

    plates = _read("1_1 Export Plates")
    gaskets = _read("1_2 Gaskets")
    projects = _read("1_3 Export Project list")
    cap = _read("2_1 Work Center Capacity Weekly")
    sap = _read("2_3 SAP MasterData")
    limits = _read("2_5 WC Schedule_limits")
    tool = _read("2_6 Tool_material nr master")
    inv = _read("3_1 Inventory ATP")
    bom = _read("3_2 Component_SF_RM")

    data = CanonicalData(
        fact_pipeline_monthly=_build_pipeline(plates, gaskets, projects),
        fact_wc_capacity_weekly=_build_wc_capacity(cap),
        fact_wc_limits_monthly=_build_wc_limits(limits),
        bridge_material_tool_wc=_build_tool_master(tool),
        fact_inventory_snapshot=_build_inventory(inv),
        fact_finished_to_component=_build_bom(bom),
        dim_project=_build_project_dim(projects),
        dim_material_master=_build_material_master(sap),
    )

    cache_dir.mkdir(exist_ok=True)
    for n in table_names:
        df = getattr(data, n)
        try:
            df.to_parquet(cache_dir / f"{n}.parquet", index=False)
        except Exception:
            # parquet may fail if pyarrow missing; fall back silently
            pass
    return data
