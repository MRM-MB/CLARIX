# Assumptions

Use this file to register every modeling, data, scenario, or synthetic-data assumption introduced during implementation.

Format:

`ASSUMPTION_ID | description | rationale | impact | synthetic=true/false`

## Current Assumptions

`A001 | The existing backend in clarix/ is the correct base to evolve rather than replace | It already contains canonical loaders and deterministic planning logic | High | synthetic=false`

`A002 | The workbook sheet 2_4 Model Calendar should become the source for month-to-week allocation | The current engine evenly spreads monthly demand, while the workbook already includes a calendar asset | High | synthetic=false`

`A003 | Initial logistics and disruption layers will require synthetic enrichment because no lane master exists in the repo-backed data | The repo includes master data, BOM, inventory, and capacity, but not shipping-lane datasets | High | synthetic=true`

`A004 | Legacy Streamlit surfaces remain valid demo consumers during migration | Existing pages and charts already demonstrate capacity and sourcing outcomes | Medium | synthetic=false`

`A005 | Urgency score in Wave 1 is anchored to 2026-04-18 and bucketed by days to requested delivery date | The dataset snapshot is around April 2026 and no explicit urgency field exists in the source workbook | High | synthetic=false`

`A006 | Revenue tier and customer segment are mapped to deterministic business-priority score components via fixed lookup tables | Wave 1 requires interpretable normalized scoring before richer business-policy inputs exist | High | synthetic=false`

`A007 | Wave 2 stores the weekly bucket key as YYYY-Www in the single required week column | The prompt requires a week column but also requires uniqueness across a multi-year horizon without a separate year key | High | synthetic=false`

`A008 | Monte Carlo Light in Wave 2 uses a fixed seed of 42 and 200 Bernoulli trials at the monthly row level before weekly allocation | The prompt requires seeded stochastic logic and the legacy engine already uses a light Monte Carlo pattern | High | synthetic=false`

`A009 | Wave 3 uses fact_scenario_logistics_weekly as the base project-grain table because it is the only available input already keyed by scenario, project_id, plant, and week | Capacity and sourcing inputs are plant-week aggregates and cannot define project grain on their own | High | synthetic=false`

`A010 | Wave 3 falls back from monte_carlo_light to expected_value for capacity risk because fact_scenario_capacity_weekly does not include Monte Carlo rows | The prompt requires a deterministic base risk engine now, without waiting for final disruption-adjusted outputs | High | synthetic=false`

`A011 | Wave 3 interprets sourcing coverage_days_or_weeks as a conservative time-cover metric normalized over a 14-day threshold for lead-time risk | The available sourcing fact does not carry a cleaner lead-time-risk field, but the prompt requires a base lead-time component now | Medium | synthetic=false`

`A012 | Wave 4 aggregates multiple disruption branches affecting the same scenario x project x plant x week by summing their incremental deltas and clipping the final disruption-adjusted scores to 1.0 | fact_scenario_resilience_impact is branch-level while fact_integrated_risk must stay at planner grain; additive capped deltas preserve visibility without introducing hidden branch selection logic | High | synthetic=false`

`A013 | Wave 4 collapses sourcing-row and bottleneck-row QA flags to project grain using max penalty per inherited scope before merging onto scenario x project x plant x week rows | those QA flags are generated below project grain and summing every component or work-center issue would distort the final planner score by row multiplicity rather than severity | High | synthetic=false`

`A014 | Wave 5 defines the active MVP region scope as denmark_demo = {NW08,NW09,NW10} with a global reference scope kept inactive | the prompt requires a single-region demo filter but the repo has no authoritative plant-to-country master, so the scope is an explicit business configuration rather than a geography dimension | High | synthetic=false`

`A015 | Wave 5 quarter-state and decision-history logic use the expected_value scenario as the canonical business continuity baseline | Wave 5 outputs do not include a scenario column, and expected_value is the least speculative scenario for quarter-over-quarter business tracking | High | synthetic=false`

`A016 | Wave 5 infers previous_action_type per project-quarter by combining the prior-quarter dominant top_driver with the project-plant action catalog from fact_planner_actions | fact_planner_actions does not carry week or quarter keys, so a documented adapter is required to keep decision history traceable without fabricating planner-run timestamps | High | synthetic=false`

`A017 | Wave 5 marks action_outcome_status as pending_outcome_synth whenever a prior-quarter decision exists because no realized execution outcomes are available in the repo-backed data | the prompt explicitly forbids inventing realized outcomes, but Q1 to Q2 continuity still needs a labeled placeholder state | High | synthetic=true`

`A018 | Wave 5 counts high-confidence projects where probability_score >= 0.70 and strategic projects where revenue_tier is Strategic or strategic_segment_score >= 0.80 | the required quarter business snapshot needs deterministic project counts and these fields already exist in the priority dimension | Medium | synthetic=false`

`A019 | Wave 6 derives project-quarter learning on the expected_value scenario only and treats quarter-level risk repetition as a top-driver persistence signal | expected_value is already the Wave 5 business continuity baseline and top-driver persistence is the most explainable repeat-risk indicator available from fact_integrated_risk | High | synthetic=false`

`A020 | Wave 6 keeps carry_over_probability_adjustment as a standalone signal equal to the deterministic confidence-adjustment signal and never mutates the base probability stored in dim_project_priority | the prompt explicitly requires probability to remain separate from business-priority adjustments | High | synthetic=false`

`A021 | Wave 6 unresolved_action_penalty is triggered by Wave 5 pending_outcome_synth carry-over rows because no realized execution outcomes exist in repo-backed data | this preserves quarter roll-forward friction without fabricating actual planner outcomes | High | synthetic=true`

`A022 | Wave 7 derives scope-aware business risk rows by joining fact_integrated_risk to fact_quarter_learning_signals on project_id + quarter_id, allowing the same weekly risk row to exist in multiple business scopes | scope membership is defined in the quarter-learning layer, not in fact_integrated_risk v1, so scope-aware duplication is required to preserve explicit business filters | High | synthetic=false`

`A023 | Wave 7 maps delivery caution from fact_delivery_risk_rollforward by project_id + carry_forward_quarter_id regardless of the source scope_id because Wave 6 Carolina uses mvp_3plant while Luigi business scopes use denmark_demo/global_reference | this is an explicit adapter across scope systems and is documented in the v2 report instead of hidden behind a fake scope reconciliation | High | synthetic=false`

`A024 | Wave 7 maps maintenance_risk_score from Wave 6 Lara by taking the maximum pct_capacity_lost_to_maintenance per plant across maintenance scenarios and broadcasting it to business-scope rows at that plant | maintenance assets are plant/work-center based and use maintenance scenarios rather than demand scenarios, so a plant-level conservative adapter is the most transparent way to expose maintenance risk in integrated risk v2 | High | synthetic=false`

## Template For New Entries

`A### | description | rationale | impact | synthetic=true/false`
