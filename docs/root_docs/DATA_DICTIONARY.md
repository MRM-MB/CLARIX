# Data Dictionary — Predictive Manufacturing Hackathon Dataset

This dictionary describes the 12 sheets in [data/hackathon_dataset.xlsx](data/hackathon_dataset.xlsx): what each sheet contains, what each column means, and how the sheets join to one another. It is intentionally **descriptive, not prescriptive** — it tells you the structure of the data, not how to analyze it.

## Source & format

- **File:** `data/hackathon_dataset.xlsx` (~26 MB, 12 sheets)
- **Cleanliness:** Every sheet has a single header row on **row 1** and no blank leading columns. Load with `pd.read_excel(path, sheet_name=...)` and you're done — no `header=3` or `skiprows=35` gymnastics required. The original Danfoss export had multi-row headers, refresh-metadata preambles, and blank leading columns; those have all been normalized.
- **Anonymization:** Plant codes, plant names, material codes, tool numbers, project names, and vendor IDs have all been replaced with synthetic values. The schema, units, data-quality quirks, and inter-sheet relationships mirror the real export.
- **Snapshot date:** simulated at ~April 2026.
- **Horizon:** 36 months (Jan 2026 – Dec 2028) with weekly granularity.
- **Scale:** 15 plants, 109 work centers, ~2,300 active materials + 22,500 phantom materials in the ops plan, ~7,600 tool-material master records, ~9,500 BOM lines.

## Plants (factories)

Fifteen anonymized plants forming the fictional "Northwind" global manufacturing network. Sites vary in press portfolio, ancillary lines (extrusion, grinding, lathe, oven, assembly), shift patterns, weekend conventions, and regional holiday calendars.

| Code | Name | Region |
|------|------|--------|
| NW01 | Northwind Midwest | North America |
| NW02 | Northwind Heartland | Europe West |
| NW03 | Northwind Carpathia | Europe East *(uses `PRES_` naming)* |
| NW04 | Northwind Southbay | South Asia |
| NW05 | Northwind Pacific | East Asia |
| NW06 | Northwind Southeast | North America |
| NW07 | Northwind West Coast | North America |
| NW08 | Northwind Iberia | Europe West |
| NW09 | Northwind Alpine | Europe West |
| NW10 | Northwind Baltics | Europe East |
| NW11 | Northwind Levant | MENA *(Sun-Thu work week)* |
| NW12 | Northwind Cerrado | South America |
| NW13 | Northwind Andes | South America |
| NW14 | Northwind Oceania | Oceania |
| NW15 | Northwind Indochina | Southeast Asia |

Each plant runs a unique combination of:
- **Press portfolio** — 3-6 presses per plant, mix of 3300T / 5500T / 8000T / 11000T / 13900T (caliber S / M / L).
- **Ancillary lines** — 2-4 per plant from: extrusion, grinding, lathe, oven, assembly.
- **Shift pattern** — hours/day (8 or 12), days/week (5 or 6), OEE (0.73–0.85), daily breaks.
- **Weekend convention** — most plants Sat-Sun off; NW03 / NW04 / NW10 / NW15 work Saturdays; NW11 observes a Fri-Sat weekend.
- **Holiday calendar** — regional observances (see sheet 2_4).

## Sheet index

| NR | Sheet name | Area | What it contains |
|----|------------|------|------------------|
| — | `Flow` | Overview | Human-readable flow diagram. |
| 1.1 | `1_1 Export Plates` | Sales pipeline | Pipeline demand at plate-material granularity. |
| 1.2 | `1_2 Gaskets` | Sales pipeline | Pipeline demand at gasket-material granularity. |
| 1.3 | `1_3 Export Project list` | Sales pipeline | Project metadata (owner, region, probability, requested date). |
| 2.1 | `2_1 Work Center Capacity Weekly` | Capacity | Weekly plan vs. capacity per work center (23 measures). |
| 2.2 | `2_2 OPS plan per material` | Capacity | Plan disaggregated to plant × material per week (pieces). |
| 2.3 | `2_3 SAP MasterData` | Master data | Lead times, procurement type, ABC, safety stock. |
| 2.4 | `2_4 Model Calendar` | Master data | Day/week/month/quarter grid with per-plant working-day and holiday flags. |
| 2.5 | `2_5 WC Schedule_limits` | Master data | Five shift levels per WC with OEE and break discounts. |
| 2.6 | `2_6 Tool_material nr master` | Master data | The core join table: material ↔ tool ↔ WC ↔ plant ↔ cycle time. |
| 3.1 | `3_1 Inventory ATP` | Inventory | Stock, in-transit, safety stock per plant × material. |
| 3.2 | `3_2 Component_SF_RM` | BOM | Finished good → raw material relationship. |

