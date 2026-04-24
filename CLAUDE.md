# Hackathon: Predictive Manufacturing — Capacity & Supply Chain Optimization

## Project Overview

Build an AI orchestration system for Danfoss Climate Solutions that predicts production capacity, simulates supply chain scenarios, and optimizes raw material sourcing across a global manufacturing network.

**Case Owner:** Daniel Parapunov, Danfoss Climate Solutions  
**Challenge Area:** AI modelling, production planning, supply chain optimization, scenario simulation, predictive analytics

---

## Problem Statement

Danfoss operates multiple factories globally, each with:
- Different machines, tooling, and pressing cycle times
- Mandatory tool maintenance windows and downtime
- A sales pipeline of unapproved projects with probability ratios (e.g., 50%)
- Raw material dependencies (metal coils, rubber compounds for gaskets)

The goal is to synthesize these variables into a system that can:
1. Forecast work center load and capacity bottlenecks
2. Simulate production scenarios under uncertainty
3. Predict raw material sourcing requirements and timing
4. Integrate tool downtime into scheduling logic

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | **Predictive Capacity Model** | Forecasts work center load and identifies bottlenecks per factory |
| 2 | **Scenario Simulation** | Runs production scenarios based on project probability ratios |
| 3 | **Smart Sourcing Forecast** | Automated predictions for timely raw material sourcing |
| 4 | **Downtime Integration** | Scheduling logic with tool maintenance and varied processing speeds |

---

## Data Sources

### Input Data

Single file: **`data/hackathon_dataset.xlsx`** (~26 MB, 13 sheets). Load with `pd.read_excel(path, sheet_name=...)` — row-1 headers, no skiprows needed.

| Sheet | Area | What it contains |
|-------|------|-----------------|
| `1_1 Export Plates` | Sales pipeline | Pipeline demand at plate-material granularity (~180 rows, monthly PCS × 36 months) |
| `1_2 Gaskets` | Sales pipeline | Same structure as 1_1, for gasket materials |
| `1_3 Export Project list` | Sales pipeline | Project metadata: probability (10/25/50/75/90%), delivery date, region, revenue tier (~720 rows) |
| `2_1 Work Center Capacity Weekly` | Capacity | Weekly plan vs. capacity per WC, 23 measures, 109 WCs × 15 plants (~2,500 rows × 190 cols) |
| `2_2 OPS plan per material` | Capacity | Ops plan disaggregated to plant × material × week in **pieces** (~30,000 rows) |
| `2_3 SAP MasterData` | Master data | Lead times, procurement type, safety stock, cost per plant × material (~7,600 rows) |
| `2_4 Model Calendar` | Master data | Day/week/month/holiday grid per plant for 2026–2028 — use to reconcile weekly vs monthly granularity |
| `2_5 WC Schedule_limits` | Master data | 5 shift levels per WC with OEE, breaks, weekly available hours (109 WCs × 5 = ~545 rows) |
| `2_6 Tool_material nr master` | Master data | **Core join table**: plant × material × tool × WC × cycle time (~7,600 rows) |
| `3_1 Inventory ATP` | Inventory | On-hand stock, in-transit, safety stock, ATP per plant × material (~7,600 rows) |
| `3_2 Component_SF_RM` | BOM | Finished good → raw material, with scrap factors and effective quantities (~9,500 rows) |
| `Flow` | Metadata | Human-readable flow diagram |
| `Savings per area` | Metadata | Reference only |

**Companion file:** `data/Data_Dictionary_overview.xlsx` — sheet-level summary. See `DATA_DICTIONARY.md` for full column reference.

### Key joins

