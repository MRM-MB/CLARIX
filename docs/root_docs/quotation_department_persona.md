# Persona: Quotation Department Lead

## Document purpose
This persona is designed to help adapt the app, workflow, dashboard, and decision logic to the needs of the quotation department. It drives the hackathon demo narrative and all UI framing decisions.

---

## 1. Persona summary

**Name:** Marta Jensen
**Role:** Quotation Department Lead / Commercial Feasibility Manager
**Department:** Quotation / Pre-Sales / Commercial Operations
**Region scope:** One region at a time, typically Denmark or another selected operational scope
**Reports to:** Head of Sales Operations or Business Unit Director
**Works closely with:** Sales, Production Planning, Sourcing/Procurement, Finance, Factory Managers

### One-line profile
Marta decides which customer opportunities are worth quoting and later worth accepting — by balancing expected revenue, expected margin, delivery feasibility, capacity constraints, sourcing risk, and strategic importance.

### The sentence that defines her problem
> "Marta gets 40 quote requests a week. She approves them on gut feel and a spreadsheet."

### Core mission
Approve the right opportunities quickly, reject the wrong ones early, and never say yes to an order that will later become a delivery failure or a capacity crisis.

---

## 2. Why this persona is the right primary user

The product starts from an uncertain sales pipeline, qualifies opportunities by business priority, translates them into manufacturable demand, and ends with ranked planner actions with confidence scores and reasoning traces. That is exactly the chain of reasoning Marta needs before committing to a customer opportunity — not as an add-on, but as the native use case the architecture was built for.

---

## 3. Main responsibilities

### A. Pre-quote economic evaluation
Before approving quote effort, Marta estimates whether the opportunity is commercially attractive:
- material cost proxy
- production cost proxy
- labor and energy cost proxy
- shipping and logistics cost
- expected margin
- expedite premium if delivery becomes critical
- risk-adjusted profitability

### B. Opportunity screening
She decides which requests deserve serious effort and which should be rejected, postponed, or escalated. Typical questions:
- Is this order profitable enough?
- Can we produce it on time?
- Will it damage service level for better opportunities?
- Is the customer strategic enough to justify lower margin?
- Should we reroute production to a different plant?

### C. Commercial acceptance support
She does not only ask whether an order is technically possible. She asks whether it is worth accepting under current operational conditions.

### D. Portfolio optimization
She is not evaluating orders one by one. She is managing a portfolio of 40+ opportunities under finite capacity and finite sourcing flexibility — every decision she makes affects the others.

---

## 4. What success looks like

Marta is successful when she can:
- approve the right opportunities quickly — with confidence, not gut feel
- reject low-quality or low-margin opportunities before wasting commercial effort
- protect margin without hurting strategic relationships
- avoid accepting orders that later create bottlenecks or delivery failures
- explain every acceptance or rejection in one sentence to sales and management

### Key success metrics
- expected gross margin per approved opportunity
- quote win quality, not just win volume
- on-time delivery confidence at time of acceptance
- number of accepted orders later escalated due to capacity or material issues
- reduced last-minute expediting and firefighting

---

## 5. Main decisions

| Decision | Question she asks |
|----------|------------------|
| Quote or do not quote | Does this request deserve effort? |
| Accept, reject, or escalate | Should we take this order under current conditions? |
| Which plant | Where is the right balance of cost, capacity, and delivery reliability? |
| Standard or exception path | Expedite, reroute, split, or escalate? |
| Margin vs strategic concession | Is lower margin justified by this customer's strategic value? |
| Quarter carry-over | If Q1 showed this plant is fragile, should Q2 decisions be more conservative? |

---

## 6. Information she needs — in order

### 1. Is the opportunity attractive?
- project probability, expected quantity, expected revenue, revenue tier
- requested delivery date, priority score

### 2. Can we produce it?
- plant, work center, tool, cycle time
- effective capacity after maintenance and downtime (not just nominal)
- overload / bottleneck risk

