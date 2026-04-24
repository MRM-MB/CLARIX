# Demo Readiness Checklist v2

**Wave 7 · Clarix · Danfoss Climate Solutions Hackathon**  
Date: 2026-04-18

---

## Pre-demo setup

- [ ] `streamlit run app.py` starts without errors
- [ ] All 5 Wave 7 pages render without broken screens (Scope & Region, Quarter History, Capacity & Maintenance, Sourcing & Delivery, Final Actions)
- [ ] `ANTHROPIC_API_KEY` set in environment (for Ask Clarix page)
- [ ] Browser window at 1920×1080 or wider, sidebar expanded

---

## Data availability

| File | Required | Status |
|------|----------|--------|
| `dim_region_scope.csv` | Scope & Region page | ✅ |
| `fact_pipeline_quarterly.csv` | Scope & Region, Quarter History | ✅ |
| `fact_effective_capacity_weekly_v2.csv` | Capacity & Maintenance | ✅ |
| `fact_maintenance_impact_summary.csv` | Capacity & Maintenance | ✅ |
| `fact_delivery_commitment_weekly.csv` | Sourcing & Delivery | ✅ |
| `fact_delivery_risk_rollforward.csv` | Sourcing & Delivery | ✅ |
| `fact_quarter_service_memory.csv` | Quarter History, Final Actions | ✅ |
| `fact_quarter_rollforward_inputs.csv` | Quarter History | ✅ |
| `fact_quarter_learning_signals.csv` | Quarter History | ✅ |
| `fact_planner_actions.csv` | Final Actions | ✅ |

---

## Page validation

### Scope & Region
- [ ] Region selector shows at least one region (default: first active)
- [ ] KPI row populates: projects, plants, materials, expected value
- [ ] Quarter-by-quarter bar chart renders
- [ ] Project breakdown table shows ≥1 row

### Quarter History
- [ ] Quarter selector populated from fact_quarter_service_memory
- [ ] Service memory table renders for selected quarter
- [ ] "What changed?" roll-forward panel shows adjustments
- [ ] Learning signals table shows repeated flag counts
- [ ] Delivery caution rollforward section renders

### Capacity & Maintenance
- [ ] Maintenance scenario selector populates from fact_effective_capacity_weekly_v2
- [ ] Switching scenario updates KPIs and heatmap
- [ ] Heatmap renders (top 25 WCs × weeks, colored by overload %)
- [ ] Scenario comparison bar chart renders
- [ ] Maintenance impact summary table renders

### Sourcing & Delivery
- [ ] KPIs reflect selected sidebar scenario
- [ ] Delivery feasibility scatter plot renders (on-time % vs service risk)
- [ ] Caution rollforward bar chart renders
- [ ] High/medium/low caution expanders show per-project explanations

### Final Actions
- [ ] Actions table shows `caution_level` column enriched from rollforward
- [ ] Action type distribution chart renders
- [ ] "Why this recommendation?" dropdown populated
- [ ] Selecting a project shows: action, reason, expected effect, quarter context
- [ ] Service memory history expander works for projects with history

---

## Workflow coherence checks

- [ ] Quarter switch (Q1 → Q2) updates service memory AND rollforward tables coherently
- [ ] Maintenance scenario switch updates capacity heatmap AND impact summary
- [ ] Scenario sidebar (expected_value / pessimistic / optimistic) updates delivery commitment KPIs
- [ ] Selecting a high-caution project in Final Actions shows non-empty caution context

---

## Real vs synthetic labeling

- [ ] Scope & Region: pills show REAL DATA for region_scope and pipeline_quarterly
- [ ] Capacity & Maintenance: pills correctly label maintenance policy as SYNTHETIC
- [ ] Sourcing & Delivery: pills label requested_delivery_date and production_time_proxy as SYNTHETIC
- [ ] Final Actions: pills label planner_actions and service_memory as REAL DATA
- [ ] No silent synthetic drops anywhere in the demo path

---

## Demo path timing

| Step | Target time | Page |
|------|-------------|------|
| Open app, navigate to Scope & Region | 0:00 – 0:35 | Scope & Region |
| Quarter History walkthrough | 0:35 – 1:10 | Quarter History |
| Capacity baseline → switch to unexpected_breakdown | 1:10 – 1:50 | Capacity & Maintenance |
| Sourcing & delivery + caution rollforward | 1:50 – 2:25 | Sourcing & Delivery |
| Final actions + why this recommendation? | 2:25 – 3:00 | Final Actions |

- [ ] Full demo path completes in under 3 minutes

---

## Known limitations (label in demo, don't hide)

- `requested_delivery_date` = week + 28d (synthetic — no real customer commit dates in scope)
- `production_time_proxy_days` = 14d constant (synthetic — no SAP production lead-time data)
- Maintenance policies are synthetic (seeded, deterministic, labeled with synthetic_flag=True)
- Scope is limited to 3 plants (NW01, NW02, NW05) — framework extends to all 15
- Planner actions v2 uses `fact_planner_actions.csv` (Wave 5 output) — not yet regenerated with Wave 6 inputs