---

## 1_1 Export Plates

Pipeline demand for plate materials — each row is one (Project × Plate material × Factory) combination with monthly PCS quantities across the 36-month horizon.

- **Grain:** one row per project × plate material × plant.
- **Approximate size:** ~180 rows.

| Column | Type | Notes |
|--------|------|-------|
| Status | str | Always `Not approved` (these are unapproved pipeline projects). |
| Connector RCCP pivot | str | `{Plant}_{PlantName}` or `Missing plant` when unresolved. |
| Connector Plant_Material nr | str | Primary join key. Pattern: `{Plant}_{MaterialCode}`. Blank rows show `_`. |
| Material number | str | Material code (null if connector unresolved). |
| Material Description | str | Plate description. |
| Cycle time | float or `Missing CT` | Per-piece time from 2_6. Unit is part of your analysis to confirm. |
| Work center | str or `Missing WC` | Short WC code (e.g., `PRESS_3`, `PRES_3_1`). |
| Tool number | str or `Missing tool` | Tool ID from 2_6. |
| Project_name | str | Text name. Joins to `1_3 Export Project list`. |
| Plate Factory | str | Resolved factory long form: `P01_{Plant}_{PlantName}`. |
| Plate Final | str | Resolved material code. |
| Plate Description | str | Resolved description. |
| All delayed | int | Total delayed qty. |
| Monthly columns (×36) | float | Pattern `M YYYY` (e.g., `1 2026`, `2 2026` … `12 2028`). Values are PCS. Null or zero = no demand that month. |

**Joins**
- `Connector Plant_Material nr` → `2_6.Connector`
- `Project_name` → `1_3.Project name`
- Work-center code → `2_1.Work center code` as `P01_{Plant}_{Work center}`

---

## 1_2 Gaskets

