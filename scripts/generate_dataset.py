"""Generate the anonymized Predictive Manufacturing hackathon dataset.

Produces `hackathon_starter/data/hackathon_dataset.xlsx` — a clean,
analysis-ready workbook mirroring the structure of Danfoss's real SIOP
export but with single-row headers, no preamble rows, and no blank
leading columns.

Cleaning methodology
--------------------
Applied per-sheet using the same conventions documented in the Predictive
Manufacturing project's `data/DATA_DICTIONARY.md`:

- 1_1 / 1_2: row 1 is the header; year/month padding rows removed.
- 1_2: `Plate Factory/Final/Description` renamed to `Gasket *` (fixes
  the template copy mistake from the real export).
- Typo fix: `Material Descritpion` renamed to `Material Description`.
- 2_1: row 1 is the header (refresh-timestamp preamble removed); blank
  leading column removed; work-center column named `Work center code`.
- 2_2: sheet name is `2_2 OPS plan per material` (no trailing space);
  title row `Operations Plan Final` dropped.
- 2_3: first column explicitly named `Sap code` instead of `Unnamed: 0`.
- 2_4: row 1 is the header (Anaplan refresh metadata dropped).
- 2_5: row 1 is the header (35-row preamble dropped); blank col A dropped.
- 2_6: row 1 is the header (source-labels row `Internal / Routing CDS /
  Anaplan / MARC CDS` dropped).
- 3_1: row 1 is the header (`EUR` currency row merged into value-column
  names, e.g., `Stock Value (EUR)`).
- Hidden SAP metadata sheet and `Sheet3` working-copy dropped entirely.
- `Savings per area` dropped (out of scope for capacity/sourcing).

Authentic data-quality features preserved
-----------------------------------------
- `_` missing connectors and `Missing CT` / `Missing WC` / `Missing tool`
  placeholder strings in 1_1 / 1_2 (master-data gaps).
- Rev no drift: the same material code can carry different Rev no's at
  different plants.
- Occasional `#N/A` values in 2_6.`Work center`.
- Tool-level scheduling conflicts: multiple pipeline projects targeting
  the same (plant, tool, month).
- Cross-plant tool identity: the same tool number appears at multiple
  plants so substitution analysis has something to find.
- Sparse monthly demand in 1_1/1_2 (not every month has volume).
- Dual-unit reporting hooks: 2_1 exposes both FOP hours and FOP qty so
  a pieces-per-hour rate is derivable per WC.
- Plant-specific cycle times for the same material (±25% variation).
- Five shift levels per WC with OEE and break discounts (2_5).

Scale
-----
Tuned to land at ~50-65% of the real export row counts where the
5-plant anonymization constraint permits.
"""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

# ── Reproducibility ──────────────────────────────────────────────

SEED = 20260418
random.seed(SEED)
np.random.seed(SEED)

# ── Anonymized topology ─────────────────────────────────────────

PLANTS = [
    ("NW01", "Northwind Midwest",     "North America"),
    ("NW02", "Northwind Heartland",   "Europe West"),
    ("NW03", "Northwind Carpathia",   "Europe East"),
    ("NW04", "Northwind Southbay",    "South Asia"),
    ("NW05", "Northwind Pacific",     "East Asia"),
    ("NW06", "Northwind Southeast",   "North America"),
    ("NW07", "Northwind West Coast",  "North America"),
    ("NW08", "Northwind Iberia",      "Europe West"),
    ("NW09", "Northwind Alpine",      "Europe West"),
    ("NW10", "Northwind Baltics",     "Europe East"),
    ("NW11", "Northwind Levant",      "MENA"),
    ("NW12", "Northwind Cerrado",     "South America"),
    ("NW13", "Northwind Andes",       "South America"),
    ("NW14", "Northwind Oceania",     "Oceania"),
    ("NW15", "Northwind Indochina",   "Southeast Asia"),
]
PLANT_CODES = [p[0] for p in PLANTS]
PLANT_NAME = {code: name for code, name, _ in PLANTS}

