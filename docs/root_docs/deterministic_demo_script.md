# Deterministic Demo Script (5 minutes)

## Setup (before audience)
1. Run: `streamlit run app.py`
2. Verify all 8 pages load
3. Set scenario to: **expected_value** (sidebar)

## Minute 1 — Executive Overview
**Say:** "Here's the Northwind manufacturing network — 15 plants, ~720 pipeline projects, all with probability weights."
- Show KPI cards: total pipeline PCS, active projects, plants
- Point at the pipeline funnel chart
**Key message:** "Not all of this demand will land. We weight it by probability before loading capacity."

## Minute 2 — Capacity Planner → Bottlenecks
**Say:** "Let's see what happens when we route this demand through real press constraints."
- Switch to Capacity planner → pick plant NW01
- Show the utilization heatmap (red = overloaded work centers)
- Switch to Bottlenecks → highlight top bottleneck
**Key message:** "This is where Excel breaks down — we can see tool-level overloads weeks in advance."

## Minute 3 — Sourcing & MRP
**Say:** "Now let's ask: do we have the raw materials when we need them?"
- Switch to Sourcing & MRP
- Point at material shortage table — highlight shortage rows in red
- Show recommended order dates
**Key message:** "The system back-calculates when to place orders so material lands before the press starts."

## Minute 4 — Logistics & Disruptions
**Say:** "What about getting finished goods to customers on time?"
- Switch to Logistics & Disruptions
- Show % on-time feasible KPI
- Show disruption scenario comparison (switch to pessimistic / all_in to show risk increases)
**Key message:** "We model transit times and route reliability — and flag when expediting is the only option."

## Minute 5 — Actions
**Say:** "Finally — the AI synthesizes all of this into concrete planner recommendations."
- Switch to Actions page
- Sort by adjusted_action_score descending
- Click one high-score row → show "Why this recommendation?" panel
- Point at explainability_note and penalty breakdown
**Key message:** "This is a decision-support tool, not a black box. Every recommendation is traceable to data."

## Closing
"We demonstrated this on 2 plants live. The framework extends to all 15 — same pipeline, same logic, same explainability."