Pipeline demand for gasket materials. **Same structure as 1_1** except the resolution columns are correctly named `Gasket Factory`, `Gasket Final`, `Gasket Description` (fixed from the original export's template mistake).

Approximate size: ~180 rows.

---

## 1_3 Export Project list

Project-level metadata for sales pipeline items.

- **Grain:** one row per project.
- **Approximate size:** ~720 rows.

| Column | Type | Notes |
|--------|------|-------|
| Project name | str | Join key back to `1_1` / `1_2`. |
| Project ID | str | Salesforce ID. |
| Region | str | NA, EMEA-West, EMEA-East, APAC-South, APAC-East, LATAM. |
| Owner | str | Account owner. |
| Probability | int | 10 / 25 / 50 / 75 / 90 (percentage). |
| Requested delivery date | date str | Customer-requested delivery date. |
| Customer segment | str | e.g., Industrial, Refrigeration, Data Center, Pharma. |
| Total expected PCS | int | Rough volume estimate. |
| Total expected EUR | float | Rough revenue estimate. |
| Revenue tier | str | Small / Medium / Large / Strategic. |
| Submission channel | str | Direct / Distributor / Partner / OEM. |
| Status | str | `Not approved`. |
| Notes | str | Free text. |

**Note:** not every project in `1_1` / `1_2` is present in `1_3` — a small number of recently added pipeline items haven't been synced to the master list. That's authentic master-data latency, not a join bug.

---

## 2_1 Work Center Capacity Weekly

Anaplan capacity baseline. Pivoted: rows are (Work Center × Measure), columns are weekly buckets plus monthly summary columns.

- **Grain:** one row per (work center × measure).
- **23 measures per work center** covering demand (net, back orders, plan), capacity, limit levels, and overload flags.
- **Approximate size:** ~2,500 rows × ~190 columns (156 weekly + 36 monthly summary + 2 keys). 109 work centers across 15 plants.

| Column | Notes |
|--------|-------|
| Work center code | `P01_{Plant}_{WC}`. |
| Measure | One of the 23 measure names (see below). |
| `Week N YYYY` | Weekly value. |
| `Mon YY` | Monthly summary column. |

**The 23 measures**

```
Available Capacity, hours
Net Demand (Production Needed), qty / Load in hours / Capacity %
Back Orders, qty / Load in hours
Net Demand + Back Orders, qty / Load in hours / Capacity %
Final Operations Plan, qty / Load in hours / Capacity %
Overload Capacity check
Remaining Available Capacity, hours
Missing Capacity, hours
Upside Limit 2 (%) / (hrs)
Upside Limit 1 (%) / (hrs)
Downside Limit 1 (%) / (hrs)
Downside Limit 2 (%) / (hrs)
```

**Notes**
- `Final Operations Plan, qty` and `Final Operations Plan, Load in hours` together imply a pieces-per-hour rate per work center.
- The 5 limit levels correspond to different shift configurations in sheet `2_5` — running extra shifts moves a WC up or down the limit ladder.

**Joins**
- `Work center code` ↔ `2_6` via `P01_{2_6.Plant}_{2_6.Work center}`.
- `Work center code` ↔ `2_5` via `Plant + WC-Description`.

---

## 2_2 OPS plan per material

Plan in pieces, disaggregated from Operations Plan down to plant × material per week.

- **Grain:** one row per (plant × material).
- **Unit:** **pieces** (not hours). Values are small per row because they represent one material's share of the plant's total plan each week.
- **Approximate size:** ~30,000 rows × ~160 columns.
- **Note:** the ops plan references two classes of material: **active / tooled** material codes (these also appear in sheet 2_6) and **phantom** codes — materials planned in Anaplan but not yet tooled at that plant (legacy codes, future SKUs, or variants still being productionized). Phantom codes use the `MAT-9xxxxx` prefix range and carry much smaller weekly volumes than active codes.

| Column | Notes |
|--------|-------|
| P80 - Plant Material: Plant without system | Plant code. |
| P80 - Plant Material: Code | `P01_{Plant}_{Material}`. |
| P80 - Plant Material: Pure Material | Material code. |
| P80 - Plant Material: Material Description | |
| P80 - Plant Material: Operations Group | OPS group. |
| P80 - Plant Material: Mixed MRP | `true` / `false`. |
| `Week N YYYY` | Weekly pieces planned. |

---

## 2_3 SAP MasterData

SAP material master — procurement, lead times, safety stock, cost.

- **Grain:** one row per plant × material. **Covers only actively-tooled materials** — phantom codes from sheet 2_2 do not have SAP master records.
- **Approximate size:** ~7,600 rows.

Selected columns:

| Column | Notes |
|--------|-------|
| Sap code | Material code (primary identifier). |
| Description | |
| Old Material Number | |
| Base Unit of Measure | PC, M, KG… |
| Material Type | FERT (finished), HALB (semi), ROH (raw). |
| ABC (SAP) | ABC classification. |
| Procurement Type | E (external), F (in-house), X (both). |
| In House Production Time (WD) | Working days. |
| Production LT Weeks | Production lead time in weeks. |
| Transportation Lanes Lead Time (CD) | Calendar days. |
| Planned Delivery Time (MARC) (CD) | Calendar days — common choice for sourcing-order-by-date math. |
| Standard Cost in EUR | |
| Avg Sales Price in EUR | |
| G35 - Plant | Plant code. |
| G37 - Vendor | Vendor code. |
| P45 - Supply Group | |
| P55 - Operations Group | Joins to `2_2`. |
| Is Network Material | Y/N. |
| BOM Material / Header / Component | BOM references. |

---

## 2_4 Model Calendar

Transposed calendar: each column is a calendar day or a weekly summary column; each row is an attribute.

- **Structure:** ~65 attribute rows × ~830 date/week columns over the 2026–2028 horizon. Attribute rows include per-plant working-day, working-hours, and holiday-flag rows for all 15 plants.

**Attribute rows**
- `Day Number`, `Day of Week (ISO)`, `Day Name`
- `Week Number`, `Week Number Weekly`, `Week Start Date`
- `Month Number`, `Month Number Weekly {Corrected}`, `Month Name`
- `Quarter`, `Year`, `Fiscal Year`, `Fiscal Period`, `Half Year`
- `Weekend Flag`, `Business Day Flag`
- `Days in Month`, `Days in Year`
- `Working Days NW01` … `NW05` (0/1 flag per calendar day per plant)
- `Working Hours NW01` … `NW05` (hours contributed per working day per plant)
- `Holiday Flag NW01` … `NW05` (0/1 per plant)

**Use case.** The capacity sheet (`2_1`) is weekly. The demand sheet (`1_1`/`1_2`) is monthly. The calendar tells you how many days of each week fall into each month, so you can aggregate or disaggregate cleanly. An ISO week that straddles Jan 30 → Feb 5 has 2 days of January and 5 days of February; the calendar tells you that explicitly.

---

## 2_5 WC Schedule_limits

Five shift configurations per work center — how many hours and days, what OEE applies, daily breaks, and the resulting weekly available time.

- **Grain:** 5 rows per WC (one per shift level).
- **Approximate size:** ~545 rows (109 work centers × 5 levels).

| Column | Notes |
|--------|-------|
| WC Schedule Label | Composite label `{Plant}_{WC} {H}/{D} ({H}H/{D}D)`. |
| Plant | Plant code. |
| Plant name | |
| Size | S / M / L press caliber. |
| WC-Group | (often blank) |
| WC-Description | Short WC name. |
| WC-Description long | e.g., `Press 8000T`. |
| Weekly Schedule | e.g., `12/5`, `24/7`. |
| Hours | Hours per shift per day. |
| Days | Working days per week at this shift level. |
| AP Limit | One of: `Downside Limit 2 (hrs)`, `Downside Limit 1 (hrs)`, `Available Capacity, hours`, `Upside Limit 1 (hrs)`, `Upside Limit 2 (hrs)`. |
| Weekly available time | `Hours × Days × OEE − breaks × Days`. |
| Suggested % Limit / AP Limit (in %) / AP Limit time (in H) | Same level expressed different ways. |
| OEE (in %) | 0–1. |
| Daily breaks (in H) | Deducted per day. |
| NR of stands per WC | Parallel press stands. |
| JAN…DEC | Pre-computed monthly capacity at this shift level. |

**Interpretation.** The five limits together describe management's levers — they can up-shift to absorb more demand (Upside 1, Upside 2) or scale down when demand is soft (Downside 1, Downside 2). Your scenario logic will probably want to choose a shift level per WC per period.

---

## 2_6 Tool_material nr master

The core join table. Every other sheet's material-level information ultimately lands here.

- **Grain:** one row per plant × material × tool combination.
- **Approximate size:** ~7,600 rows.

| Column | Notes |
|--------|-------|
| Connector | Primary key — `{Plant}_{MaterialCode}`. Joins to `1_1` / `1_2`. |
| Plant | Plant code. |
| Type | `Plates` or `Gaskets`. |
| Sap code | SAP material code. |
| Material description | |
| Total QTY | Accumulated pressed volume. |
| Tool No. | Tool identifier. |
| Work center | Short WC code. May be `#N/A` for rows pending master-data completion. Joins to `2_1` as `P01_{Plant}_{Work center}`. |
| Group | SAP routing group. |
| Cycle times Standard Value (Machine) | Per-piece time. Unit: SAP convention — confirm in your analysis. |
| OPS plan GD | OPS plan Gross Demand — accumulated planned volume per tool. Useful for maintenance prioritization. |
| Rev no | Version. **Different Rev no's for the same material cannot be freely substituted** — wrong revision can cause product failure. |
| Material Status | Active / Phase-out. |

---

## 3_1 Inventory ATP

Current inventory snapshot per plant × material, showing on-hand stock, in-transit stock, safety stock, and various valuations in EUR.

- **Grain:** one row per plant × material. Covers only actively-tooled materials.
- **Approximate size:** ~7,600 rows.

Selected columns:

| Column | Unit | Notes |
|--------|------|-------|
| Source system ID | | Always `P01`. |
| Plant (code) / Plant (name) | | |
| Calendar day | date str | Snapshot date. |
| Operation Group | | |
| Material Unique (code) / (name) | | |
| Stock Qty | PCS | On-hand. |
| ATP Quantity | PCS | Available to promise. |
| ATP Qty (allow negative) | PCS | |
| Reserved Stock Qty | PCS | |
| Stock in Transit Qty | PCS | **Separate from on-hand stock — do not sum them blindly.** |
| Safety Stock Qty / Minimum Safety Stock Qty | PCS | |
| Stock Value (EUR) / ATP Stock Value (EUR) / Reserved Stock Value (EUR) / Safety Stock Value (EUR) / Stock in Transit Value (EUR) / Total Stock Value (EUR) | EUR | EUR currency is embedded in the column name. |

---

## 3_2 Component_SF_RM

Bill of Materials — the relationship from finished goods (plates, gaskets) down to raw materials (coils, rubber compounds).

- **Grain:** one row per (header material × component material). Covers only actively-tooled materials.
- **Approximate size:** ~9,500 rows.

| Column | Notes |
|--------|-------|
| Header Material | `P01_{Plant}_{FinishedMaterial}`. |
| Component Material | `P01_{Plant}_{RawMaterial}`. |
| Header Material code | Just the finished material code (useful for joins). |
| Component Material code | Just the raw material code. |
| Component Quantity | Qty of component per 1 unit of header (KG for coils/compounds). |
| Component BUoM | Unit (KG, M, PC…). |
| Component Description | Raw material description. |
| Production LT in Weeks | Component lead time. |
| Component Scrap (perc) / Assembly Scrap (perc) | Scrap rates. |
| Component Scrap Factor / Assembly Scrap Factor / Total Scrap Factor | Multipliers. |
| Effective Component Quantity | `Component Quantity × Total Scrap Factor`. |
| Plant | `P01_{Plant}_{PlantName}`. |
| Header OPS Group / Component OPS Group | |
| Comp Plate/Gasket | Whether the header is a plate or a gasket. |
| Header Description | |
| Version / Usage / BOM Status | |

**Notes**
- BOMs are **plant-specific** — the same finished material at two different plants can use different components.
- Some plate items use two components (co-extruded); most use one.

---

## Cross-sheet join quick reference

```
1_1 / 1_2  (pipeline demand)
   |-- Connector Plant_Material nr  ──►  2_6.Connector
   |-- Project_name                 ──►  1_3.Project name
   └── Work center                  ──►  2_1.Work center code as P01_{Plant}_{WC}
                                     ──►  2_5 via Plant + WC-Description

2_6  (core join table)
   |-- Sap code                     ──►  2_3.Sap code
   |-- Plant + Work center          ──►  2_5 via Plant + WC-Description
   └── Plant + Material             ──►  2_2 via P01_{Plant}_{Material}
                                     ──►  3_1 via Plant + Material code
                                     ──►  3_2 via Header Material code

3_2  (BOM)
   └── Component Material code      ──►  3_1 (via component in inventory)

2_4  (calendar)
   └── Week Number / Month Number   ──►  aggregation between 2_1/2_2 (weekly) and 1_1/1_2 (monthly)
```

---

## Data quality notes

The data has real-world imperfections, left in deliberately:

- **Missing connectors** in `1_1` / `1_2` (rows with `_` and placeholder strings `Missing CT`, `Missing WC`, `Missing tool`) — master-data gaps.
- **Occasional `#N/A` values** in `2_6.Work center` — pending master-data update. pandas reads these as NaN unless you pass `keep_default_na=False`.
- **Rev no drift** — the same material can appear with different Rev no's at different plants. Many materials have 2–3 Rev no's across the five-plant network.
- **Project list lag** — a small number of pipeline projects in `1_1` / `1_2` have not yet been reflected in `1_3 Export Project list`.

Each one is a decision point, not a bug. Document your handling in your README.