# Work-center portfolio per plant. Each tuple:
#   (wc_short, wc_long, caliber, hours_per_day, days_per_week, OEE, daily_breaks_H)
# Scaled up to ~80 WCs total (real: ~126).
def _wc_portfolio() -> dict[str, list[tuple]]:
    portfolio: dict[str, list[tuple]] = {p: [] for p in PLANT_CODES}
    # Press rosters per plant. 15 plants × ~7-10 WCs each ≈ 130 WCs (close to real 126).
    # Use standard PRESS_N naming everywhere EXCEPT NW03 which retains the PRES_ quirk.
    presses = {
        "NW01": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 8000T", "M"),
                 ("PRESS_5", "Press 11000T", "L"), ("PRESS_6", "Press 13900T", "L")],
        "NW02": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 3300T", "S"),
                 ("PRESS_3", "Press 5500T", "M"), ("PRESS_4", "Press 8000T", "M"),
                 ("PRESS_5", "Press 11000T", "L"), ("PRESS_6", "Press 13900T", "L")],
        "NW03": [("PRES_3_1", "Press 3300T", "S"), ("PRES_3_2", "Press 3300T", "S"),
                 ("PRES_4",   "Press 5500T", "M"), ("PRES_7_1", "Press 8000T", "M"),
                 ("PRES_8_1", "Press 13900T", "L")],
        "NW04": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 11000T", "L"),
                 ("PRESS_5", "Press 13900T", "L")],
        "NW05": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 3300T", "S"),
                 ("PRESS_3", "Press 5500T", "M"), ("PRESS_4", "Press 8000T", "M"),
                 ("PRESS_5", "Press 11000T", "L"), ("PRESS_6", "Press 13900T", "L")],
        "NW06": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 13900T", "L")],
        "NW07": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 3300T", "S"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 11000T", "L"),
                 ("PRESS_5", "Press 13900T", "L")],
        "NW08": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 13900T", "L")],
        "NW09": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 11000T", "L")],
        "NW10": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 13900T", "L")],
        "NW11": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 11000T", "L")],
        "NW12": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M")],
        "NW13": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 13900T", "L")],
        "NW14": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M")],
        "NW15": [("PRESS_1", "Press 3300T", "S"), ("PRESS_2", "Press 5500T", "M"),
                 ("PRESS_3", "Press 8000T", "M"), ("PRESS_4", "Press 11000T", "L"),
                 ("PRESS_5", "Press 13900T", "L")],
    }
    # Shift pattern per plant (Hours/Day, Days/Week, OEE, Breaks_H/day) — reflects regional norms
    shift = {
        "NW01": (12, 5, 0.80, 1.0), "NW02": (8,  5, 0.82, 1.0), "NW03": (12, 6, 0.76, 1.5),
        "NW04": (12, 6, 0.75, 1.0), "NW05": (8,  5, 0.85, 1.0), "NW06": (12, 5, 0.78, 1.0),
        "NW07": (8,  5, 0.83, 1.0), "NW08": (8,  5, 0.80, 1.0), "NW09": (12, 5, 0.78, 1.0),
        "NW10": (12, 5, 0.77, 1.5), "NW11": (12, 6, 0.73, 1.5), "NW12": (8,  5, 0.74, 1.0),
        "NW13": (8,  5, 0.76, 1.0), "NW14": (8,  5, 0.82, 1.0), "NW15": (12, 6, 0.74, 1.5),
    }
    # Ancillary lines (extrusion/grinding/lathe/oven/assembly) — 2-4 per plant
    extras_by_plant = {
        "NW01": [("EXTRUSION_1", "Extrusion line A", "M"), ("GRINDING_1", "Grinding line", "S"),
                 ("ASSY_1", "Assembly cell 1", "S")],
        "NW02": [("EXTRUSION_1", "Extrusion line A", "M"), ("GRINDING_1", "Grinding line", "S"),
                 ("LATHE_1", "Lathe cell", "S"), ("ASSY_1", "Assembly cell", "S")],
        "NW03": [("EXTRUSION_1", "Extrusion line A", "M"), ("GRINDING_1", "Grinding line", "S"),
                 ("OVEN_1", "Curing oven", "M")],
        "NW04": [("GRINDING_1", "Grinding line", "S"), ("ASSY_1", "Assembly cell", "S")],
        "NW05": [("EXTRUSION_1", "Extrusion line A", "M"), ("GRINDING_1", "Grinding line", "S"),
                 ("OVEN_1", "Curing oven", "M"), ("ASSY_1", "Assembly cell", "S")],
        "NW06": [("GRINDING_1", "Grinding line", "S"), ("ASSY_1", "Assembly cell", "S")],
        "NW07": [("EXTRUSION_1", "Extrusion line A", "M"), ("GRINDING_1", "Grinding line", "S"),
                 ("ASSY_1", "Assembly cell", "S")],
        "NW08": [("GRINDING_1", "Grinding line", "S"), ("ASSY_1", "Assembly cell", "S")],
        "NW09": [("EXTRUSION_1", "Extrusion line A", "M"), ("GRINDING_1", "Grinding line", "S")],
        "NW10": [("GRINDING_1", "Grinding line", "S"), ("LATHE_1", "Lathe cell", "S"),
                 ("ASSY_1", "Assembly cell", "S")],
        "NW11": [("GRINDING_1", "Grinding line", "S"), ("ASSY_1", "Assembly cell", "S")],
        "NW12": [("GRINDING_1", "Grinding line", "S"), ("ASSY_1", "Assembly cell", "S")],
        "NW13": [("GRINDING_1", "Grinding line", "S"), ("OVEN_1", "Curing oven", "M"),
                 ("ASSY_1", "Assembly cell", "S")],
        "NW14": [("GRINDING_1", "Grinding line", "S"), ("ASSY_1", "Assembly cell", "S")],
        "NW15": [("EXTRUSION_1", "Extrusion line A", "M"), ("GRINDING_1", "Grinding line", "S"),
                 ("OVEN_1", "Curing oven", "M"), ("ASSY_1", "Assembly cell", "S")],
    }
    for plant in PLANT_CODES:
        h, d, oee, breaks = shift[plant]
        for wc_short, wc_long, cal in presses[plant]:
            # Larger presses run longer shifts to match reality
            if cal == "L":
                p_h, p_d = 24, 5
                p_breaks = 2.0
            elif cal == "M":
                p_h, p_d = h, d
                p_breaks = breaks
            else:
                p_h, p_d = h, d
                p_breaks = breaks
            portfolio[plant].append((wc_short, wc_long, cal, p_h, p_d, oee, p_breaks))
        for wc_short, wc_long, cal in extras_by_plant.get(plant, []):
            portfolio[plant].append((wc_short, wc_long, cal, h, d, oee * 0.95, breaks))
    return portfolio


WC_DEFS = _wc_portfolio()

# Horizon: 2026-2028 (36 months; ~156 weeks) — matches the real export's horizon depth.
HORIZON_YEARS = (2026, 2027, 2028)
MONTHS = [f"{m} {y}" for y in HORIZON_YEARS for m in range(1, 13)]
WEEKS = [f"Week {w} {y}" for y in HORIZON_YEARS for w in range(1, 53)]
MONTH_ABBR_COLS = [
    f"{abbr} {str(y)[2:]}"
    for y in HORIZON_YEARS
    for abbr in ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
]

# ── Materials, tools, pool construction ─────────────────────────

PLATE_FAMILIES = ["S62", "S120", "S140", "S160", "XL420", "XL520", "PRO-9X", "PRO-12X", "MX100", "MX200", "MX250", "HT80"]
GASKET_FAMILIES = ["M10-BFG", "M8-NBR", "M12-EPDM", "M6-FKM", "M20-SILI", "M14-HNBR", "M18-AFLAS", "M22-NBR"]

# Scale targets — chosen so every sheet lands near or above 50% of the real export.
N_PLATE_MATERIALS = 1500
N_GASKET_MATERIALS = 900
N_TOOLS_POOL = 700
# Plant-share: fraction of the 15 plants each material is tooled at. Dropped
# from 0.6 → 0.22 because the 3x plant count triples the tool-material row
# count at constant share; 0.22 lands 2_6 near real 10.4k rows.
PLATE_PLANT_SHARE = 0.22
GASKET_PLANT_SHARE = 0.20
N_PROJECTS_PIPELINE = 720   # appear in 1_3
N_PIPELINE_LINE_ITEMS = 360   # rows across 1_1 + 1_2 combined
# Phantom materials: planned in Anaplan (appear in 2_2) but not actively
# tooled (so absent from 2_6). Lifts 2_2 row count toward real scale without
# inflating 2_6, 2_3, 3_1, 3_2 — mirrors how real Anaplan plans reference
# legacy / not-yet-tooled material codes.
N_PHANTOM_MATERIALS_PER_PLANT = 1500


def _mat_code(i: int) -> str:
    return f"MAT-{i:06d}"

def _tool_code(i: int, suffix: str) -> str:
    return f"T-{i:05d}-{suffix}"

def _project_code(i: int, wave: str) -> str:
    return f"PRJ-{wave}-{i:04d}"


