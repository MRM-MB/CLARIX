# frontend_architecture.md
## Frontend Architecture — Wave 1

Date: 2026-04-18

---

## Architecture overview

Single-file Streamlit application (`app.py`) with a modular backend in `clarix/`.
No multi-page restructure is needed for hackathon scope — one file keeps the demo simple and fast to recover from errors.

```
app.py                          ← app shell, routing, global state, all page renderers
clarix/
  data_loader.py                ← Excel → 8 canonical DataFrames (KEEP, unchanged)
  engine.py                     ← capacity / bottleneck / sourcing / what-if (KEEP, unchanged)
  charts.py                     ← Plotly factories + new Wave 1 chart types (ADAPT)
  agent.py                      ← Claude tool-use loop (KEEP, unchanged)
  ui.py                         ← [NEW] shared UI primitives (empty state, explanation panel,
                                     assumption badge, "why" panel, data-source strip)
project/
  src/app/demo_layer.py         ← Wave 6/7 CSV loader (KEEP, already fixed)
  data/processed/               ← all Wave 6/7 CSV outputs
```

---

## Folder structure

```
Hackathon-case3/
├── app.py                          ← entry point: streamlit run app.py
├── clarix/
│   ├── __init__.py
│   ├── agent.py                    ← KEEP
│   ├── charts.py                   ← ADAPT: add 7 new chart factories
│   ├── data_loader.py              ← KEEP
│   ├── engine.py                   ← KEEP
│   └── ui.py                       ← NEW: shared UI primitives
├── project/
│   ├── src/app/demo_layer.py       ← KEEP
│   └── data/processed/             ← CSV outputs from Wave 1–7 runners
├── frontend_audit.md
├── frontend_migration_plan.md
├── frontend_information_architecture.md
├── frontend_component_inventory.md
├── frontend_risk_register.md
├── frontend_architecture.md        ← this file
├── design_system.md
├── frontend_data_contracts.md
└── wave1_frontend_report.md
```

---

## Routing model

Streamlit has no true router. Navigation is a sidebar `st.radio` → Python `if/elif` dispatch.

### Navigation structure (Wave 1 target)

```python
page = st.radio("Navigate", [
    # --- WORKFLOW ---
    "1. Overview",
    "2. Scope & Pipeline",
    "3. Capacity & Maintenance",
    "4. Sourcing & Delivery",
    "5. Logistics & Disruptions",
    "6. Quarter History",
    "7. Actions & Recommendations",
    # --- TOOLS ---
    "What-if planner",
    "Ask Clarix",
], label_visibility="collapsed")
```

Section headers are rendered as `st.markdown("### WORKFLOW")` / `st.markdown("### TOOLS")` above the radio widget, with a reduced item count (9 from 13) achieved by merging duplicate pages.

### Page dispatch pattern

```python
_PAGE_DISPATCH = {
    "1. Overview":                    _page_overview,
    "2. Scope & Pipeline":            _page_scope_pipeline,
    "3. Capacity & Maintenance":      _page_capacity_maintenance,
    "4. Sourcing & Delivery":         _page_sourcing_delivery,
    "5. Logistics & Disruptions":     _page_logistics,
    "6. Quarter History":             _page_quarter_history,
    "7. Actions & Recommendations":   _page_actions,
    "What-if planner":                _page_whatif,
    "Ask Clarix":                     _page_ask_clarix,
}
_PAGE_DISPATCH[page]()
```

Each page is a top-level function. This replaces the current `if/elif` chains.

---

## Global state model

All filters live in `st.session_state` under a flat namespace. They are set in the sidebar before any page renders.

```python
# Set in sidebar, consumed by all pages
filters = {
    "scenario":           str,    # "expected" | "all_in" | "high_confidence" | "monte_carlo"
    "plant":              str | None,
    "scope_id":           str,    # from dim_region_scope.scope_id
    "region_name":        str,    # display name
    "quarter":            str,    # "2026-Q1" | ... | "all"
    "maintenance_scenario": str,  # from fact_effective_capacity_weekly_v2.scenario
    "work_center":        str | None,
    "priority_band":      str | None,  # "high" | "medium" | "low" | None
    "material_criticality": str | None,  # "A" | "B" | "C" | None
    "show_synthetic":     bool,   # True = show synthetic data with badge; False = hide
}
```

Filters are passed as a dict to each page function, never read from `st.session_state` inside page functions (avoids hidden coupling).

