# frontend_information_architecture.md
## Target Information Architecture

Date: 2026-04-18

---

## Core narrative

The dashboard tells one story from left to right in the sidebar:

> **Uncertain sales pipeline → prioritized projects → production load → material gaps → logistics risk → what did we learn → what should the planner do now**

Every page is a chapter in that story. The user should never wonder "why am I seeing this?" — each page flows from the previous one.

---

## Top-level navigation

```
CLARIX
Capacity & Sourcing Engine
────────────────────────────

WORKFLOW ──────────────────
  ○ Overview
  ○ Scope & Pipeline
  ○ Capacity & Maintenance
  ○ Sourcing & Delivery
  ○ Logistics & Disruptions
  ○ Quarter History
  ○ Actions & Recommendations

TOOLS ─────────────────────
  ○ What-if planner
  ○ Ask Clarix

────────────────────────────
Scenario  [dropdown]
Plant     [dropdown]
Region    [dropdown]
────────────────────────────
```

---

## Page hierarchy and content contract

### WORKFLOW pages

---

#### 1. Overview
**Story beat:** "Here is the current risk profile in one glance."
**Primary audience:** Executive, planner, demo judge (first impression)

**KPI row 1** (clarix engine):
- Pipeline value all-in (€M)
- Expected pipeline value (€M, qty × prob)
- Peak utilization across all WCs
- Bottleneck work centers count

**KPI row 2** (Wave 6/7 data, shown only if available):
- Avg integrated risk score
- High-priority planner actions (score > 0.6)
- Sourcing shortage rows
- Delivery commitment gaps

**Charts:**
- Pipeline scenario funnel (all-in → expected → high-confidence)
- Scenario comparison bar (4 scenarios × peak util)
- Demand mix treemap (plant → type → material)

**Graceful degradation:** KPI row 2 hidden with `st.info("Wave 6/7 data not yet generated — run the pipeline first.")` when CSVs missing

---

#### 2. Scope & Pipeline
**Story beat:** "Here is what we think is coming, and which factories are in scope."
**Primary audience:** Planner, supply-chain lead

**KPI row:**
- Active scope (plants in scope)
- Projects in pipeline (count by probability tier)
- Total expected pieces (probability-weighted)
- Horizon (months)

**Content:**
- Scope table: `dim_region_scope` — scope_id, region, plants, active flag
- Pipeline timeline: stacked monthly bar, probability-weighted vs all-in, split by plant
- Project list: `dim_project_priority` — name, probability, revenue_tier, delivery date, region
- What's synthetic vs real: `dim_service_level_policy_synth` badge if present

**Data sources:** `dim_region_scope`, `dim_project_priority`, `fact_pipeline_quarterly`, `fact_pipeline_monthly`

---

#### 3. Capacity & Maintenance
**Story beat:** "Can the factories actually produce this? Where are the breaking points?"
**Primary audience:** Production planner, factory manager

**Tabs:**
1. **Heatmap** — utilization heatmap (top-N WCs, weekly × WC); WC drilldown bar chart
2. **Bottlenecks** — ranked bottleneck table; explain-constraint auto-analysis of worst WC
3. **Maintenance Impact** — maintenance scenario comparison; avg reduction hours by plant/WC; effective capacity bottleneck weeks; KPIs: worst week, pct capacity lost, delta overload hours

**Sidebar filter active on this page:** Scenario, Plant, Maintenance scenario

**Data sources:**
- Tabs 1–2: `clarix/engine.build_utilization()`, `detect_bottlenecks()`
- Tab 3: `fact_maintenance_impact_summary`, `fact_effective_capacity_weekly_v2`

---

#### 4. Sourcing & Delivery
**Story beat:** "Do we have the materials? Can we commit to delivery dates?"
**Primary audience:** Sourcing manager, supply-chain lead

**Tabs:**
1. **MRP Recommendations** — BOM-exploded component shortfalls vs ATP; order-by table; urgent counter (≤ 4 weeks)
2. **Delivery Commitments** — `fact_delivery_commitment_weekly` line chart; committed vs required by plant/week; shortage flags from `fact_scenario_sourcing_weekly`

**Sidebar filter active:** Scenario, Plant

**Data sources:**
- Tab 1: `clarix/engine.sourcing_recommendations()`
- Tab 2: `fact_delivery_commitment_weekly`, `fact_scenario_sourcing_weekly`

---

#### 5. Logistics & Disruptions
**Story beat:** "What happens if a route fails or a plant goes down?"
**Primary audience:** Logistics lead, supply-chain manager

**KPI row:**
- Active logistics scenarios
- At-risk delivery weeks
- Carry-over risk (from rollforward)
- Reroute opportunities