```
1_1 / 1_2  →  2_6   via  Connector Plant_Material nr = Connector
1_1 / 1_2  →  1_3   via  Project_name = Project name
2_6        →  2_1   via  P01_{Plant}_{Work center} = Work center code
2_6        →  2_3   via  Sap code
2_6        →  3_1   via  Plant + Material code
2_6        →  2_2   via  P01_{Plant}_{Material}
3_2        →  3_1   via  Component Material code (raw material inventory)
2_4        →  all   granularity bridge: weekly (2_1/2_2) ↔ monthly (1_1/1_2)
```

### Data Model Concepts
- **15 plants** (`NW01`–`NW15`), 109 work centers, ~2,300 active materials, ~7,600 tool-material records
- A **Tool** can produce multiple material codes; the same tool number can exist at multiple plants (cross-factory substitution opportunity)
- A **Work Center** has one or more tools; capacity is expressed at WC level in hours
- **Cycle time** is in the `2_6` sheet (`Cycle times Standard Value (Machine)`) — SAP convention is minutes/piece; verify against `Total QTY` magnitudes
- **Available capacity** = shift hours × OEE − breaks (from `2_5`) − any maintenance windows you model
- **Probability-weighted demand**: `expected_units = project_units × probability` (probabilities are 10/25/50/75/90 integer %)
- `2_2` values are **pieces**, typically 0.001–0.2 per row per week — small because each row is one material's share
- Rev no matters: same material at different Rev no is **not interchangeable**

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Orchestration Layer                  │
│         (Claude API with tool use / agents)          │
└────────────┬──────────────────────┬─────────────────┘
             │                      │
    ┌────────▼────────┐    ┌────────▼────────┐
    │  Capacity       │    │  Sourcing       │
    │  Forecast Agent │    │  Forecast Agent │
    └────────┬────────┘    └────────┬────────┘
             │                      │
    ┌────────▼──────────────────────▼────────┐
    │           Core Engine (Python)          │
    │  - Scenario simulator                   │
    │  - Capacity calculator                  │
    │  - Bottleneck detector                  │
    │  - Material requirements planner (MRP)  │
    └────────┬────────────────────────────────┘
             │
    ┌────────▼────────────────────────────────┐
    │              Data Layer                  │
    │  hackathon_dataset.xlsx (13 sheets)     │
    └─────────────────────────────────────────┘
```

---

## Project Structure

```
sdu-ai-hackathon-case-3/
├── CLAUDE.md                        # This file
├── CASE_BRIEF.md                    # Problem statement from case owner
├── DATA_DICTIONARY.md               # Full column + join reference for all sheets
├── HINTS.md                         # Case owner suggestions and gotchas
├── README.md                        # Quick-start instructions
├── requirements.txt                 # Python deps (add anthropic, streamlit, scipy, python-dotenv)
├── data/
│   ├── hackathon_dataset.xlsx       # All data — 13 sheets, ~26 MB
│   └── Data_Dictionary_overview.xlsx# Sheet-level summary
├── notebooks/
│   └── starter_notebook.ipynb       # Loads every sheet, prints shape — start here for EDA
├── scripts/
│   └── generate_dataset.py          # How the dataset was generated (reference only, don't re-run)
├── src/                             # TO BUILD
│   ├── data_loader.py               # Load & validate all 13 sheets, handle NaN/#N/A/Missing* quirks
│   ├── capacity_engine.py           # WC available hours, probability-weighted demand, utilization %
│   ├── scenario_simulator.py        # Pessimistic / base / optimistic scenario logic
│   ├── mrp.py                       # Back-calculate raw material needs, offset inventory, lead times
│   ├── bottleneck.py                # Flag WCs > 85% (warning) / 100% (critical), rank by impact
│   └── agents/
│       ├── capacity_agent.py        # Claude tool_use agent: capacity forecasting
│       └── sourcing_agent.py        # Claude tool_use agent: sourcing recommendations
├── app.py                           # TO BUILD — Streamlit UI or CLI entry point
└── tests/
    └── test_capacity_engine.py      # TO BUILD
