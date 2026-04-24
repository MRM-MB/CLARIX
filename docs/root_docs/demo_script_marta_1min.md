# demo_script_marta_1min.md
## Clarix — 1-Minute Demo Script (Marta / Quotation Persona)

Date: 2026-04-18
Audience: Danfoss judges, case owner Daniel Parapunov
Target reaction: "This solves a real problem" + "Every quoting team could use this"

---

## Pre-Demo Setup (30 seconds before you speak)

```
1. Open http://localhost:8501
2. Navigate to: Executive Overview
3. Set scenario: base
4. Sidebar: click "▶ Start 3-Min Demo" to activate banners
5. Full-screen browser, sidebar expanded
```

The Executive Overview must be visible before you say the first word.

---

## The Script

### 0:00 — The hook (10 seconds)

**Say — before touching anything:**
> "Marta gets 40 quote requests a week. She approves them on gut feel and a spreadsheet. She has no way to know if an opportunity is actually manufacturable before she commits."

**Do:** Nothing. Let the sentence land.

---

### 0:10 — The overview (20 seconds)

**Point to the W7 intelligence row:**
> "This is what Clarix shows her instead."

**Point to the top-5 action cards:**
> "Every opportunity, ranked. Not by revenue — by whether it can actually be produced, sourced, and delivered on time. Each card has a recommended action and a confidence score."

**Point to the top-5 bottleneck cards:**
> "And the constraints driving those recommendations are right here — no digging required."

---

### 0:30 — The reasoning (20 seconds)

**Navigate to: Final Actions**

**Point to the top-3 action cards above the fold — do NOT click into the why-panel:**
> "For each opportunity: accept, expedite, reroute, or escalate — with the reason visible without opening anything."

**Point to the confidence scores:**
> "The confidence score tells Marta how much to trust the recommendation. The reason tells her how to defend it to sales."

**Point to the scenario selector in the sidebar — switch base → pessimistic:**
> "Switch to pessimistic — watch which orders flip from green to red. Those are the ones she should not approve today."

---

### 0:50 — The vision (10 seconds)

**Say — looking at the judges, not the screen:**
> "Every quoting team at Danfoss could make this decision in 30 seconds instead of 3 days."

**Pause one beat, then:**
> "That's Clarix."

---

## What NOT to do

- Do not open the why-panel by clicking a project — the reasoning is already visible on the cards
- Do not navigate to Scope & Region, Quarter History, or Sourcing & Delivery — they are not part of this story
- Do not explain the data model or the wave architecture
- Do not show more than 2 pages (Overview → Final Actions)

---

## Backup answer if asked "Is this real data?"

> "The pipeline, cycle times, BOM, and inventory are all from the real Danfoss hackathon dataset — 13 sheets, 15 plants. The shipping cost proxies are synthetic enrichments, clearly labelled. Everything else is real."

## Backup answer if asked "How does it scale?"

> "The demo shows 3 plants. The pipeline processes all 15 with no code changes. The quoting logic is data-driven — add a new region, it works."

## Backup answer if asked "What's the AI doing?"

> "The AI agent can answer natural language questions — 'what should I order this week', 'why is this plant overloaded'. But the ranked actions and confidence scores come from a deterministic engine, not a black box. Every number is traceable."

---

## Demo Checklist

- [ ] `streamlit run app.py` running at localhost:8501
- [ ] Wave 7 CSVs exist in `project/data/processed/`
- [ ] Executive Overview loads without error
- [ ] Final Actions top-3 cards visible above fold
- [ ] Scenario selector functional (base → pessimistic changes card colors)
- [ ] Demo mode activated (banner visible)
- [ ] Browser full-screen, sidebar expanded
- [ ] You have timed yourself — 60 seconds exactly
