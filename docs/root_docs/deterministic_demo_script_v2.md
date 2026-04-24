# Deterministic Demo Script v2
# Clarix — Wave 7 Demo Walkthrough

**Target duration:** under 3 minutes  
**Audience:** product owners / case judges  
**Message:** "We turn uncertain demand into operationally feasible production and sourcing decisions before the shortage is expensive."

---

## Minute 0:00 — Open app, navigate to Scope & Region

**Action:** Open `streamlit run app.py`. Click **Scope & Region** in the sidebar.

**Say:**
> "We're scoped to the MVP 3-plant region — NW01, NW02, NW05 — representing the Danfoss Nordics cluster.
> This is the single-region focus the product owners asked for: one region, fully modelled."

**Point to:**
- Region info card (scope_id, plants, scope rule)
- KPI row: projects, plants, materials, expected pipeline value
- Quarter-by-quarter expected qty bar chart

**Talking point:** The scope is explicit, auditable, and switchable via the sidebar — not hardcoded.

---

## Minute 0:35 — Quarter History / Learning

**Action:** Click **Quarter History** in the sidebar. Quarter selector shows Q1.

**Say:**
> "Q1 is the training quarter. Here we see which projects had service violations, and what the model learned."

**Point to:**
- Carry-over caution KPI: shows how many projects are flagged
- "What Changed from Last Quarter?" panel: probability/priority adjustments arriving at Q2
- Learning signals table: repeated_risk_flag, confidence_adjustment_signal

**Click expander "carry-over"** in Quarter selector to show all-quarter rollup.

**Talking point:** This is quarter-over-quarter learning — the system gets smarter with each cycle, not just each run.

---

## Minute 1:10 — Capacity with Maintenance

**Action:** Click **Capacity & Maintenance**. Maintenance scenario selector shows `baseline_maintenance`.

**Say:**
> "Here's our nominal effective capacity. Now watch what happens under unexpected breakdown."

**Action:** Switch maintenance scenario to `unexpected_breakdown`.

**Point to:**
- Capacity Lost to Maintenance KPI jumps
- Heatmap: red WC-week cells appear where they weren't before
- Scenario comparison bar chart: baseline vs overrun vs breakdown
- Maintenance impact summary table — highlight rows with `high` severity

**Talking point:** Maintenance is a hard constraint. We model it as four deterministic scenarios, not a magic slider.

---

## Minute 1:50 — Sourcing & Delivery

**Action:** Click **Sourcing & Delivery**. Scenario sidebar = `expected_value`.

**Say:**
> "Now the demand side. Given our scoped logistics, what's the delivery picture?"

**Point to:**
- On-Time Feasible % KPI
- Avg Service Violation Risk KPI
- Scatter plot: on-time % vs service risk per project (high-risk projects upper-left)

**Scroll to Caution Rollforward section.**

**Say:**
> "For projects that had issues in Q1, we carry the caution forward. High-caution projects get a 2-week buffer recommendation automatically."

**Expand the HIGH caution block** to show the individual caution_explanation strings.

---

## Minute 2:25 — Final Actions

**Action:** Click **Final Actions**.

**Say:**
> "All of this feeds into the planner actions table. Sorted by score, enriched with the quarter caution level."

**Point to:**
- Action Type Distribution chart
- Top-100 actions table — highlight `caution_level` column (H/M/L from rollforward)

**Select a high-caution project** from the "Why This Recommendation?" dropdown.

**Point to:**
- Recommended action + reason + expected effect
- Quarter caution context block: shows the caution explanation from service memory
- Action Score + Confidence metrics

**Say:**
> "Every recommendation is traceable to the data that drove it. No black box."

---

## Closing (30 sec)

> "In under 3 minutes we saw: a single-region scope, Q1 learning feeding Q2 planning, maintenance-aware effective capacity, delivery feasibility with carry-over caution, and prioritized planner actions with full explainability.
>
> The framework extends to all 15 plants and any planning horizon. Questions?"

---

## Fallback lines (if data looks thin)

- "The MVP scope is 3 plants — the same logic runs across all 15 with a config change."
- "Synthetic fields are labeled explicitly — you can see which numbers are real vs modelled."
- "The pipeline produces deterministic outputs — re-run gives the same result every time."