```

---

## Technical Approach

### 1. Capacity Calculation
- Load factory params and tooling data
- Compute available hours per work center per time period (week/month)
- Subtract scheduled maintenance windows
- Calculate required hours from sales pipeline × probability weight × cycle time

### 2. Scenario Simulation
- **Optimistic**: Use upper-bound probabilities, compressed cycle times
- **Base case**: Use stated probabilities, nominal cycle times
- **Pessimistic**: Use probabilities × 1.0, extended cycle times + unplanned downtime buffer
- Monte Carlo runs (N=1000+) to produce capacity utilization distributions

### 3. Bottleneck Detection
- Flag work centers where utilization > 85% (warning) or > 100% (critical)
- Rank bottlenecks by impact (lost capacity × unit margin proxy)
- Suggest rebalancing options (shift to alternative tools/factories)

### 4. Material Requirements Planning (MRP)
- Back-calculate raw material needs from capacity plan
- Apply inventory on-hand and in-transit offsets
- Generate sourcing recommendations with lead time windows

### 5. AI Orchestration Layer
- Claude API (claude-sonnet-4-6) with tool use
- Tools exposed to the agent: `get_capacity_forecast`, `run_scenario`, `get_sourcing_recommendations`, `get_bottlenecks`, `explain_constraint`
- Natural language interface for planners to query the model

---

## Key Domain Rules

- One tool can produce multiple component types (specified in material master)
- Cycle times vary by factory AND by tool (not just one or the other)
- Probability-weighted demand: `expected_units = project_units × probability`
- Maintenance windows are hard constraints — they cannot be overridden
- Lead time for raw materials must be respected in sourcing recommendations
- Capacity is measured in **H/PCS** (hours per piece) from Anaplan; realised production is **PCS/H**

---

## Development Priorities

1. Get the core capacity engine working with synthetic/provided data first
2. Wire up scenario simulation before the AI layer
3. Add the Claude agent layer last — it wraps the engine, not replaces it
4. Keep the UI simple: a Streamlit dashboard or CLI is sufficient for the demo

---

## Dependencies

The repo's `requirements.txt` is missing several packages needed for the agent and UI layers. Add them:

```
# Already in requirements.txt
pandas>=2.0
numpy>=1.24
openpyxl>=3.1
plotly>=5.18
matplotlib>=3.7
scikit-learn>=1.3
jupyter>=1.0
ipykernel>=6.25

# Add these
anthropic>=0.40.0    # Claude API + tool use
streamlit>=1.35      # UI dashboard
scipy>=1.12          # distributions for scenario simulation
python-dotenv>=1.0   # ANTHROPIC_API_KEY from .env
```

---

## Environment Variables

```
ANTHROPIC_API_KEY=...
```

---

## Demo Script (Success Criteria)

1. Load sales pipeline with mixed probability projects (from `1_1`/`1_2`/`1_3`)
2. Show baseline capacity forecast across 2–3 plants
3. Run "pessimistic" scenario → highlight bottleneck at a specific work center
4. Ask the AI agent: *"What materials do I need to source in the next 6 weeks?"*
5. Agent responds with prioritized sourcing list with quantities and timing
6. Show downtime impact: inject a maintenance window → capacity drops, agent re-routes

---

## One-Day Hackathon Strategy

### Core Positioning: Probabilistic Capacity Twin

> We transform uncertain sales opportunities into operationally feasible production and sourcing decisions before the demand becomes a problem.

The case owner cares about **attitude and approach** over perfect code, and specifically wants to see familiarity with Claude API agents, tool use, and orchestration. The winning move is a thin but complete vertical slice where a Claude agent orchestrates real tools to answer a planner's question — not just a dashboard, not just a forecast.

---

### What to Build (Realistic 1-Day Scope)

**Layer 1 — Data foundation (2h)**
- Load the 13 Excel sheets into pandas DataFrames (use `starter_notebook.ipynb` as the starting point)
- Handle data quality: `Missing CT`/`Missing WC`/`Missing tool` placeholders, `#N/A` WC codes, blank connectors (`_`)
- Compute effective capacity per work center per month from `2_5` shift levels and `2_4` calendar
- Compute probability-weighted demand from `1_1`/`1_2` pipeline × `1_3` probabilities × `2_6` cycle times
- Files: `src/data_loader.py` + `src/capacity_engine.py`