### 3. Can we source the materials?
- BOM-driven component requirements, stock, ATP, in-transit inventory
- order-by date, shortage risk, long lead-time exposure

### 4. Can we deliver on time at acceptable cost?
- production time proxy + transit time
- shipping cost, landed-cost proxy
- expedite option flag, on-time feasible flag, disruption sensitivity

### 5. What is the best commercial action?
- accept / reject / escalate recommendation
- recommended plant
- confidence score
- reason in one sentence
- expected effect of the decision

---

## 7. What she cares about most

1. **Expected profitability** — margin after realistic cost and delivery constraints
2. **On-time delivery confidence** — not just "technically possible"
3. **Capacity realism** — effective capacity, not Anaplan nominal
4. **Material availability** — order-by dates, not just shortage flags
5. **Commercial priority** — strategic customers can justify lower margin, but never invisible operational risk
6. **Explainability** — every recommendation defensible to sales and management
7. **Quarter-over-quarter learning** — Q1 failures should be visible before Q2 decisions

---

## 8. Pain points

Marta gets frustrated when:
- sales pushes for approval without clear margin visibility
- capacity looks available on paper but not in reality
- a quote is approved and later becomes impossible due to material shortage
- shipping and transit cost is ignored until too late
- maintenance and downtime are treated as afterthoughts
- decisions are made on isolated spreadsheets instead of a connected workflow
- she cannot compare opportunities against each other under the same finite-capacity reality
- Q2 decisions ignore what went wrong in Q1

---

## 9. Behavioral profile

**Decision style:** Analytical but pragmatic. Skeptical of black-box recommendations. Wants transparent trade-offs. Comfortable with scenarios, not just single-point forecasts.

**Communication style:** Concise and business-oriented. Wants a clear recommendation plus rationale. Prefers ranked choices over raw data dumps. Expects red/yellow/green risk signals.

**Risk appetite:** Moderate by default. Lower tolerance for low-margin orders. Higher willingness to accept risk for strategic customers — but only when the expected upside is visible and the downside is quantified.

**Trust requirements:** She trusts the system when data provenance is visible, synthetic data is labeled, calculations are traceable, and recommendations include explanation traces. She will not defend a decision she cannot explain.

---

## 10. Core workflow

| Step | What Marta does | What Clarix provides |
|------|----------------|---------------------|
| 1. Intake | Review 40+ incoming opportunities | Ranked priority list — best opportunities first |
| 2. Economic screening | Estimate margin attractiveness | Expected revenue, cost proxy, margin signal |
| 3. Capacity feasibility | Check production constraints | Effective capacity vs load, bottleneck cards |
| 4. Material feasibility | Check sourcing risk | Shortage table, order-by dates |
| 5. Logistics feasibility | Check delivery confidence | On-time flag, transit cost, expedite options |
| 6. Portfolio trade-off | Compare against other active opportunities | Scenario comparison, risk-adjusted ranking |
| 7. Decision | Accept / reject / escalate / reroute | Ranked planner actions with confidence + reason |
| 8. Quarter learning | Apply Q1 lessons to Q2 | Carry-over risk cards, learning signal panel |

---

## 11. Example quotes

- *"Do not show me just revenue. Show me expected margin after realistic cost and delivery constraints."*
- *"A strategic customer can justify lower margin, but not an invisible operational disaster."*
- *"I need to know whether this order is worth accepting, not just whether it is technically possible."*
- *"If the model recommends rejecting an order, I need the reason in one sentence."*
- *"If Q1 already showed this plant is fragile, I want that memory visible before we repeat the mistake in Q2."*

---

## 12. Final design principle

Design the app so that Marta can answer one question without clicking through five screens:

> **"Given expected value, expected cost, expected risk, and delivery feasibility — should we quote and accept this order?"**

The reasoning must be visible. The confidence must be explicit. The recommendation must be defensible.
