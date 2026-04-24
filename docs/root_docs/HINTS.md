# Hints & questions worth asking

This file is a grab-bag — starting points, subtle things to watch out for in the dataset, and the *kinds* of questions that typically surface when someone actually builds this. We're not telling you *how* to solve the case; we're flagging where the interesting decisions live so you can make them deliberately.

## Starting-point suggestions (from the case brief)

1. **Map the data flow logically**: *Sales Pipeline (Probability) → Product Requirements → Raw Material Needs & Tooling → Factory Capacity & Uptime.*
2. **Consider how probability weighting impacts expected capacity.** How should the supply chain prepare for a massive project that only has a 50% chance of closing? Reserve full capacity? Weighted demand? Scenario split?
3. **Look into ML applications for predictive maintenance and probability forecasting** — but remember only a snapshot of data is available, so training anything data-hungry will be limited. What can you do with rules + heuristics + simulation first?

## Things worth noticing in the data (authentic artifacts, not traps)

- Several rows in `1_1` / `1_2` have **placeholder strings** like `Missing CT`, `Missing WC`, `Missing tool`, `_`, or `Missing plant`. These are master-data gaps, not random noise. Decide how to handle them.
- Some rows in `2_6.Work center` hold **`#N/A`** values — master data pending update. `pandas.read_excel` reads these as `NaN` unless you pass `keep_default_na=False`.
- The same **material code can appear with different `Rev no` at different plants**. Treating these as interchangeable is wrong (wrong revision = product failure). How does your model handle this?
- Tools have **cycle times expressed per piece**. Whether they're minutes or seconds is worth double-checking against the `Total QTY` and typical values.
- Sheet `2_2` values are much smaller than you'd expect (typically 0.001–0.2) — they are disaggregated pieces per week per material, not hours.
- **One tool can serve multiple materials**, and **the same tool number can exist at multiple plants** — that's an opportunity for cross-factory substitution, not a data error.
- Not every pipeline project in `1_1` / `1_2` is present in `1_3 Export Project list`. That's authentic master-data latency.

## The kinds of questions the case owner's team actually had to answer

Consider these when deciding your own approach. You don't have to answer them the same way the real team did — coming up with a *different* answer with a clear rationale is perfectly valid.

- **What unit is `Cycle time` in sheet 1_1 / 1_2 and 2_6?** Convention in SAP routing is minutes per piece — does your analysis assume that?
- **How do pipeline projects interact with the approved business plan?** Do they *replace* the existing plan at a work center? *Add to* it? *Compete for* the same slots?
- **Weekly vs monthly reporting granularity.** The capacity sheet (`2_1`) is weekly. The pipeline demand (`1_1`/`1_2`) is monthly. The project delivery dates (`1_3`) are specific dates. Which one is your primary granularity, and how do you reconcile the rest?
- **Dual unit reporting.** Is your final output in hours or pieces? The Anaplan plan has both. Plant planners typically want both — the finance team just wants pieces.
- **Tool-level vs work-center-level.** A WC may have spare capacity overall while one specific tool is triple-booked. Does your analysis catch that?
- **Scenarios.** Three common framings: (a) fill capacity to the limit and flag the rest, (b) allocate only to available capacity and show overflow, (c) distribute demand evenly. Which do you implement, and why?
- **Rev no compatibility.** If pipeline project X needs material Y at Rev B and inventory has Rev A, is that a stop or a flag?
- **Tool maintenance threshold.** What triggers a maintenance event in your model? Accumulated volume? Calendar? Neither is spelled out in the data — design a rule.
- **Scrap factors.** Sheet `3_2` has both scrap-factor columns and effective-quantity columns. Which do you use for sourcing math?
- **Cross-factory reallocation.** Same tool number at another plant — does that mean the work *could* move? What else would need to be true?
- **Missing data.** Rows with `Missing CT`, `_` connectors, `#N/A` work centers. What's your policy — drop, impute, flag, or all three?

## Ask the case owner

Your team gets up to **3 clarification questions** during the hackathon. Use them for things you *cannot* infer from the data or the dictionary. For example:

- "What's your tool-maintenance threshold rule in real life?"
- "When a pipeline project lands, is its demand additive to the Anaplan plan, or does the plan already anticipate some of it?"
- "What's the cost of missing a sourcing deadline — is there a specific penalty we should optimize against?"

Don't waste them on things the data already tells you.

## A final word

The case owner has already built a solution on the real data. He deliberately did not share his approach here because the goal is for you to come up with something original. If your solution differs from his, that's a feature, not a bug — and if your solution is *better* than his, please explain exactly how and why at the final demo.
