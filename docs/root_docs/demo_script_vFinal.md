# demo_script_vFinal.md
## Clarix — 3-Minute Demo Script (Final)

Date: 2026-04-18  
Presenter: [Your name]  
Audience: Danfoss judges, case owner Daniel Parapunov

---

## Pre-Demo Setup (before presenting)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate Wave 6/7 processed outputs
python -m project.src.wave6.runner
python -m project.src.wave7.runner

# 3. Start the dashboard
streamlit run app.py

# 4. In the sidebar: click "▶  Start 3-Min Demo"
#    — story banners appear on each page
#    — default filters are already set correctly (base scenario, first region)
```

---

## The Story (pitch in one sentence)

> **We turn an uncertain sales pipeline into concrete sourcing and capacity actions — weeks before the problem becomes a crisis.**

---

## Step-by-Step Script

### Step 1 — Scope & Region (30 seconds)

**What to show:** The region info card, the demand distribution bar chart, and the data coverage panel.

**Say:**
> "Danfoss has 15 plants globally. For this MVP we deliberately focus on 3 — the highest revenue concentration in the region. This scope boundary is a demo constraint, not a product limitation. The framework extends to all 15 plants with no code changes."

**Point to:** Data coverage panel at the bottom — all 5 Wave 7 tables show AVAILABLE.

---

### Step 2 — Executive Overview (40 seconds)

**What to show:** The 4 classic KPIs, then the Wave 7 intelligence row, then the top-5 bottleneck and top-5 action cards.

**Say:**
> "This is the command centre. €[X]M of expected pipeline across [N] plants. Peak utilization is already at [X]% — some work centers are going critical. The Wave 7 intelligence layer has generated [N] planner actions, [N] of them high-confidence. These top-5 risks and top-5 actions are visible without opening a single other page."

**Point to:** The scenario summary table — show how switching to pessimistic increases high-risk rows.

---

### Step 3 — Quarter History (20 seconds)

**What to show:** The Q-over-Q delta metrics, then the carry-over project risk cards.

**Say:**
> "This is what makes the system smarter over time. The engine remembers last quarter — projects with repeated risks get a confidence penalty on their action scores. Planners are no longer surprised by the same bottleneck twice."

**Point to:** The "What this means" block at the bottom if needed.

---

### Step 4 — Capacity & Maintenance (30 seconds)

**What to show:** Select a plant in the "Nominal vs Effective" section. Show the two lines diverging during maintenance windows. Then show the bottleneck cards.

**Say:**
> "Nominal capacity is what Anaplan shows. Effective capacity is what the factory can actually do — after maintenance, OEE, and shift limits. This gap is the real constraint. These [N] work centers are flagged as critical bottlenecks, each with a suggested mitigation lever."

---

### Step 5 — Sourcing & Delivery (25 seconds)

**What to show:** The shortage table — scroll briefly. Then order-by recommendations.

**Say:**
> "For every shortage, the engine back-calculates from demand through the BOM to a specific material and gives you the last safe date to place a purchase order. This table goes directly to the procurement team. No manual analysis required."

**Point to:** Material criticality cards — "red means act today."

---

### Step 6 — Logistics & Disruptions (20 seconds)

**What to show:** Switch scenario from base to pessimistic. Show the disruption bar chart change. Point to route risk panel.

**Say:**
> "What if a key shipping lane is disrupted? The pessimistic scenario shows [X] more late route-weeks and [X]% higher logistics risk. [N] routes are expedite-eligible — that's your buffer. The landed cost proxy shows the financial tradeoff."

---

### Step 7 — Final Actions (25 seconds)

**What to show:** Top-3 action cards. Then select one project in the "Why this recommendation?" drilldown. Show the explanation trace.

**Say:**
> "This is the system's output: [N] ranked planner actions, each with a confidence score and a full reasoning chain. A planner can click any project, see exactly why the engine recommends 'expedite' or 'reroute', check the quarter context and service history, then sign off. The decision is explainable, auditable, and fast."

**Final line:**
> "Decisions made weeks earlier, not after the shortage is already expensive. That's Clarix."

---

## Backup Questions & Answers

| Question | Answer |
|----------|--------|
| "How does it handle real data?" | "The CSV outputs are generated from the real hackathon Excel dataset — 13 sheets, 15 plants, real cycle times and probabilities. All REAL DATA badges are exact." |
| "What's synthetic?" | "Shipping lanes, country cost indices, and disruption scenarios are synthetic enrichments. Everything clearly labelled with SYNTHETIC badges." |
| "Can it scale to all 15 plants?" | "Yes — the pipeline processes all plants. The demo scope is a filter, not a code constraint. Remove the scope filter and all plants are included." |
| "How do you know the actions are correct?" | "Each action traces to a risk_score_v2 composed of 6 dimensions. The explanation trace shows the top driver and why that specific action was selected. It's not a black box." |
| "What's the latency?" | "CSV generation takes ~60 seconds. Dashboard load is ~10 seconds (Excel parse, cached after). Per-page rendering is instant." |

---

## Demo Checklist (run before presenting)

- [ ] `streamlit run app.py` starts without error
- [ ] Wave 7 CSVs exist in `project/data/processed/`
- [ ] At least one region in `dim_region_scope.csv`
- [ ] Demo mode activated in sidebar (step banners visible)
- [ ] Base scenario selected
- [ ] Browser window is full-screen, sidebar expanded
- [ ] `ANTHROPIC_API_KEY` set (optional — planner mode works without it)
- [ ] Network tab shows no failed requests
