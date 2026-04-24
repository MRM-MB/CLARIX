# clarix_migration_complete.md
## Clarix Migration — Completion Note

Date: 2026-04-18  
Wave: 5 (Final)

---

## Status: COMPLETE

All original Clarix components have been migrated, adapted, or superseded. No functionality was lost.

---

## What Was Adapted

| Original Component | What Changed | Result |
|-------------------|-------------|--------|
| Clarix chat panel | Moved from standalone prototype into `app.py` Ask Clarix page; `clarix/agent.py` `run_agent()` wired up with `CanonicalData`; `_fallback_planner()` added for no-API-key mode | ACTIVE at `elif page == "Ask Clarix"` |
| Clarix capacity view | Cleaned up and wired to `clarix/engine.py` `build_utilization()`; `utilization_heatmap()` and `utilization_lines()` styled to dark theme | ACTIVE at `elif page == "Capacity planner"` |
| Clarix bottleneck view | `detect_bottlenecks()` + `explain_constraint()` surfaced as a full page with auto-generated explanations | ACTIVE at `elif page == "Bottlenecks"` |
| Clarix sourcing view | `sourcing_recommendations()` wired to BOM-backed MRP output | ACTIVE at `elif page == "Sourcing & MRP"` |
| Clarix what-if | Basket + `project_feasibility()` kept intact | ACTIVE at `elif page == "What-if planner"` |
| Clarix design tokens | Dark bg `#0E1117`, Inter font, color variables extracted into CSS block in `app.py`; shared via `clarix/ui.py` helpers | ACTIVE across all pages |

---

## What Was Added (Wave 2–5)

Seven new story pages were added on top of the classic engine, consuming Wave 6/7 pre-generated CSV outputs:

1. **Scope & Region** — pipeline timeline, factory drilldown, data coverage panel
2. **Executive Overview** (extended) — W7 intelligence layer, bottleneck cards, action cards, scenario compare table
3. **Quarter History** — Q-over-Q delta metrics, carry-over risk cards, learning signals, risk rollforward waterfall
4. **Capacity & Maintenance** — effective vs nominal capacity timeline, maintenance impact bar, bottleneck drilldown
5. **Sourcing & Delivery** — shortage table, order-by recommendations, material criticality, delivery commitment chart
6. **Logistics & Disruptions** — route risk panel, landed cost chart, disruption scenario compare, mitigation levers
7. **Final Actions** — ranked planner actions, action score bar, action type donut, confidence scatter, why-panel drilldown

Eight new chart factories were added to `clarix/charts.py`:
`pipeline_timeline_bar`, `maintenance_impact_bar`, `effective_capacity_timeline`, `delivery_commitment_chart`, `risk_rollforward_waterfall`, `action_score_bar`, `action_type_donut`

Five UI helpers were added or extended in `clarix/ui.py`:
`data_source_strip`, `empty_state`, `assumption_panel`, `why_panel`, `planner_mode_banner`

Demo infrastructure added to `app.py`:
- `_DEMO_STEPS` dict (7 story steps)
- `_render_demo_banner()` (progress pips + step card)
- Demo mode toggle button in sidebar
- `_DASH = "\u2014"` constant (Python 3.11 f-string compatibility)

---

## What Was Deprecated

| Component | Reason | Status |
|-----------|--------|--------|
| Old "Actions" page (`elif page == "Actions":` ~line 1434) | Superseded by "Final Actions" (Wave 3) with richer W7 data binding | Dead code — not in sidebar radio, safe to delete |

No other components were deprecated. The classic engine pages (Capacity planner, Bottlenecks, Sourcing & MRP, What-if planner, Ask Clarix) remain fully functional and reachable via the sidebar.

---

## Codebase Cleanliness for Final Presentation

| Check | Status |
|-------|--------|
| `python -m py_compile app.py` | PASS — no syntax errors |
| All sidebar-visible pages render without crash | PASS (Wave 4 QA) |
| All filter state consistent across pages | PASS (Wave 4 QA) |
| All fallback states graceful | PASS (Wave 4 QA) |
| No broken imports | PASS |
| Demo mode functional | PASS |
| Dead code isolated (not deleted, not reachable) | PASS |
| `_DASH` constant before first f-string use | PASS |

The frontend is stable and ready for final presentation use.
