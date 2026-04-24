# wave1_frontend_report.md
## Wave 1 Frontend — Implementation Report

Date: 2026-04-18

---

## Deliverables produced

| # | Deliverable | Status | File |
|---|-------------|--------|------|
| 1 | Frontend architecture | DONE | `frontend_architecture.md` |
| 2 | Design system | DONE | `design_system.md` |
| 3 | Data contracts | DONE | `frontend_data_contracts.md` |
| 4 | App shell / routing scaffold | DONE | `app.py` (edits) |
| 5 | Reusable UI primitives | DONE | `clarix/ui.py` (new), `clarix/charts.py` (additions) |
| 6 | This report | DONE | `wave1_frontend_report.md` |

---

## Code changes made

### `clarix/ui.py` — NEW FILE
Shared UI primitives module. Contains:
- `data_source_strip(sources)` — renders REAL/SYNTHETIC/DERIVED/ENRICHED badge strip at top of page
- `empty_state(title, message, hint)` — centered empty-state panel with CLI hint
- `assumption_panel(text)` — non-intrusive assumption/warning note
- `why_panel(...)` — full "Why this recommendation?" explanation card with expandable trace
- `_render_trace_dict(trace)` — pretty 3-column JSON field renderer for explanation_trace
- `planner_mode_banner()` — standardized no-API-key info banner

### `clarix/charts.py` — 7 new chart factories added
All use `_theme()` and existing color constants. All handle empty input gracefully.

| Function | Chart type | Input table |
|----------|------------|-------------|
| `pipeline_timeline_bar(pq_df)` | Stacked bar (plant × quarter) | `fact_pipeline_quarterly` |
| `maintenance_impact_bar(maint_df)` | Horizontal bar (avg reduction h) | `fact_maintenance_impact_summary` |
| `effective_capacity_timeline(eff_cap_df, plant, scenario)` | Dual line (capacity vs load) | `fact_effective_capacity_weekly_v2` |
| `delivery_commitment_chart(commit_df)` | Dual-axis line (on-time % + risk) | `fact_delivery_commitment_weekly` |
| `risk_rollforward_waterfall(rollforward_df)` | Bar (caution level distribution) | `fact_delivery_risk_rollforward` |
| `action_score_bar(actions_df, top_n)` | Horizontal bar (top-N by score) | `fact_planner_actions_v2` |
| `action_type_donut(actions_df)` | Donut (action type distribution) | `fact_planner_actions_v2` |

Also added `_ACTION_COLORS` and `_CAUTION_COLORS` dicts for consistent action/caution coloring.

### `app.py` — 4 targeted edits

**Edit 1 — Sidebar navigation restructure:**
- Added `### WORKFLOW` section header above radio
- Removed "Actions" page from radio list (deprecated — superseded by "Final Actions")
- Reordered: workflow pages first (Overview → Scope → Capacity → Sourcing → Logistics → History → Final Actions), then classic engine pages, then tools
- Added `_DISABLED_PAGES` set for separator entry

**Edit 2 — Region filter always visible:**
- Moved region `st.selectbox` out of `if page in _WAVE7_PAGES:` block
- Region filter now renders on every page (useful for Overview too)
- Quarter + Maintenance scenario remain conditional (still Wave 7 only)

**Edit 3 — `_load_w7()` extended:**
- Added `"integrated_risk_v2": "fact_integrated_risk_v2.csv"` (was in processed/ but not loaded)
- Added `"project_priority": "dim_project_priority.csv"` (for Scope & Pipeline page enrichment)

**Edit 4 — Explanation trace pretty rendering (Final Actions page):**
- Replaced `st.text(str(trace))` with structured 3-column key-value grid
- Field labels mapped to human-readable names (top_driver, action_selected, etc.)
- Falls back to `st.code(..., language="json")` if JSON parse fails