def build_master_topology() -> dict:
    """Create master material/tool/WC/plant relationships at scale."""
    rng = random.Random(SEED + 1)
    # Material pool — type + family + Rev no master
    materials = []
    for k in range(N_PLATE_MATERIALS):
        fam = PLATE_FAMILIES[k % len(PLATE_FAMILIES)]
        mat = _mat_code(100000 + k)
        thick = round(rng.uniform(0.3, 0.8), 1)
        desc = f"{fam}/PL.{k % 50 + 1:02d} 304TL {thick}mm"
        rev = rng.choice(["A", "B", "C"])
        materials.append((mat, desc, "Plates", rev, fam))
    for k in range(N_GASKET_MATERIALS):
        fam = GASKET_FAMILIES[k % len(GASKET_FAMILIES)]
        mat = _mat_code(200000 + k)
        desc = f"{fam} GASKET {k % 40 + 1:02d}"
        rev = rng.choice(["A", "B", "C", "D"])
        materials.append((mat, desc, "Gaskets", rev, fam))

    # Tool pool
    tool_pool = []
    for i in range(N_TOOLS_POOL):
        cal = rng.choices(["S", "M", "L"], weights=[3, 4, 2])[0]
        suffix = rng.choice(["A", "B", "C", "D"])
        tool_pool.append((_tool_code(70000 + i, suffix), cal))

    # Assign materials → (plant, wc, tool) at scale
    tool_materials: list[dict] = []
    for plant in PLANT_CODES:
        wcs = WC_DEFS[plant]
        for (mat, desc, mtype, rev_master, fam) in materials:
            share = PLATE_PLANT_SHARE if mtype == "Plates" else GASKET_PLANT_SHARE
            if rng.random() >= share:
                continue
            # Choose a caliber based on material family hints
            if fam.startswith("XL") or fam.startswith("HT"):
                caliber_pref = "L"
            elif mtype == "Gaskets" or fam.startswith("M"):
                caliber_pref = rng.choice(["S", "M"])
            else:
                caliber_pref = rng.choice(["S", "M", "L"])
            eligible_wcs = [wc for wc in wcs if wc[2] == caliber_pref] or wcs
            wc = rng.choice(eligible_wcs)
            # Pick tool — caliber-matched, occasionally reused across plants
            eligible_tools = [t for t in tool_pool if t[1] == wc[2]] or tool_pool
            tool = rng.choice(eligible_tools)
            # Per-plant cycle time variation — realistic ±25% spread
            base_ct = {"Plates": 1.2, "Gaskets": 0.7}[mtype]
            fam_factor = {"XL": 1.8, "HT": 1.5, "PRO": 1.3, "MX": 1.0,
                          "S62": 1.0, "S12": 1.1, "S14": 1.1, "S16": 1.15,
                          "M10": 0.8, "M8": 0.6, "M12": 0.9, "M6": 0.5,
                          "M14": 0.85, "M18": 1.0, "M20": 1.1, "M22": 0.95}
            factor = next((v for k, v in fam_factor.items() if fam.startswith(k)), 1.0)
            cycle = round(base_ct * factor * rng.uniform(0.75, 1.25), 3)
            ops_gd = int(rng.uniform(2000, 320000))
            # Occasional Rev no drift across plants (authentic master-data issue)
            rev = rev_master if rng.random() > 0.18 else rng.choice(["A", "B", "C", "D"])
            tool_materials.append({
                "plant": plant,
                "wc": wc[0],
                "wc_long": wc[1],
                "caliber": wc[2],
                "tool": tool[0],
                "mat": mat,
                "mat_desc": desc,
                "mat_type": mtype,
                "family": fam,
                "cycle_time": cycle,
                "ops_plan_gd": ops_gd,
                "rev_no": rev,
            })

    return {
        "materials": materials,
        "tool_pool": tool_pool,
        "tool_materials": tool_materials,
    }


