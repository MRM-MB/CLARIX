# Wave 5 Luigi Report

Date: 2026-04-18

## Region-Scope Logic

- scopes are explicit business filters over plants and are reproducible from `scope_rule` plus `included_plants`.
- active scopes: `['denmark_demo']`

```text
        scope_id      region_name                                                            included_plants                      scope_rule  active_flag
global_reference Global Reference NW01,NW02,NW03,NW04,NW05,NW06,NW07,NW08,NW09,NW10,NW11,NW12,NW13,NW14,NW15             plant in ALL_PLANTS        False
    denmark_demo     Denmark Demo                                                             NW08,NW09,NW10 plant in ['NW08','NW09','NW10']         True
```

## Quarter Aggregation Logic

- `fact_pipeline_quarterly` aggregates `fact_pipeline_monthly` by `scope_id x quarter_id x project_id x plant x material`.
- quarter ids come from the monthly `period_date`, while decision continuity uses `clarix.engine.quarter_label()` over weekly risk rows.
- `fact_quarter_business_snapshot` rolls project-quarter demand into business KPIs and counts high-confidence / strategic projects with explicit deterministic rules.

```text
        scope_id quarter_id  total_projects  total_expected_value
    denmark_demo    2026-Q1              63          6.412713e+07
    denmark_demo    2026-Q2              63          6.412713e+07
    denmark_demo    2026-Q3              63          6.412713e+07
    denmark_demo    2026-Q4              63          6.412713e+07
    denmark_demo    2027-Q1              63          6.412713e+07
    denmark_demo    2027-Q2              63          6.412713e+07
    denmark_demo    2027-Q3              63          6.412713e+07
    denmark_demo    2027-Q4              63          6.412713e+07
    denmark_demo    2028-Q1              63          6.412713e+07
    denmark_demo    2028-Q2              63          6.412713e+07
    denmark_demo    2028-Q3              63          6.412713e+07
    denmark_demo    2028-Q4              63          6.412713e+07
global_reference    2026-Q1             288          3.312155e+08
global_reference    2026-Q2             288          3.312155e+08
global_reference    2026-Q3             288          3.312155e+08
global_reference    2026-Q4             288          3.312155e+08
global_reference    2027-Q1             288          3.312155e+08
global_reference    2027-Q2             288          3.312155e+08
global_reference    2027-Q3             288          3.312155e+08
global_reference    2027-Q4             288          3.312155e+08
global_reference    2028-Q1             288          3.312155e+08
global_reference    2028-Q2             288          3.312155e+08
global_reference    2028-Q3             288          3.312155e+08
global_reference    2028-Q4             288          3.312155e+08
```

## Decision-History Assumptions

- business continuity uses the `expected_value` scenario as the baseline quarter-state view.
- prior-quarter `top_driver` comes from the highest action-score risk row in the prior quarter.
- prior-quarter `previous_action_type` comes from the planner-action catalog for the same project and plant, constrained by the prior-quarter dominant driver when possible.
- carry-over rows materialized: `3861`

## Blockers For Wave 6

- `fact_planner_actions` has no week grain, so Wave 5 uses a documented adapter that selects prior-quarter actions from the expected-value action catalog plus prior-quarter top driver.
- realized outcomes are still unavailable; `action_outcome_status` remains explicitly labeled as pending synthetic history.
- Wave 6 should add persisted planner run ids or action timestamps so decision history no longer relies on quarter adapters.