**Layer 2 — Scenario engine (2h)**
- Three fixed scenarios: pessimistic / base / optimistic (adjust probabilities + add downtime buffer)
- Flag bottlenecks where utilization > 85% (warning) / 100% (critical)
- Back-calculate raw material needs from demand → BOM (`3_2`) → raw material quantities
- Offset against `3_1` on-hand + in-transit inventory; apply `2_3` lead times for order-by dates
- Files: `src/scenario_simulator.py` + `src/mrp.py`

**Layer 3 — Claude Agent (3h) — THE SHOWPIECE**
- Claude API with `tool_use` calling Python functions
- Tools exposed:
  - `get_capacity_forecast(factory, time_horizon)`
  - `run_scenario(scenario_type)`
  - `get_bottlenecks(threshold)`
  - `get_sourcing_recommendations(weeks_ahead)`
  - `explain_constraint(work_center_id)`
- Agent receives natural language questions, calls tools, synthesizes a coherent answer with reasoning
- This demonstrates orchestration and is the key differentiator

**Layer 4 — Streamlit UI (2h)**
- Sidebar: scenario selector + time horizon slider
- Main panel: factory heatmap (utilization %), bottleneck table, sourcing list
- Chat panel: type questions to the Claude agent, see tool calls + reasoning

---

### Work Split (3 people)

| Person | Task | Deliverable |
|--------|------|-------------|
| A | Data layer + capacity engine | All 13 sheets loaded, utilization calculated per WC |
| B | Scenario simulator + MRP | 3 scenarios, BOM-backed material requirements |
| C | Claude agent + Streamlit UI | The AI interface, the demo |

**Critical path note:** Person C should start the agent with **mocked tool responses** so the UI works while A and B finish the real engine — then swap in real data.

---

### Demo Script (5 Minutes, Every Minute Dense)

1. Show the sales pipeline — "here's what we know is coming, with uncertainty"
2. Run base scenario → show capacity heatmap across 2–3 plants
3. Switch to pessimistic → one work center turns red (bottleneck)
4. Type to the agent: *"What should I buy in the next 6 weeks?"* → watch it call `get_sourcing_recommendations` + `get_bottlenecks`, synthesize an answer
5. Inject a maintenance window → capacity drops, agent re-routes recommendation

---

### What to Skip (Don't Try in 1 Day)

- ML probability calibration — use the `1_3` probabilities as-is (10/25/50/75/90%)
- OR-Tools optimization — simple heuristics are enough
- Full Monte Carlo — three pre-defined scenarios is convincing enough
- All 15 plants — pick 2–3, show them cleanly; "framework extends to all 15" is the scalability story
- Complete product family coverage — pick plates + gaskets for 2 plants, show them cleanly

---

### Pitch Narrative

**Problem:** Planners see a sales pipeline but can't see what it does to their factories.

**Solution:** We propagate uncertain demand through real production constraints — maintenance, tool limits, cycle times — and let an AI agent translate that into sourcing and capacity actions.

**Outcome:** Decisions made weeks earlier, not after the shortage is already expensive.

---

### Judging Angle

| Criterion | How we hit it |
|---|---|
| Attitude / approach | Strategy + live agent reasoning shows deep understanding |
| AI tooling familiarity | Claude `tool_use` orchestration is exactly what was asked for |
| Business value | Agent output IS the sourcing decision, not just a chart |
| Feasibility | Tight vertical slice > broad broken system |
| Scalability story | "Demonstrated on 2 factories; framework extends to all of them" |