---

## Data loading architecture

Two data sources, both cached:

```
┌─────────────────────────────────────────────────────────────────────┐
│ SOURCE 1: hackathon_dataset.xlsx (26 MB, Excel)                      │
│   load_canonical() → CanonicalData (8 DataFrames)                   │
│   @st.cache_resource — loads once per process lifetime               │
│   parquet cache in data/.clarix_cache/ for fast restarts             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ SOURCE 2: project/data/processed/*.csv (Wave 6/7 outputs)            │
│   load_all_processed() → dict[str, pd.DataFrame] (17 keys)          │
│   @st.cache_data(ttl=300) — reloads every 5 min or on reset         │
│   graceful degradation: empty DataFrame + st.warning if file missing │
└─────────────────────────────────────────────────────────────────────┘
```

### Data adapter pattern

Each page receives pre-loaded data dicts. Pages do NOT call data loaders directly.

```python
# app.py top-level (runs once)
data   = get_canonical_data()   # @st.cache_resource wrapper
w7     = get_w7_data()          # @st.cache_data wrapper

# Page function signature
def _page_actions(filters: dict, data: CanonicalData, w7: dict) -> None:
    actions = w7.get("planner_actions_v2", pd.DataFrame())
    if actions.empty:
        ui.empty_state("No actions", "Run: python -m project.src.wave7.runner")
        return
    ...
```

---

## Loading, error, and empty states

All handled by `clarix/ui.py` primitives (see component inventory):

| State | Component | When |
|-------|-----------|------|
| CSV file missing | `ui.empty_state(title, hint)` | `df.empty` after `_load_w7()` |
| Excel loading | `st.cache_resource` spinner | First app launch |
| Heavy computation | `@st.cache_data` + `st.spinner()` | Utilization build, feasibility |
| Synthetic data | `ui.data_source_strip(sources)` | Top of every Wave 7 page |
| No filter results | `ui.empty_state()` | After applying plant/scenario filter |
| Agent no key | `ui.planner_mode_banner()` | Ask Clarix page |

---

## Chart strategy

All charts produced by `clarix/charts.py` factories. No inline Plotly in page functions.

Rules:
1. Every chart function returns `go.Figure`
2. Every chart function calls `_theme()` before return
3. Every chart function handles `df.empty` → `_theme(go.Figure(), title="No data")`
4. No `import plotly.express as px` inside page functions — only `from clarix.charts import ...`

Wave 1 adds 7 new factory functions. The inline `px.bar` / `px.scatter` calls in Wave 7 pages are migrated to these factories.

---

## Badge system for synthetic/enriched data

```python
# clarix/ui.py
DATA_BADGE = {
    "real":      ("<span class='pill pill-ok'>REAL</span>",      "Data from hackathon_dataset.xlsx"),
    "synthetic": ("<span class='pill pill-warn'>SYNTHETIC</span>", "Generated — do not use for production"),
    "derived":   ("<span class='pill pill-info'>DERIVED</span>",  "Computed from real + rules"),
    "enriched":  ("<span class='pill pill-slate'>ENRICHED</span>", "Real data with synthetic augmentation"),
}

def data_source_strip(sources: list[tuple[str, str]]) -> None:
    """Render the data provenance strip at top of page.
    sources: list of (badge_type, label) e.g. [("real", "fact_planner_actions_v2"), ("synthetic", "transit times")]
    """
```

---

## Session state keys (canonical list)

| Key | Type | Owner | Description |
|-----|------|-------|-------------|
| `basket` | `list[dict]` | What-if planner | Candidate project basket |
| `chat` | `list[dict]` | Ask Clarix | Chat turn history |
| `feas_result` | `dict` | What-if planner | Last feasibility run result |
| `pending` | `str` | Ask Clarix | Suggested-question click buffer |
| `filters` | `dict` | Sidebar | All global filter values (Wave 1 addition) |

---

## Performance targets

| Operation | Target | Method |
|-----------|--------|--------|
| App first load (warm cache) | < 3s | Parquet cache pre-generated |
| App first load (cold cache) | < 45s | Excel parse — show spinner |
| Page navigation | < 1s | All heavy compute cached |
| Wave 7 page load | < 0.5s | `_load_w7()` cached with `@st.cache_data` |
| Feasibility check (basket) | < 5s | `@st.cache_data` on run result |