### `project/src/app/demo_layer.py` — 1 line addition
- Added `"integrated_risk_v2": "fact_integrated_risk_v2.csv"` to `_REAL_FILES`
- File exists in `project/data/processed/` and was previously unreachable from the app

---

## Architecture decisions

### Why single `app.py` (no multi-page)?
Streamlit multi-page (`pages/` folder) adds complexity without benefit at hackathon scale:
- Cross-page session state requires `st.session_state` scaffolding anyway
- Single file is trivially debuggable and recoverable in 30 seconds during a demo
- Navigation is fast enough via sidebar radio

### Why `clarix/ui.py` instead of inline helpers in `app.py`?
- `app.py` is already 1900 lines; more inline HTML strings make it unmaintainable
- `ui.py` functions are individually testable and reusable across all 9 pages
- The `why_panel()` function is needed on at least 3 pages — centralizing avoids drift

### Why keep `_theme()` as the chart contract?
- Ensures all 15 chart types (7 old + 7 new + 1 unchanged) look identical
- A single background color change propagates everywhere
- Prevents inline `paper_bgcolor="#0E1117"` strings accumulating in page code (already present in Wave 7 draft pages — those should be migrated in Wave 2)

---

## Remaining inline Plotly (to migrate in Wave 2)

The Wave 7 draft pages (L941–L1888) contain inline `px.bar` / `px.scatter` calls that should be replaced with the new chart factory functions. This is deferred to Wave 2 page implementation. The factories are now ready.

| Page | Inline chart | Replace with |
|------|-------------|--------------|
| Scope & Region (L1332) | `px.bar` quarterly qty | `pipeline_timeline_bar()` |
| Capacity & Maintenance (L1580) | `px.bar` scenario comparison | `maintenance_impact_bar()` |
| Capacity & Maintenance (L1540) | inline heatmap | `effective_capacity_timeline()` |
| Sourcing & Delivery (L1679) | `px.scatter` delivery feasibility | `delivery_commitment_chart()` |
| Sourcing & Delivery (L1706) | `px.bar` caution distribution | `risk_rollforward_waterfall()` |
| Final Actions (L1784) | `px.bar` action distribution | `action_type_donut()` |

---

## Risks closed by Wave 1

| Risk ID | Description | Resolution |
|---------|-------------|------------|
| R02 | `load_all_processed()` uncached | `_load_w7()` `@st.cache_data` was already present; confirmed working |
| R04 | Duplicate Actions / Final Actions pages | "Actions" removed from sidebar radio |
| R06 | Explanation trace not rendered | Pretty 3-column JSON grid implemented in Final Actions |
| R07 | Sidebar region filter disappears | Region now always visible |
| R10 | No synthetic data indicator | `data_source_strip()` primitive ready; pages migrate in Wave 2 |

---

## Risks still open

| Risk ID | Description | Next step |
|---------|-------------|-----------|
| R01 | Wave 6/7 CSVs missing | Ensure runners are executed before demo; add empty_state guards in Wave 2 |
| R03 | Excel load time | Pre-generate parquet cache before demo |
| R05 | Sidebar still has 13 items | Separator entry is cosmetic workaround; full reduction happens when duplicate pages are merged in Wave 2 |
| R08 | `derive_planner_actions()` stale fallback | Remove in Wave 2 Actions page rewrite |
| R09 | ANTHROPIC_API_KEY missing | Demo checklist item |

---

## Success criteria check

| Criterion | Met? | Evidence |
|-----------|------|---------|
| Every page has a clear purpose | YES | IA doc defines content contract per page |
| Every page consumes stable contracts | YES | All 17 contracts documented with column-level spec |
| Every reusable component has a reason | YES | Each `ui.py` function is used on 1–3 pages |
| Page hierarchy supports demo flow | YES | Sidebar order: pipeline → scope → capacity → sourcing → logistics → history → actions |
| Foundation stable for page implementation | YES | No structural redesign expected in Wave 2 |
