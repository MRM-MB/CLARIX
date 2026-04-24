# frontend_qa_report.md
## Wave 4 — Frontend QA Report

Date: 2026-04-18

---

## Navigation QA

| Route | Status | Notes |
|-------|--------|-------|
| Executive overview | PASS | KPIs + W7 layer + "How the engine works" visible |
| Scope & Region | PASS | Region selector, pipeline timeline, factory drilldown, data coverage panel |
| Capacity & Maintenance | PASS | Effective capacity timeline, maintenance impact bar, bottleneck cards |
| Sourcing & Delivery | PASS | Shortage table, order-by recs, material criticality, delivery chart |
| Logistics & Disruptions | PASS | Route risk panel, landed cost chart, disruption compare, mitigation summary |
| Quarter History | PASS | Quarter selector, Q-over-Q compare, carry-over cards, learning signals |
| Final Actions | PASS | Filters, top-3 cards, charts, ranked table, why-panel, scenario compare |
| Capacity planner | PASS | Utilization heatmap + lines (classic engine) |
| Bottlenecks | PASS | Bottleneck table + auto-explanation |
| Sourcing & MRP | PASS | BOM-backed sourcing table |
| What-if planner | PASS | Basket + feasibility check |
| Ask Clarix | PASS | Chat panel, planner-mode fallback |
| Separator entry | PASS | Does not crash, skipped gracefully |

---

## Filter Consistency QA

| Filter | Behaviour | Status |
|--------|-----------|--------|
| Global scenario | Propagates to Overview, Capacity planner, Sourcing & MRP, Logistics, Final Actions | PASS |
| W7 scenario | Propagates to Final Actions, Sourcing & Delivery, Capacity & Maintenance | PASS |
| Plant filter | Narrows pipeline + utilization on Overview and classic pages | PASS |
| Region filter | Always visible, used by Scope & Region page | PASS |
| Quarter filter | Used by Quarter History, Sourcing & Delivery (rollforward) | PASS |
| Maintenance scenario | Used by Capacity & Maintenance | PASS |
| Per-page action filter | Final Actions filter (scenario, type, plant, confidence) is page-local | PASS |

---

## Fallback / Empty State QA

| Condition | Behaviour | Status |
|-----------|-----------|--------|
| Missing fact_planner_actions_v2 | `ui.empty_state()` + `st.stop()` on Final Actions | PASS |
| Missing fact_effective_capacity_weekly_v2 | `ui.empty_state()` shown, page continues | PASS |
| Missing fact_scenario_sourcing_weekly | `ui.empty_state()` shown in shortage section | PASS |
| Missing fact_scenario_logistics_weekly | `ui.empty_state()` + `st.stop()` on Logistics page | PASS |
| No shortages in scenario | `st.success("No shortages")` green banner | PASS |
| No caution projects in quarter | `st.success("No carry-over caution")` | PASS |
| Scenario filter returns empty DataFrame | Each chart/table shows empty state, no crash | PASS |
| `ANTHROPIC_API_KEY` missing | Planner-mode banner shown on Ask Clarix | PASS |
| Excel not found | `load_canonical` raises, Streamlit shows error block | EXPECTED |

---

## Visual Consistency QA

| Item | Status | Notes |
|------|--------|-------|
| Font: Inter across all pages | PASS | CSS import + `font-family` on all elements |
| KPI cards: 4 styles (accent/warn/ok/slate/info) | PASS | `kpi-info` added in Wave 4 CSS |
| Section headers: red left-bar motif | PASS | `.section-h::before` on all `section()` calls |
| Pills: ok/warn/crit/slate/info | PASS | Defined in CSS, used consistently |
| Dark background `#0E1117` | PASS | Global `--bg` variable used everywhere |
| Plotly charts: `paper_bgcolor="#0E1117"` | PASS | All new charts use `_theme()` or explicit dark layout |
| Interpretation blocks: slate background | PASS | Present on all 4 Wave 3 pages + Wave 2 Actions page |
| `ui.data_source_strip()` | PASS | Present on all Wave 2–3 pages |
| `ui.assumption_panel()` | PASS | Used on Scope & Region + Quarter History |
| `_DASH` constant used instead of `'\u2014'` in f-strings | PASS | Replaced in Wave 2 fix |

---

## Terminology Consistency QA

| Term | Used on | Status |
|------|---------|--------|
| "Planner action" / "action" | Final Actions, Overview, Why panel | PASS — consistent |
| "Scenario" (pessimistic/base/optimistic) | All pages using scenario filter | PASS |
| "Risk score v2" | Integrated risk references | PASS |
| "Quarter" / "quarter_id" | Quarter History, rollforward, caution panels | PASS |
| "Effective capacity" vs "Nominal capacity" | Capacity & Maintenance only | PASS |
| "Shortage" / "shortage_flag" | Sourcing & Delivery only | PASS |
| "Carry-over caution" | Quarter History + Sourcing & Delivery | PASS |
| "Landed cost proxy" | Logistics only, labelled SYNTHETIC | PASS |

---

## Presentation Readiness QA

| Check | Status |
|-------|--------|
| Every page has a clear title and one-sentence subtitle | PASS |
| Every Wave 3 advanced page has a "What this means" block | PASS |
| Top recommendation visible on Overview without scrolling | PASS — top-3 action cards above fold |
| Top risk visible on Overview without scrolling | PASS — top-5 bottleneck cards |
| Demo mode toggle available in sidebar | PASS |
| Demo mode shows step banner + progress pips on all 7 story pages | PASS |
| "How the engine works" explainer on Overview | PASS |
| Product owner can understand page purpose without code explanation | PASS |

---

## Known Issues / Accepted Risks

| ID | Description | Severity | Mitigation |
|----|-------------|----------|------------|
| R01 | Wave 6/7 CSVs must be pre-generated before demo | HIGH | Run `python -m project.src.wave7.runner` before demo |
| R02 | Excel load time ~10s on first run | MEDIUM | Pre-warm with one page load; `@st.cache_resource` holds it |
| R03 | Plotly charts fail if `plotly` not installed | HIGH | `pip install -r requirements.txt` |
| R04 | `ANTHROPIC_API_KEY` not set → Ask Clarix in planner mode | LOW | Expected fallback; demo script avoids Ask Clarix |
| R05 | `kpi-info` style used but pill class `pill-info` pre-existing | LOW | Both defined; no conflict |
| R06 | `effective_capacity_timeline()` requires `work_center` column | MEDIUM | Graceful fallback to `ui.empty_state()` if column missing |
| R07 | Demo mode does not force filter values | LOW | All defaults already set to best demo values (base scenario, Q1, first region) |
