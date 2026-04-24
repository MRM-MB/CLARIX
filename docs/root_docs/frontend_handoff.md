# frontend_handoff.md
## Clarix — Frontend Handoff Document

Date: 2026-04-18  
Wave: 5 (Final)

---

## How to Run the Frontend

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Required) Pre-generate Wave 6/7 processed CSVs
python -m project.src.wave6.runner
python -m project.src.wave7.runner

# 3. Start the dashboard
streamlit run app.py

# 4. Optional: set Anthropic API key for Ask Clarix live mode
export ANTHROPIC_API_KEY=sk-ant-...
```

The app opens at `http://localhost:8501`. First load parses `data/hackathon_dataset.xlsx` (~10s); subsequent page navigations are instant due to `@st.cache_resource`.

---

## Where the Main Pages Live

All page routing is in **`app.py`** — one file, no sub-page files.

| Page | Routing Condition | Approx. Line | Status |
|------|------------------|--------------|--------|
| Executive overview | `if page == "Executive overview"` | ~607 | ACTIVE — story page 2 |
| Scope & Region | `if page == "Scope & Region"` | ~1633 | ACTIVE — story page 1 |
| Quarter History | `elif page == "Quarter History"` | ~1825 | ACTIVE — story page 3 |
| Capacity & Maintenance | `elif page == "Capacity & Maintenance"` | ~2040 | ACTIVE — story page 4 |
| Sourcing & Delivery | `elif page == "Sourcing & Delivery"` | ~2203 | ACTIVE — story page 5 |
| Logistics & Disruptions | `elif page == "Logistics & Disruptions"` | ~1199 | ACTIVE — story page 6 |
| Final Actions | `elif page == "Final Actions"` | ~2375 | ACTIVE — story page 7 |
| Capacity planner | `elif page == "Capacity planner"` | ~790 | ACTIVE — classic engine |
| Bottlenecks | `elif page == "Bottlenecks"` | ~828 | ACTIVE — classic engine |
| Sourcing & MRP | `elif page == "Sourcing & MRP"` | ~888 | ACTIVE — classic engine |
| What-if planner | `elif page == "What-if planner"` | ~929 | ACTIVE — classic engine |
| Ask Clarix | `elif page == "Ask Clarix"` | ~1141 | ACTIVE — agent chat |
| Actions (old) | `elif page == "Actions"` | ~1434 | DEPRECATED — dead code, not in sidebar |

The sidebar `st.radio` in the `with st.sidebar:` block controls which pages are reachable. The deprecated "Actions" page is not listed there and will never render during normal use.

---

## Where the Shared Components Live

| Module | Path | Purpose |
|--------|------|---------|
| UI helpers | `clarix/ui.py` | KPI cards, empty states, assumption panels, why-panel, data source strips |
| Chart factories | `clarix/charts.py` | All Plotly chart functions, dark-themed via `_theme()` |
| Data loader | `clarix/data_loader.py` | Excel → `CanonicalData` dataclass; `load_canonical()` entry point |
| Engine | `clarix/engine.py` | Capacity maths, bottleneck detection, MRP, scenario simulation |
| Agent | `clarix/agent.py` | Claude `tool_use` agent; `run_agent()` + `_fallback_planner()` |
| Demo adapter | `project/src/app/demo_layer.py` | Loads Wave 6/7 CSVs; `load_all_processed()`, `derive_planner_actions()`, `get_demo_summary()` |

The `clarix/` package is the classic engine. The `demo_layer.py` adapter bridges `clarix` pages to the pre-generated Wave 7 outputs.

---

## Where the Data Adapters Live

### Classic Engine Adapter
`clarix/data_loader.py` → `load_canonical(xlsx_path)` → returns `CanonicalData` (dataclass wrapping all 13 sheet DataFrames).  
Cached via `@st.cache_resource` in `app.py` (`_load_data()`).

### Wave 7 Adapter
`project/src/app/demo_layer.py` → `load_all_processed()` → returns dict of DataFrames keyed by logical name.  
Wrapped in `app.py` as `_load_w7()` with `@st.cache_data(ttl=300)`.

Key keys returned by `_load_w7()`:

| Key | Source CSV | Used By |
|-----|-----------|---------|
| `actions_v2` | `fact_planner_actions_v2.csv` | Final Actions, Overview |
| `integrated_risk` | `fact_integrated_risk_v2.csv` | Final Actions, Overview |
| `bottlenecks` | `fact_capacity_bottleneck_summary.csv` | Overview, Capacity & Maintenance |
| `sourcing` | `fact_scenario_sourcing_weekly.csv` | Sourcing & Delivery |
| `logistics` | `fact_scenario_logistics_weekly.csv` | Logistics & Disruptions |
| `capacity_weekly` | `fact_effective_capacity_weekly_v2.csv` | Capacity & Maintenance |
| `rollforward` | `fact_delivery_risk_rollforward.csv` | Quarter History, Sourcing & Delivery |
| `quarter_snapshot` | `fact_quarter_business_snapshot.csv` | Quarter History |
| `learning_signals` | `fact_quarter_learning_signals.csv` | Quarter History |
| `pipeline_quarterly` | `fact_pipeline_quarterly.csv` | Scope & Region |
| `region_scope` | `dim_region_scope.csv` | Scope & Region |
| `maintenance` | `fact_maintenance_impact_summary.csv` | Capacity & Maintenance |
| `delivery` | `fact_delivery_commitment_weekly.csv` | Sourcing & Delivery |