def build_pipeline_projects(topology: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Generate pipeline demand rows for plates (1_1), gaskets (1_2), and 1_3."""
    rng = random.Random(SEED + 2)
    tm = topology["tool_materials"]

    # Larger project pool for 1_3 (independent of pipeline line items)
    project_pool = []
    for i in range(N_PROJECTS_PIPELINE):
        wave = rng.choice(["ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "OMEGA"])
        project_pool.append(_project_code(i + 1, wave))

    # Helper: ramp-up/ramp-down monthly profile
    def demand_profile(peak_month_index: int, volume: int) -> dict[str, float]:
        out = {}
        for i, m in enumerate(MONTHS):
            if i < peak_month_index - 3 or i > peak_month_index + 5:
                out[m] = 0.0
            else:
                dist = 1.0 - abs(i - peak_month_index) / 6
                v = volume * max(0.0, dist) * rng.uniform(0.75, 1.25)
                out[m] = round(v, 0) if v > 0.5 else 0.0
        return out

    def make_row(project: str, entry: dict, include_missing: bool) -> dict:
        plant = entry["plant"]
        mat = entry["mat"]
        cycle = entry["cycle_time"]
        wc = entry["wc"]
        tool = entry["tool"]
        desc = entry["mat_desc"]
        connector = f"{plant}_{mat}"
        rccp = f"{plant}_{PLANT_NAME[plant]}"
        if include_missing:
            connector = "_"
            rccp = "Missing plant"
            cycle = "Missing CT"
            wc = "Missing WC"
            tool = "Missing tool"
        peak = rng.randint(2, len(MONTHS) - 4)
        volume = rng.randint(400, 12000)
        profile = demand_profile(peak, volume)
        # Note: sheet-specific "Plate/Gasket Factory" column is named at sheet-build time
        return {
            "Status": "Not approved",
            "Connector RCCP pivot": rccp,
            "Connector Plant_Material nr": connector,
            "Material number": mat if connector != "_" else None,
            "Material Description": desc,  # cleaned: typo "Descritpion" fixed
            "Cycle time": cycle,
            "Work center": wc,
            "Tool number": tool,
            "Project_name": project,
            "__factory": f"P01_{plant}_{PLANT_NAME[plant]}" if connector != "_" else None,
            "__final": mat if connector != "_" else None,
            "__description": desc if connector != "_" else None,
            "All delayed": 0,
            **profile,
        }

    plate_rows: list[dict] = []
    gasket_rows: list[dict] = []
    line_items_per_sheet = N_PIPELINE_LINE_ITEMS // 2
    # Distribute line items across project pool
    while (len(plate_rows) + len(gasket_rows)) < N_PIPELINE_LINE_ITEMS:
        project = rng.choice(project_pool)
        entry = rng.choice(tm)
        include_missing = rng.random() < 0.06
        row = make_row(project, entry, include_missing)
        if entry["mat_type"] == "Plates" and len(plate_rows) < line_items_per_sheet:
            plate_rows.append(row)
        elif entry["mat_type"] == "Gaskets" and len(gasket_rows) < line_items_per_sheet:
            gasket_rows.append(row)
        elif len(plate_rows) < line_items_per_sheet:
            plate_rows.append(row)
        elif len(gasket_rows) < line_items_per_sheet:
            gasket_rows.append(row)

    # Force tool-level conflicts: extra rows all targeting one tool
    for mtype, sink in (("Plates", plate_rows), ("Gaskets", gasket_rows)):
        candidates = [e for e in tm if e["mat_type"] == mtype]
        if not candidates:
            continue
        conflict_entry = rng.choice(candidates)
        for k in range(3):
            sink.append(make_row(rng.choice(project_pool), conflict_entry, False))

    # 1_3 Export Project list — includes projects referenced AND some not yet in 1_1/1_2
    regions = ["NA", "EMEA-West", "EMEA-East", "APAC-South", "APAC-East", "LATAM"]
    owners = ["A. Meyer", "L. Tran", "P. Kovac", "S. Iyer", "J. Park", "M. Silva", "R. Weber",
              "T. Novak", "M. Akiyama", "C. Moreau", "H. Lindqvist", "K. Suzuki"]
    segments = ["Industrial", "Refrigeration", "District Heating", "Marine", "Data Center",
                "Food & Beverage", "Oil & Gas", "Pharma"]
    project_list_rows = []
    for i, pj in enumerate(project_pool):
        project_list_rows.append({
            "Project name": pj,
            "Project ID": f"SF-{100000 + i}",
            "Region": rng.choice(regions),
            "Owner": rng.choice(owners),
            "Probability": rng.choice([10, 25, 50, 75, 90]),
            "Requested delivery date": f"2026-{rng.randint(2, 12):02d}-{rng.randint(1, 28):02d}",
            "Customer segment": rng.choice(segments),
            "Total expected PCS": rng.randint(1000, 60000),
            "Total expected EUR": round(rng.uniform(25000, 1200000), 2),
            "Revenue tier": rng.choice(["Small", "Medium", "Large", "Strategic"]),
            "Submission channel": rng.choice(["Direct", "Distributor", "Partner", "OEM"]),
            "Status": "Not approved",
            "Notes": "",
        })

    return plate_rows, gasket_rows, project_list_rows


# ── Individual sheet builders (clean, single-row-header output) ─

def build_sheet_1_1(plate_rows: list[dict]) -> pd.DataFrame:
    """1_1 Export Plates — cleaned: typo fixed, row 1 is the header."""
    df = pd.DataFrame(plate_rows)
    df = df.rename(columns={"__factory": "Plate Factory", "__final": "Plate Final", "__description": "Plate Description"})
    lead = [c for c in df.columns if c not in MONTHS]
    df = df[lead + MONTHS]
    return df


def build_sheet_1_2(gasket_rows: list[dict]) -> pd.DataFrame:
    """1_2 Gaskets — cleaned: columns correctly named Gasket * instead of Plate *."""
    df = pd.DataFrame(gasket_rows)
    df = df.rename(columns={
        "__factory": "Gasket Factory",
        "__final": "Gasket Final",
        "__description": "Gasket Description",
    })
    lead = [c for c in df.columns if c not in MONTHS]
    df = df[lead + MONTHS]
    return df


def build_sheet_1_3(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def build_sheet_2_1(topology: dict) -> pd.DataFrame:
    """2_1 Work Center Capacity Weekly — cleaned: row 1 header, no refresh-metadata preamble, no blank col A.

    First column named `Work center code`; second column named `Measure`.
    """
    measures = [
        "Available Capacity, hours",
        "Net Demand (Production Needed), qty",
        "Net Demand (Production Needed), Load in hours",
        "Net Demand (Production Needed), Capacity %",
        "Back Orders, qty",
        "Back Orders, Load in hours",
        "Net Demand + Back Orders, qty",
        "Net Demand + Back Orders, Load in hours",
        "Net Demand + Back Orders, Capacity %",
        "Final Operations Plan, qty",
        "Final Operations Plan, Load in hours",
        "Final Operations Plan, Capacity %",
        "Overload Capacity check",
        "Remaining Available Capacity, hours",
        "Missing Capacity, hours",
        "Upside Limit 2 (%)",
        "Upside Limit 2 (hrs)",
        "Upside Limit 1 (%)",
        "Upside Limit 1 (hrs)",
        "Downside Limit 1 (%)",
        "Downside Limit 1 (hrs)",
        "Downside Limit 2 (%)",
        "Downside Limit 2 (hrs)",
    ]
    rng = random.Random(SEED + 3)
    rows = []

    # Pre-compute week columns and month-summary columns once
    week_cols = WEEKS
    month_cols = MONTH_ABBR_COLS

    for plant in PLANT_CODES:
        for wc_short, wc_long, cal, h, d, oee, breaks in WC_DEFS[plant]:
            wc_key = f"P01_{plant}_{wc_short}"
            weekly_capacity = round(h * d * oee - breaks * d, 2)
            base_load_pct = rng.uniform(0.38, 0.82)
            # Seasonality — mild summer dip and Q4 spike
            seasonal = np.array([rng.uniform(0.85, 1.15) for _ in week_cols])
            fop_hours_weekly = np.clip(weekly_capacity * base_load_pct * seasonal, 0, weekly_capacity * 1.7)
            pph = {"S": 120, "M": 80, "L": 40}[cal] * rng.uniform(0.75, 1.25)
            limits_h = {
                "Upside Limit 2 (hrs)": weekly_capacity * 1.6,
                "Upside Limit 1 (hrs)": weekly_capacity * 1.3,
                "Downside Limit 1 (hrs)": weekly_capacity * 0.7,
                "Downside Limit 2 (hrs)": weekly_capacity * 0.5,
            }
            limits_pct = {
                "Upside Limit 2 (%)": 1.6,
                "Upside Limit 1 (%)": 1.3,
                "Downside Limit 1 (%)": 0.7,
                "Downside Limit 2 (%)": 0.5,
            }

            for meas in measures:
                row = {"Work center code": wc_key, "Measure": meas}
                for i, wk in enumerate(week_cols):
                    fop_h = float(fop_hours_weekly[i])
                    fop_q = fop_h * pph
                    bo_h = round(fop_h * rng.uniform(0.0, 0.08), 2)
                    nd_h = round(max(0.0, fop_h - bo_h), 2)
                    if meas == "Available Capacity, hours":
                        v = weekly_capacity
                    elif meas == "Final Operations Plan, Load in hours":
                        v = round(fop_h, 2)
                    elif meas == "Final Operations Plan, qty":
                        v = round(fop_q, 1)
                    elif meas == "Final Operations Plan, Capacity %":
                        v = round(fop_h / weekly_capacity, 4) if weekly_capacity else 0
                    elif meas == "Net Demand (Production Needed), Load in hours":
                        v = nd_h
                    elif meas == "Net Demand (Production Needed), qty":
                        v = round(nd_h * pph, 1)
                    elif meas == "Net Demand (Production Needed), Capacity %":
                        v = round(nd_h / weekly_capacity, 4) if weekly_capacity else 0
                    elif meas == "Back Orders, qty":
                        v = round(bo_h * pph, 1)
                    elif meas == "Back Orders, Load in hours":
                        v = bo_h
                    elif meas == "Net Demand + Back Orders, qty":
                        v = round((nd_h + bo_h) * pph, 1)
                    elif meas == "Net Demand + Back Orders, Load in hours":
                        v = round(nd_h + bo_h, 2)
                    elif meas == "Net Demand + Back Orders, Capacity %":
                        v = round((nd_h + bo_h) / weekly_capacity, 4) if weekly_capacity else 0
                    elif meas == "Overload Capacity check":
                        v = 1 if fop_h > weekly_capacity else 0
                    elif meas == "Remaining Available Capacity, hours":
                        v = round(weekly_capacity - fop_h, 2)
                    elif meas == "Missing Capacity, hours":
                        v = round(max(0.0, fop_h - weekly_capacity), 2)
                    elif meas in limits_h:
                        v = round(limits_h[meas], 2)
                    elif meas in limits_pct:
                        v = limits_pct[meas]
                    else:
                        v = 0.0
                    row[wk] = v
                for m_abbr in month_cols:
                    if meas.endswith(", hours") or meas.endswith("(hrs)"):
                        row[m_abbr] = round(weekly_capacity * 4.3, 2)
                    else:
                        row[m_abbr] = None
                rows.append(row)
    return pd.DataFrame(rows)


def build_sheet_2_2(topology: dict) -> pd.DataFrame:
    """2_2 OPS plan per material — cleaned: row 1 header, title row removed.

    Two groups of rows:
      1. Actively tooled plant-material pairs (one per unique entry in 2_6).
      2. Phantom rows for plant-materials that appear in the Anaplan plan but
         are NOT tooled at that plant (legacy codes, not-yet-productionized
         variants, future SKUs). These do NOT appear in 2_6 / 2_3 / 3_1.
    """
    rng = random.Random(SEED + 4)
    rows = []
    seen = set()
    # Group 1: actively tooled pairs
    for entry in topology["tool_materials"]:
        key = (entry["plant"], entry["mat"])
        if key in seen:
            continue
        seen.add(key)
        base = rng.uniform(0.005, 0.18)
        row = {
            "P80 - Plant Material: Plant without system": entry["plant"],
            "P80 - Plant Material: Code": f"P01_{entry['plant']}_{entry['mat']}",
            "P80 - Plant Material: Pure Material": entry["mat"],
            "P80 - Plant Material: Material Description": entry["mat_desc"],
            "P80 - Plant Material: Operations Group": f"OPS-{entry['family']}",
            "P80 - Plant Material: Mixed MRP": random.choice(["true", "false"]),
        }
        for wk in WEEKS:
            row[wk] = round(base * rng.uniform(0.25, 1.9), 4) if rng.random() > 0.12 else 0.0
        rows.append(row)

    # Group 2: phantom materials — present in 2_2 (ops plan) but not in 2_6.
    # Codes are drawn from a distinct synthetic range so they cannot collide
    # with actively tooled materials.
    phantom_families = PLATE_FAMILIES + GASKET_FAMILIES
    for plant in PLANT_CODES:
        for k in range(N_PHANTOM_MATERIALS_PER_PLANT):
            fam = rng.choice(phantom_families)
            # Phantom code range: 900000-999999 (well outside tooled 100k/200k).
            # 15 plants × 1500 = 22,500 phantom slots — allocate 6,000 per plant.
            mat = _mat_code(900000 + PLANT_CODES.index(plant) * 6000 + k)
            desc = f"{fam} PHANTOM {k:04d}"
            base = rng.uniform(0.001, 0.05)  # much lower volumes than active
            row = {
                "P80 - Plant Material: Plant without system": plant,
                "P80 - Plant Material: Code": f"P01_{plant}_{mat}",
                "P80 - Plant Material: Pure Material": mat,
                "P80 - Plant Material: Material Description": desc,
                "P80 - Plant Material: Operations Group": f"OPS-{fam}",
                "P80 - Plant Material: Mixed MRP": rng.choice(["true", "false"]),
            }
            for wk in WEEKS:
                # Phantoms are sparse — most weeks zero
                row[wk] = round(base * rng.uniform(0.1, 1.5), 4) if rng.random() > 0.55 else 0.0
            rows.append(row)

    return pd.DataFrame(rows)


def build_sheet_2_3(topology: dict) -> pd.DataFrame:
    """2_3 SAP MasterData — cleaned: first column explicitly named `Sap code`."""
    rng = random.Random(SEED + 5)
    rows = []
    seen = set()
    for entry in topology["tool_materials"]:
        key = (entry["plant"], entry["mat"])
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "Sap code": entry["mat"],
            "Description": entry["mat_desc"],
            "Old Material Number": f"OLD-{entry['mat'][-6:]}",
            "Base Unit of Measure": "PC",
            "Material Type": rng.choice(["FERT", "HALB", "ROH"]),
            "ABC (SAP)": rng.choice(["A", "B", "C"]),
            "Procurement Type": rng.choice(["E", "F", "X"]),
            "In House Production Time (WD)": rng.choice([5, 7, 10, 14, 21]),
            "Production LT Weeks": rng.choice([2, 3, 4, 6, 8]),
            "Transportation Lanes Lead Time (CD)": rng.choice([7, 14, 21, 30]),
            "Planned Delivery Time (MARC) (CD)": rng.choice([14, 21, 28, 35, 45, 60]),
            "Standard Cost in EUR": round(rng.uniform(1.5, 120.0), 2),
            "Avg Sales Price in EUR": round(rng.uniform(4.0, 220.0), 2),
            "G35 - Plant": entry["plant"],
            "G37 - Vendor": f"V-{rng.randint(10000, 99999)}",
            "P45 - Supply Group": f"SG-{rng.randint(10, 120)}",
            "P55 - Operations Group": f"OPS-{entry['family']}",
            "Is Network Material": rng.choice(["Y", "N"]),
            "BOM Material": entry["mat"],
            "BOM Header": f"BH-{rng.randint(1000, 9999)}",
            "BOM Component": f"BC-{rng.randint(1000, 9999)}",
        })
    return pd.DataFrame(rows)


def build_sheet_2_4() -> pd.DataFrame:
    """2_4 Model Calendar — cleaned: row 1 is the header."""
    start = pd.Timestamp("2026-01-01")
    end = pd.Timestamp("2027-12-31")
    days = pd.date_range(start, end, freq="D")

    cols = []
    week_to_col: dict[tuple[int, int], str] = {}
    current_week = None
    for d in days:
        iso_year, iso_week, _ = d.isocalendar()
        wkey = (int(iso_year), int(iso_week))
        if wkey != current_week:
            wc_name = f"Week {int(iso_week)} {int(iso_year)}"
            if wc_name not in week_to_col.values():
                week_to_col[wkey] = wc_name
                cols.append(("week", wc_name, wkey))
                current_week = wkey
        col_name = f"{d.day} {d.strftime('%b')} {str(d.year)[2:]}"
        cols.append(("day", col_name, d))

    header = [c[1] for c in cols]
    records: dict[str, list] = {"Attribute": []}
    for col in header:
        records[col] = []

    def append_row(attribute: str, value_fn):
        records["Attribute"].append(attribute)
        for kind, name, ref in cols:
            records[name].append(value_fn(kind, ref))

    append_row("Day Number", lambda k, r: r.day if k == "day" else None)
    append_row("Day of Week (ISO)", lambda k, r: r.isoweekday() if k == "day" else None)
    append_row("Day Name", lambda k, r: r.strftime("%a") if k == "day" else None)
    append_row("Week Number", lambda k, r: r.isocalendar()[1] if k == "day" else r[1])
    append_row("Week Number Weekly", lambda k, r: r[1] if k == "week" else None)
    append_row("Week Start Date", lambda k, r: (pd.Timestamp.fromisocalendar(r[0], r[1], 1).date() if k == "week" else None))
    append_row("Month Number", lambda k, r: r.month if k == "day" else None)
    append_row("Month Number Weekly {Corrected}",
               lambda k, r: None if k == "day" else pd.Timestamp.fromisocalendar(r[0], r[1], 1).month)
    append_row("Month Name", lambda k, r: r.strftime("%B") if k == "day" else None)
    append_row("Quarter", lambda k, r: f"Q{((r.month - 1) // 3) + 1}" if k == "day" else None)
    append_row("Year", lambda k, r: r.year if k == "day" else r[0])
    append_row("Fiscal Year", lambda k, r: r.year if k == "day" else r[0])
    append_row("Fiscal Period", lambda k, r: r.month if k == "day" else None)
    append_row("Weekend Flag", lambda k, r: (1 if r.weekday() >= 5 else 0) if k == "day" else None)
    append_row("Business Day Flag", lambda k, r: (0 if r.weekday() >= 5 else 1) if k == "day" else None)
    append_row("Half Year", lambda k, r: f"H{1 if r.month <= 6 else 2}" if k == "day" else None)
    append_row("Days in Month", lambda k, r: r.days_in_month if k == "day" else None)
    append_row("Days in Year", lambda k, r: (366 if r.is_leap_year else 365) if k == "day" else None)
    # Per-plant schedule rules. `weekend` = set of weekday indices that are
    # the plant's weekend (0=Mon … 6=Sun). `shift_h` = default daily hours.
    schedule_rules = {
        "NW01": {"weekend": {5, 6},    "shift_h": 12},
        "NW02": {"weekend": {5, 6},    "shift_h": 8},
        "NW03": {"weekend": {6},       "shift_h": 12},  # Mon-Sat
        "NW04": {"weekend": {6},       "shift_h": 12},  # Mon-Sat
        "NW05": {"weekend": {5, 6},    "shift_h": 8},
        "NW06": {"weekend": {5, 6},    "shift_h": 12},
        "NW07": {"weekend": {5, 6},    "shift_h": 8},
        "NW08": {"weekend": {5, 6},    "shift_h": 8},
        "NW09": {"weekend": {5, 6},    "shift_h": 12},
        "NW10": {"weekend": {6},       "shift_h": 12},  # Mon-Sat
        "NW11": {"weekend": {4, 5},    "shift_h": 12},  # MENA: Sun-Thu
        "NW12": {"weekend": {5, 6},    "shift_h": 8},
        "NW13": {"weekend": {5, 6},    "shift_h": 8},
        "NW14": {"weekend": {5, 6},    "shift_h": 8},
        "NW15": {"weekend": {6},       "shift_h": 12},  # Mon-Sat
    }

    append_row("== Working Days ==", lambda k, r: None)
    for plant, _, _ in PLANTS:
        def wd(kind, ref, _p=plant):
            if kind != "day":
                return None
            return 0 if ref.weekday() in schedule_rules[_p]["weekend"] else 1
        append_row(f"Working Days {plant}", wd)
    for plant, _, _ in PLANTS:
        def wh(kind, ref, _p=plant):
            if kind != "day":
                return None
            if ref.weekday() in schedule_rules[_p]["weekend"]:
                return 0
            return schedule_rules[_p]["shift_h"]
        append_row(f"Working Hours {plant}", wh)
    # Regional holiday sets
    holiday_calendar = {
        "NW01": {(1, 1), (7, 4), (11, 26), (12, 25)},           # US
        "NW02": {(1, 1), (5, 1), (12, 24), (12, 25), (12, 26)}, # EU West
        "NW03": {(1, 1), (5, 1), (5, 9), (8, 15), (12, 25), (12, 26)}, # EU East
        "NW04": {(1, 1), (1, 26), (8, 15), (10, 2), (12, 25)},  # India
        "NW05": {(1, 1), (5, 1), (10, 1), (10, 2), (10, 3)},    # China Golden Week
        "NW06": {(1, 1), (7, 4), (11, 26), (12, 25)},           # US
        "NW07": {(1, 1), (7, 4), (11, 26), (12, 25)},           # US
        "NW08": {(1, 1), (5, 1), (12, 24), (12, 25), (12, 26)}, # Iberia
        "NW09": {(1, 1), (5, 1), (12, 24), (12, 25), (12, 26)}, # Alpine
        "NW10": {(1, 1), (5, 1), (6, 23), (12, 24), (12, 25)},  # Baltics
        "NW11": {(1, 1), (5, 1), (9, 1), (12, 25)},             # MENA (simplified)
        "NW12": {(1, 1), (5, 1), (9, 7), (10, 12), (12, 25)},   # Brazil-like
        "NW13": {(1, 1), (5, 1), (7, 28), (12, 25)},            # Andes-like
        "NW14": {(1, 1), (1, 26), (4, 25), (12, 25), (12, 26)}, # Oceania
        "NW15": {(1, 1), (4, 30), (5, 1), (9, 2), (12, 25)},    # SE Asia
    }
    for plant, _, _ in PLANTS:
        def hol(kind, ref, _p=plant):
            if kind != "day":
                return None
            return 1 if (ref.month, ref.day) in holiday_calendar[_p] else 0
        append_row(f"Holiday Flag {plant}", hol)

    return pd.DataFrame(records)


def build_sheet_2_5(topology: dict) -> pd.DataFrame:
    """2_5 WC Schedule_limits — cleaned: row 1 header, no blank col A, no 35-row preamble."""
    limit_defs = [
        ("Downside Limit 2 (hrs)", 0.5),
        ("Downside Limit 1 (hrs)", 0.7),
        ("Available Capacity, hours", 1.0),
        ("Upside Limit 1 (hrs)", 1.3),
        ("Upside Limit 2 (hrs)", 1.6),
    ]
    rng = random.Random(SEED + 6)
    rows = []
    for plant in PLANT_CODES:
        plant_name = PLANT_NAME[plant]
        for wc_short, wc_long, caliber, h, d, oee, breaks in WC_DEFS[plant]:
            base_weekly = h * d * oee - breaks * d
            stands = {"S": 1, "M": 2, "L": 3}[caliber]
            for lname, factor in limit_defs:
                row = {
                    "WC Schedule Label": f"{plant}_{wc_short} {h}/{d} ({h}H/{d}D)",
                    "Plant": plant,
                    "Plant name": plant_name,
                    "Size": caliber,
                    "WC-Group": "",
                    "WC-Description": wc_short,
                    "WC-Description long": wc_long,
                    "Weekly Schedule": f"{h}/{d}",
                    "Hours": h,
                    "Days": d,
                    "AP Limit": lname,
                    "Weekly available time": round(base_weekly * factor, 2),
                    "Suggested % Limit": factor,
                    "AP Limit (in %)": factor,
                    "AP Limit time (in H)": round(base_weekly * factor, 2),
                    "OEE (in %)": oee,
                    "Daily breaks (in H)": breaks,
                    "NR of stands per WC": stands,
                }
                for m_abbr in ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                               "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]:
                    row[m_abbr] = round(base_weekly * factor * 4.3 * rng.uniform(0.95, 1.05), 2)
                rows.append(row)
    return pd.DataFrame(rows)


def build_sheet_2_6(topology: dict) -> pd.DataFrame:
    """2_6 Tool_material nr master — cleaned: row 1 header, no source-labels preamble row."""
    rng = random.Random(SEED + 7)
    rows = []
    for entry in topology["tool_materials"]:
        wc_value = entry["wc"] if rng.random() > 0.025 else "#N/A"
        rows.append({
            "Connector": f"{entry['plant']}_{entry['mat']}",
            "Plant": entry["plant"],
            "Type": entry["mat_type"],
            "Sap code": entry["mat"],
            "Material description": entry["mat_desc"],
            "Total QTY": round(rng.uniform(500, 260000), 0),
            "Tool No.": entry["tool"],
            "Work center": wc_value,
            "Group": f"N/{rng.randint(50000000, 60000000)}",
            "Cycle times Standard Value (Machine)": entry["cycle_time"],
            "OPS plan GD": entry["ops_plan_gd"],
            "Rev no": entry["rev_no"],
            "Material Status": rng.choice(["Active", "Active", "Active", "Active", "Phase-out"]),
        })
    return pd.DataFrame(rows)


def build_sheet_3_1(topology: dict) -> pd.DataFrame:
    """3_1 Inventory ATP — cleaned: row 1 header. EUR currency row merged into value column names."""
    rng = random.Random(SEED + 9)
    rows = []
    seen = set()
    for entry in topology["tool_materials"]:
        key = (entry["plant"], entry["mat"])
        if key in seen:
            continue
        seen.add(key)
        stock = round(rng.uniform(0, 12000), 0)
        transit = round(rng.uniform(0, 3500), 0)
        safety = round(rng.uniform(50, 1200), 0)
        unit_value = rng.uniform(3, 60)
        rows.append({
            "Source system ID": "P01",
            "Plant (code)": entry["plant"],
            "Plant (name)": PLANT_NAME[entry["plant"]],
            "Calendar day": "2026.04.03",
            "Operation Group": f"OPS-{entry['family']}",
            "Material Unique (code)": entry["mat"],
            "Material Unique (name)": entry["mat_desc"],
            "Stock Qty": stock,
            "ATP Quantity": round(stock * rng.uniform(0.5, 0.95), 0),
            "ATP Qty (allow negative)": round(stock * rng.uniform(0.3, 0.9), 0),
            "Reserved Stock Qty": round(stock * rng.uniform(0.0, 0.2), 0),
            "Stock in Transit Qty": transit,
            "Safety Stock Qty": safety,
            "Minimum Safety Stock Qty": round(safety * 0.7, 0),
            "Stock Value (EUR)": round(stock * unit_value, 2),
            "ATP Stock Value (EUR)": round(stock * unit_value * 0.9, 2),
            "Reserved Stock Value (EUR)": round(stock * unit_value * rng.uniform(0.05, 0.2), 2),
            "Safety Stock Value (EUR)": round(safety * unit_value, 2),
            "Stock in Transit Value (EUR)": round(transit * unit_value, 2),
            "Total Stock Value (EUR)": round((stock + transit) * unit_value, 2),
        })
    return pd.DataFrame(rows)


# Raw-material catalog (referenced in 3_2) — plant-agnostic codes
RAW_MATERIALS = {
    "coils": [
        ("RM-COIL-SS304", "COIL SS304 1250mm 0.4mm", 6.5, "KG"),
        ("RM-COIL-SS316", "COIL SS316 1250mm 0.5mm", 7.1, "KG"),
        ("RM-COIL-TI",    "COIL TITANIUM 1200mm 0.4mm", 5.3, "KG"),
        ("RM-COIL-AL",    "COIL ALUMINUM 1300mm 0.6mm", 4.8, "KG"),
        ("RM-COIL-NI",    "COIL NICKEL 1200mm 0.35mm", 6.0, "KG"),
        ("RM-COIL-HC276", "COIL HASTELLOY C276 1250mm 0.5mm", 7.8, "KG"),
    ],
    "compounds": [
        ("RM-COMP-NBR",  "RUBBER COMPOUND NBR70", 0.35, "KG"),
        ("RM-COMP-EPDM", "RUBBER COMPOUND EPDM80", 0.28, "KG"),
        ("RM-COMP-FKM",  "RUBBER COMPOUND FKM75", 0.42, "KG"),
        ("RM-COMP-SILI", "RUBBER COMPOUND SILICONE", 0.30, "KG"),
        ("RM-COMP-HNBR", "RUBBER COMPOUND HNBR60", 0.38, "KG"),
        ("RM-COMP-AFLAS","RUBBER COMPOUND AFLAS", 0.45, "KG"),
    ],
}


def build_sheet_3_2(topology: dict) -> pd.DataFrame:
    """3_2 Component_SF_RM — cleaned: row 1 header. BOM header→component, plant-specific."""
    rng = random.Random(SEED + 10)
    rows = []
    for entry in topology["tool_materials"]:
        plant = entry["plant"]
        mat = entry["mat"]
        family = entry["family"]
        mtype = entry["mat_type"]
        comp_list = RAW_MATERIALS["coils"] if mtype == "Plates" else RAW_MATERIALS["compounds"]
        n_components = 1 if rng.random() > 0.25 else 2
        chosen = rng.sample(comp_list, k=n_components)
        for comp_code, comp_desc, comp_base_qty, comp_uom in chosen:
            if family.startswith(("XL", "HT")):
                base_q = comp_base_qty * 1.8
            elif family.startswith("PRO"):
                base_q = comp_base_qty * 1.3
            else:
                base_q = comp_base_qty
            base_q = round(base_q * rng.uniform(0.82, 1.2), 3)
            scrap = round(rng.uniform(0.01, 0.06), 3)
            assy_scrap = round(rng.uniform(0.005, 0.03), 3)
            total_scrap = round((1 + scrap) * (1 + assy_scrap), 4)
            rows.append({
                "Header Material": f"P01_{plant}_{mat}",
                "Component Material": f"P01_{plant}_{comp_code}",
                "Header Material code": mat,
                "Component Material code": comp_code,
                "Component Quantity": base_q,
                "Component BUoM": comp_uom,
                "Component Description": comp_desc,
                "Production LT in Weeks": rng.choice([2, 3, 4, 6, 8]),
                "Component Scrap (perc)": scrap,
                "Assembly Scrap (perc)": assy_scrap,
                "Component Scrap Factor": 1 + scrap,
                "Assembly Scrap Factor": 1 + assy_scrap,
                "Total Scrap Factor": total_scrap,
                "Effective Component Quantity": round(base_q * total_scrap, 3),
                "Plant": f"P01_{plant}_{PLANT_NAME[plant]}",
                "Header OPS Group": f"OPS-{family}",
                "Component OPS Group": f"RM-{'COIL' if mtype == 'Plates' else 'COMP'}",
                "Comp Plate/Gasket": mtype,
                "Header Description": entry["mat_desc"],
                "Version": "001",
                "Usage": "1",
                "BOM Status": "Active",
            })
    return pd.DataFrame(rows)


def build_flow_sheet() -> pd.DataFrame:
    rows = [
        ["Stage", "Sheet", "Purpose"],
        ["Demand", "1_1 Export Plates", "Sales pipeline — plate material requests"],
        ["Demand", "1_2 Gaskets", "Sales pipeline — gasket material requests"],
        ["Demand", "1_3 Export Project list", "Project metadata (region, owner, probability)"],
        ["Capacity", "2_1 Work Center Capacity Weekly", "Anaplan capacity + plan per work center"],
        ["Capacity", "2_2 OPS plan per material", "Per-material disaggregated plan (pieces)"],
        ["Master data", "2_3 SAP MasterData", "Lead times, vendor, ABC, safety stock"],
        ["Master data", "2_4 Model Calendar", "Daily/weekly/monthly time calendar"],
        ["Master data", "2_5 WC Schedule_limits", "Shift configurations & capacity limits"],
        ["Master data", "2_6 Tool_material nr master", "The core join table: material ↔ tool ↔ WC ↔ plant"],
        ["Inventory", "3_1 Inventory ATP", "Stock, transit, safety stock per material"],
        ["Inventory", "3_2 Component_SF_RM", "BOM — finished good → raw material"],
    ]
    return pd.DataFrame(rows[1:], columns=rows[0])


def build_data_dictionary_overview() -> pd.DataFrame:
    return pd.DataFrame([
        ["NR", "Masterdata file", "Area", "Masterdata Information"],
        [1.1, "Export Plates", "Sales force", "SIOP — Not approved project requirements on a Plate material level."],
        [1.2, "Export Gaskets", "Sales force", "SIOP — Not approved project requirements on a Gasket material level."],
        [1.3, "Export Project list", "Sales force", "SIOP — project owners, regions, delivery dates, probability."],
        [2.1, "Work Center Capacity Weekly", "Capacity load - Anaplan", "Work center capacity & plan in hours and PCS."],
        [2.2, "OPS plan per material", "Capacity load - RCCP", "Operations plan disaggregated to material level."],
        [2.3, "SAP MasterData", "Capacity load - Anaplan", "Lead times, sourcing plants, ABC, safety stock, vendor."],
        [2.4, "Model Calendar", "Capacity load - Anaplan", "Day-week-month calendar grid."],
        [2.5, "Work Center Schedule Limits", "Capacity load - RCCP", "Anaplan limit levels expressed as shift schedules."],
        [2.6, "Tool Material Number Master", "Capacity load - RCCP", "Work center × material × cycle time × tool × Rev no."],
        [3.1, "Inventory ATP", "Material availability", "Stock, in-transit, safety stock per plant × material."],
        [3.2, "Component_SF_RM", "Material availability", "BOM relation from plate/gasket to coil/compound."],
    ])


# ── Write workbook (clean single-row-header format) ─────────────

def _write_excel(path: Path) -> None:
    """Write the workbook with row-1 headers across all sheets."""
    topology = build_master_topology()
    plate_rows, gasket_rows, project_list_rows = build_pipeline_projects(topology)

    sheets = {
        "Flow": build_flow_sheet(),
        "1_1 Export Plates": build_sheet_1_1(plate_rows),
        "1_2 Gaskets": build_sheet_1_2(gasket_rows),
        "1_3 Export Project list": build_sheet_1_3(project_list_rows),
        "2_1 Work Center Capacity Weekly": build_sheet_2_1(topology),
        "2_2 OPS plan per material": build_sheet_2_2(topology),
        "2_3 SAP MasterData": build_sheet_2_3(topology),
        "2_4 Model Calendar": build_sheet_2_4(),
        "2_5 WC Schedule_limits": build_sheet_2_5(topology),
        "2_6 Tool_material nr master": build_sheet_2_6(topology),
        "3_1 Inventory ATP": build_sheet_3_1(topology),
        "3_2 Component_SF_RM": build_sheet_3_2(topology),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)


def _write_dictionary_overview(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df = build_data_dictionary_overview()
        df.to_excel(writer, sheet_name="Sheet1", index=False, header=False)


if __name__ == "__main__":
    import time
    out_dir = Path(__file__).resolve().parent.parent / "data"
    dataset_path = out_dir / "hackathon_dataset.xlsx"
    dictionary_path = out_dir / "Data_Dictionary_overview.xlsx"
    t0 = time.time()
    _write_excel(dataset_path)
    t1 = time.time()
    _write_dictionary_overview(dictionary_path)
    t2 = time.time()
    print(f"wrote {dataset_path} ({dataset_path.stat().st_size / 1024 / 1024:.2f} MB) in {t1-t0:.1f}s")
    print(f"wrote {dictionary_path} ({dictionary_path.stat().st_size / 1024:.1f} KB) in {t2-t1:.1f}s")
