# Planner Actions Report

Date: 2026-04-18

## Inputs

- `fact_integrated_risk_base` (Luigi Wave 3)
- `dim_action_policy` (Carolina Wave 3)
- `fact_capacity_bottleneck_summary` (Lara Wave 2)
- `fact_data_quality_flags` (Carolina Wave 3)
- `fact_scenario_resilience_impact` (Lara Wave 3)

## Output Summary

- total action rows: `224691`
- action type distribution: `{'hedge_inventory': 54506, 'upshift': 53451, 'buy_now': 53415, 'split_production': 48571, 'reschedule': 14096, 'wait': 652}`
- confidence distribution: `{'low': 178467, 'medium': 46224}`
- mean action_score by scenario: `{'all_in': 0.2644, 'expected_value': 0.1198, 'high_confidence': 0.2195, 'monte_carlo_light': 0.1496}`

## Top 20 Actions (by action_score)

```
scenario      action_type  action_score project_id plant         material_or_wc confidence                                                              reason
  all_in          upshift      0.563104  SF-100477  NW10       P01_NW10_PRESS_2     medium capacity_risk=1.00≥0.80; priority=0.93≥0.30 — shift lever available
  all_in split_production      0.563104  SF-100477  NW10       P01_NW10_PRESS_2     medium   capacity_risk=1.00≥0.70; priority=0.93≥0.40 — split across plants
  all_in          buy_now      0.563104  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium    sourcing_risk=1.00≥0.70; priority=0.93≥0.30; risk_base=0.81≥0.60
  all_in  hedge_inventory      0.563104  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium  sourcing_risk=1.00≥0.50; priority=0.93≥0.20 — buffer stock advised
  all_in  hedge_inventory      0.563100  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium  sourcing_risk=1.00≥0.50; priority=0.93≥0.20 — buffer stock advised
  all_in          upshift      0.563100  SF-100477  NW10       P01_NW10_PRESS_2     medium capacity_risk=1.00≥0.80; priority=0.93≥0.30 — shift lever available
  all_in          buy_now      0.563100  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium    sourcing_risk=1.00≥0.70; priority=0.93≥0.30; risk_base=0.81≥0.60
  all_in split_production      0.563100  SF-100477  NW10       P01_NW10_PRESS_2     medium   capacity_risk=1.00≥0.70; priority=0.93≥0.40 — split across plants
  all_in split_production      0.563098  SF-100477  NW10       P01_NW10_PRESS_2     medium   capacity_risk=1.00≥0.70; priority=0.93≥0.40 — split across plants
  all_in          buy_now      0.563098  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium    sourcing_risk=1.00≥0.70; priority=0.93≥0.30; risk_base=0.81≥0.60
  all_in  hedge_inventory      0.563098  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium  sourcing_risk=1.00≥0.50; priority=0.93≥0.20 — buffer stock advised
  all_in          upshift      0.563098  SF-100477  NW10       P01_NW10_PRESS_2     medium capacity_risk=1.00≥0.80; priority=0.93≥0.30 — shift lever available
  all_in          upshift      0.563094  SF-100477  NW10       P01_NW10_PRESS_2     medium capacity_risk=1.00≥0.80; priority=0.93≥0.30 — shift lever available
  all_in          buy_now      0.563094  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium    sourcing_risk=1.00≥0.70; priority=0.93≥0.30; risk_base=0.81≥0.60
  all_in split_production      0.563094  SF-100477  NW10       P01_NW10_PRESS_2     medium   capacity_risk=1.00≥0.70; priority=0.93≥0.40 — split across plants
  all_in  hedge_inventory      0.563094  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium  sourcing_risk=1.00≥0.50; priority=0.93≥0.20 — buffer stock advised
  all_in  hedge_inventory      0.563087  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium  sourcing_risk=1.00≥0.50; priority=0.93≥0.20 — buffer stock advised
  all_in split_production      0.563087  SF-100477  NW10       P01_NW10_PRESS_2     medium   capacity_risk=1.00≥0.70; priority=0.93≥0.40 — split across plants
  all_in          buy_now      0.563087  SF-100477  NW10 ALL_MATERIALS_AT_PLANT     medium    sourcing_risk=1.00≥0.70; priority=0.93≥0.30; risk_base=0.81≥0.60
  all_in          upshift      0.563087  SF-100477  NW10       P01_NW10_PRESS_2     medium capacity_risk=1.00≥0.80; priority=0.93≥0.30 — shift lever available
```

## Action Logic

- buy_now: sourcing_risk ≥ 0.70 AND priority ≥ 0.30 AND risk_base ≥ 0.60
- wait: risk_base < 0.30 AND priority < 0.40
- reroute: logistics_risk ≥ 0.50 AND priority ≥ 0.40
- upshift: capacity_risk ≥ 0.80 AND priority ≥ 0.30
- expedite_shipping: logistics_risk ≥ 0.60 AND priority ≥ 0.50
- reschedule: capacity_risk ≥ 0.60 AND priority < 0.50
- escalate: action_score_base ≥ 0.80 AND top_driver ∈ {capacity_risk, sourcing_risk} AND priority ≥ 0.70
- hedge_inventory: sourcing_risk ≥ 0.50 AND priority ≥ 0.20
- split_production: capacity_risk ≥ 0.70 AND priority ≥ 0.40

## Quality Penalty Application

- weaken flags → action_score reduced by penalty × 0.20
- block flags → confidence forced to low
- flag_only → shown with warning, score unaffected
- disruption_risk from Wave 3 adds up to 10% boost to action_score

## Validation

- every action row carries explanation_trace with full driver breakdown
- recommended_target_plant set only for reroute and split_production
- top 20 actions readable by product owners (see table above)
- no black-box logic — all triggers are explicit boolean thresholds
