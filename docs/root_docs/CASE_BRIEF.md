# Case Brief — Predictive Manufacturing

**Optimizing Production Capacity & Supply Chain Sourcing**

## Problem statement

A global manufacturing network (5 factories, dozens of presses, hundreds of tools) faces a hard scheduling and sourcing problem. Sales sits on a pipeline of unapproved projects — each with a probability of closing, a monthly quantity profile, and a plant of record. Operations already runs an approved-business plan on top of finite press capacity. When a pipeline project lands, it needs to slot in on top of existing load using specific tools at specific work centers, and the raw materials (metal coils for plates, rubber compounds for gaskets) need to be on the dock when pressing starts.

The hard parts:

- **Cycle times vary by factory and tool** — the same plate material takes longer on a smaller press at one plant than on a larger press at another.
- **One tool can produce multiple material codes.** Mapping demand to tool-level capacity is not one-to-one.
- **Tools have mandatory maintenance** driven by accumulated pressed volume. A tool due for service cannot be scheduled against.
- **Raw materials have lead times** (SAP `Plan Delivery Time (MARC)`) measured in calendar days; ordering too late means the tool is idle.
- **Not every pipeline project will close.** The business runs multiple scenarios to understand exposure.

Today, this analysis is done by hand in Excel. The ask is to build a prototype that automates it.

## Desired outcomes

1. **Predictive Capacity Model.** A forecast of work-center load vs. capacity across factories for the next N months, highlighting where pipeline demand would exceed what the plant can deliver.
2. **Scenario Simulation.** The ability to run the same data through more than one assumption — for example, "what if 100% of pipeline closes?" vs. "what if only the high-probability projects close?" vs. "what if demand is evenly distributed across available capacity?"
3. **Smart Sourcing Forecast.** For each pipeline project, a ranked list of which raw materials need to be ordered, when to place the order to meet the demand date, and whether on-hand + in-transit inventory already covers it.
4. **Downtime Integration.** Scheduling logic that respects tool maintenance windows and the different shift patterns each factory runs.

## The data (all anonymized)

You get one Excel file — [data/hackathon_dataset.xlsx](data/hackathon_dataset.xlsx) — with 13 sheets. High level:

| Theme | Sheets |
|-------|--------|
| Sales pipeline (unapproved projects) | `1_1 Export Plates`, `1_2 Gaskets`, `1_3 Export Project list` |
| Capacity & planning | `2_1 Work Center Capacity Weekly`, `2_2 OPS plan per material `, `2_5 WC Schedule_limits` |
| Master data | `2_3 SAP MasterData`, `2_4 Model Calendar`, `2_6 Tool_material nr master` |
| Inventory & BOM | `3_1 Inventory ATP`, `3_2 Component_SF_RM` |
| Metadata / diagrams | `Flow`, `Savings per area`, `Sheet3` |

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for columns, units, and joins.

## Hints

> _Inspiration / Starting Point_ (from the case owner — do with these what you like)
>
> - Map the data flow logically: **Sales Pipeline (Probability) → Product Requirements → Raw Material Needs & Tooling → Factory Capacity & Uptime**.
> - Consider how probability weighting impacts expected capacity — how should the supply chain prepare for a massive project that only has a 50% chance of closing?
> - Look into machine learning applications for predictive maintenance and supply chain probability forecasting.

## Deliverables (what to show at the final presentation)

- A runnable prototype (notebook, CLI, web app — your choice) that ingests the Excel and produces the capacity and sourcing views.
- A 10-minute walkthrough of your approach, the assumptions you made, and the questions you'd ask Operations if you had more time.
- The code, readable enough for another team to extend.

## Contact

- **Case owner:** Daniel Parapunov — Case Owner / Project Lead
- **Email during the hackathon:** your hackathon coordinator will hand out the channel

Good luck. Build something you'd be proud to hand to an ops planner.
