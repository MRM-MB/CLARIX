# Wave 3 Carolina Report — Action Policy & QA Guardrails

## Inputs Used

| Input | Location | Notes |
|---|---|---|
| fact_scenario_sourcing_weekly.csv | project/data/processed/ | Wave 2 sourcing output |
| fact_scenario_logistics_weekly.csv | project/data/processed/ | Wave 2 logistics output |
| fact_capacity_bottleneck_summary.csv | project/data/processed/ | Wave 2 bottleneck output |
| fact_integrated_risk_base.csv | project/data/processed/ | Wave 3 Luigi integrated risk |
| dim_service_level_policy_synth.csv | processed/ | Wave 1 synthetic service level |

## dim_action_policy

9 action families defined. Policy version: v1.

| action_type | trigger_condition | min_priority | min_risk | effect |
|---|---|---|---|---|
| buy_now | sourcing_risk_score >= 0.7 AND shortage_flag AND lead_time allows | 0.3 | 0.6 | reduce_shortage |
| wait | risk_score_base < 0.3 AND priority_score < 0.4 | 0.0 | 0.0 | hedge_uncertainty |
| reroute | logistics_risk_score >= 0.5 AND alt plant available with capacity | 0.4 | 0.4 | reduce_delay |
| upshift | capacity_risk_score >= 0.8 AND upshift limit available | 0.3 | 0.5 | reduce_overload |
| expedite_shipping | logistics_risk_score >= 0.6 AND expedite_allowed_flag | 0.5 | 0.5 | reduce_delay |
| reschedule | capacity_risk_score >= 0.6 AND priority_score < 0.5 | 0.0 | 0.4 | reduce_overload |
| escalate | action_score_base >= 0.8 AND top_driver in [capacity_risk, sourcing_risk] | 0.7 | 0.7 | escalate_decision |
| hedge_inventory | sourcing_risk_score >= 0.5 AND coverage_days_or_weeks < 14 | 0.2 | 0.3 | hedge_uncertainty |
| split_production | capacity_risk_score >= 0.7 AND alt plant available | 0.4 | 0.6 | reduce_overload |

## fact_data_quality_flags

Produced 162,336 flag rows across all Wave 2 outputs.

| Issue Type | Count | Severity | Penalty | Handling |
|---|---|---|---|---|
| synthetic_logistics_dependency | 57,792 | warning | 0.10 | flag_only |
| placeholder_quality_zero | 57,792 | info | 0.05 | flag_only |
| missing_inventory_coverage | 45,009 | critical | 0.40 | weaken |
| on_time_infeasible | 1,416 | critical | 0.30 | weaken |
| capacity_bottleneck_critical | 327 | critical | 0.35 | weaken |

## Penalty Impact on Recommendations

- Penalties accumulate additively per (scenario, project, plant, week)
- Wave 4 should sum penalty_score per entity_key group and subtract from action_score_base
- Maximum effective penalty per row: 1.0 (clamp after sum)
- QUALITY_PENALTY_PLACEHOLDER rows indicate the integrated risk base has not yet applied real quality penalties

## Blocking Conditions

- recommended_handling = "block": do not surface recommendation to planner
- recommended_handling = "weaken": reduce action_score_base by penalty_score
- recommended_handling = "flag_only": show recommendation with warning label

## Blockers for Wave 4

- Wave 4 can now join dim_action_policy on top_driver + risk thresholds to select applicable actions
- fact_data_quality_flags provides the penalty_score to degrade action_score_base
- No blockers identified