All CSVs live in `project/data/processed/`. If a file is missing, `_load_w7()` returns an empty DataFrame for that key and each page renders an `ui.empty_state()` instead of crashing.

---

## How Filters Work

### Global Sidebar Filters (all pages share these via `st.session_state`)

| Filter | Session Key | Default | Pages |
|--------|------------|---------|-------|
| Scenario (classic) | `scenario` | `"base"` | Capacity planner, Bottlenecks, Sourcing & MRP, Overview |
| W7 Scenario | `w7_scenario` | `"base"` | Final Actions, Sourcing & Delivery, Capacity & Maint., Logistics |
| Plant filter | `plant_filter` | `"All"` | Overview KPIs, Capacity planner |
| Region filter | `region` | first region in dim_region_scope | Scope & Region |
| Quarter filter | `selected_quarter` | most recent quarter_id | Quarter History, Sourcing & Delivery |
| Maintenance scenario | `maint_scenario` | `"base"` | Capacity & Maintenance |

### Page-Local Filters
**Final Actions** has its own filter bar (scenario, action_type, plant, min_confidence) stored in local widget state — not persisted to session_state.

### How to add a new global filter
1. Add the `st.sidebar.*` widget in the sidebar block (search for `# --- GLOBAL FILTERS ---`)
2. Write to `st.session_state["your_key"]`
3. Read `st.session_state.get("your_key", default)` inside any page block

---

## How Demo Mode Works

### Toggle
Sidebar bottom button: **"▶ Start 3-Min Demo"** / **"◼ Exit Demo Mode"**  
Sets `st.session_state["demo_mode"] = True/False`.

### Step Banners
`_DEMO_STEPS` dict in `app.py` (module level) maps page name → `(step_num, title, desc, next_hint)`.  
`_render_demo_banner(page_name)` is called as the last line of `page_header()`, so every story page gets a banner automatically when demo mode is on.

Banner shows:
- 7 progress pips (filled = current step, grey = future)
- Step number + title
- One-sentence description
- Next step hint

### Story Pages Order
1. Scope & Region
2. Executive overview
3. Quarter History
4. Capacity & Maintenance
5. Sourcing & Delivery
6. Logistics & Disruptions
7. Final Actions

### Extending Demo Mode
Add a new story page to `_DEMO_STEPS` with a step number and set `next_hint` on the preceding page.

---

## What Assumptions the Frontend Surfaces

Every Wave 7 advanced page uses `ui.assumption_panel()` or `ui.data_source_strip()` to make synthetic data visible.

| Location | Assumption surfaced |
|----------|-------------------|
| Logistics & Disruptions | Shipping lanes, country cost indices, disruption scenarios are SYNTHETIC |
| Capacity & Maintenance | Maintenance windows use a synthetic downtime model |
| Sourcing & Delivery | Demand projections are probability-weighted estimates |
| Scope & Region | Coverage limited to 3 highest-revenue plants (demo scope filter) |
| Data source strip (all pages) | REAL DATA vs SYNTHETIC badges per data source |

The `ui.assumption_panel(text)` call renders a non-intrusive slate callout. The `ui.data_source_strip(sources)` call renders pill-style REAL/SYNTHETIC/DERIVED/ENRICHED badges.

---

## How to Extend Pages After the Hackathon

### Add a new chart to an existing page
1. Write the chart factory in `clarix/charts.py` following the `_theme(fig)` pattern (dark background, Inter font)
2. Import it at the top of `app.py` alongside the existing chart imports (~line 20)
3. Call it inside the relevant page routing block

### Add a new page
1. Add the page name to the `st.radio` options in the sidebar
2. Add `elif page == "New Page":` block after the existing routing chain
3. Start with `page_header("New Page", "subtitle")` — this wires demo banners automatically
4. Add `ui.data_source_strip([...])` to declare data provenance

### Add a new Wave 7 CSV
1. Add the filename to `_REAL_FILES` in `project/src/app/demo_layer.py`
2. Add a key to `_load_w7()` fallback dict in `app.py`
3. Reference `w7["new_key"]` in the page that needs it

### Switch from demo data to live data
Replace `_load_w7()` calls with a direct database/API adapter. The page logic does not need to change — it only requires a dict of DataFrames with the same keys.