**Content:**
- Delivery risk rollforward waterfall: `fact_delivery_risk_rollforward` — shows risk trajectory quarter-over-quarter
- Disruption scenario table: `fact_scenario_logistics_weekly` — scenario × plant × week × shortage flag
- Maintenance-induced disruption: cross-reference with maintenance scenario (sidebar)

**Sidebar filter active:** Scenario, Plant, Maintenance scenario

**Data sources:** `fact_delivery_risk_rollforward`, `fact_scenario_logistics_weekly`, `fact_delivery_commitment_weekly`

---

#### 6. Quarter History
**Story beat:** "What did we learn last quarter? What caution flags carry into this one?"
**Primary audience:** Planner, capacity analyst

**KPI row:**
- Quarters tracked
- Learning signals flagged
- Service caution carry-overs
- Prior violation risk (avg)

**Content:**
- Service memory table: `fact_quarter_service_memory` — scope, quarter, project, caution flag, prior risk
- Learning signals table: `fact_quarter_learning_signals` — signal type, value, trend direction
- Carry-over caution highlight: rows where `carry_over_service_caution_flag = True` shown in amber/red

**Sidebar filter active:** Region, Quarter

**Data sources:** `fact_quarter_service_memory`, `fact_quarter_learning_signals`, `fact_quarter_rollforward_inputs`

---

#### 7. Actions & Recommendations
**Story beat:** "Given everything above — what should the planner do, ranked by urgency?"
**Primary audience:** Planner, demo judge (closing impression)

**KPI row:**
- Total actions this quarter
- High-priority (score > 0.6)
- Maintenance-specific actions (shift_maintenance + protect_capacity_window)
- Avg confidence

**Content:**
- Action score bar chart: top 20 actions sorted by adjusted_action_score, colored by action_type
- Action type distribution donut
- Action table: scope_id, scenario, project_id, plant, quarter_id, action_type, action_score, confidence, reason, expected_effect
- Explanation trace expander: show JSON fields (top_driver, action_selected, maint_severity, caution_carry_over, reroute_target)
- Filter: scope, scenario, quarter, action_type

**Sidebar filter active:** Region, Quarter, Scenario

**Data sources:** `fact_planner_actions_v2`

---

### TOOLS pages

---

#### What-if planner
**Story beat:** "I want to test if a new project fits before committing."
**Primary audience:** Planner, sales manager

**Content (unchanged from current):**
- Add-project form (plant, material, quarter, qty, probability, spread)
- Basket view
- Feasibility verdict per project
- Quarter-by-quarter impact table

---

#### Ask Clarix
**Story beat:** "I have a question the dashboard doesn't directly answer — ask the AI."
**Primary audience:** Any user; primary demo showpiece for judges

**Content (unchanged from current):**
- Suggested questions
- Chat input
- Tool call trace (shows which tools were called)
- Answer with source scenario noted

---

## Page flow diagram

```
Overview
   │
   ▼
Scope & Pipeline ──────────────────────────────────────────────┐
   │                                                            │
   ▼                                                            │
Capacity & Maintenance (Heatmap / Bottlenecks / Maintenance)   │
   │                                                            │
   ▼                                                            │
Sourcing & Delivery (MRP / Delivery Commitments)               │
   │                                                            │
   ▼                                                            │
Logistics & Disruptions                                        │
   │                                                            │
   ▼                                                            │
Quarter History                                                │
   │                                                            │
   ▼                                                            │
Actions & Recommendations ◄────────────────────────────────────┘
   │
   ▼
[Ask Clarix / What-if planner — accessible from any step]
```

---

## Data visibility rules

| Data type | Visibility treatment |
|-----------|---------------------|
| Real processed data (project/data/processed/*.csv) | Shown normally |
| Synthetic data (dim_service_level_policy_synth.csv) | Show `SYNTHETIC` badge in section header |
| Missing Wave 6/7 CSVs | `st.info()` with instruction to run pipeline runner |
| Assumptions in explanation_trace | Show in collapsible expander, not inline |
| Scenario confidence | Show as small badge next to KPIs, not as primary metric |

---

## Responsive layout rules

| Layout pattern | Usage |
|----------------|-------|
| 4 columns | KPI rows (top of every page) |
| 2 columns 50/50 | Side-by-side charts |
| 1 column full-width | Heatmaps, data tables, action bars |
| `st.tabs()` | Pages with 3+ sub-views (Capacity, Sourcing) |
| `st.expander()` | Explanation traces, methodology notes |

---

## URL / state mapping (session_state keys)

| Key | Type | Used on |
|-----|------|---------|
| `basket` | list[dict] | What-if planner |
| `chat` | list[dict] | Ask Clarix |
| `feas_result` | dict | What-if planner |
| *(new)* `w7_data` | dict[str, DataFrame] | All Wave 7 pages (via `@st.cache_data`) |
