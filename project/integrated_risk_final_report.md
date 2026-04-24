# Integrated Risk Final Report

Date: 2026-04-18

## Inputs

- `fact_integrated_risk_base`
- `fact_scenario_resilience_impact`
- `fact_data_quality_flags`

## Merge Logic

- disruption impacts are aggregated at `scenario x project_id x plant x week`, summed per row, and clipped to preserve bounded scores.
- the highest-impact disruption branch is retained only in explainability text so the final table stays planner-ready at the declared grain.
- exact QA flags (`risk_row`, `logistics_row`) are summed at row grain; multi-grain sourcing and bottleneck QA flags are collapsed with max-penalty adapters before joining to project rows.
- final `risk_score` and `action_score` follow the Wave 4 contract formulas exactly.

## Validation

- rows: `57792`
- duplicate grain rows: `0`
- bounded risk violations: `0`
- bounded action violations: `0`
- rows with disruption effect: `54924`
- rows with QA penalty: `54924`
- top drivers: `{'sourcing_risk': 38561, 'capacity_risk': 16123, 'logistics_risk': 2868, 'lead_time_risk': 240}`
- average risk by scenario: `{'all_in': 0.6891, 'expected_value': 0.6891, 'high_confidence': 0.6813, 'monte_carlo_light': 0.6727}`

## Top 20 Action Rows

scenario project_id plant     week  risk_score  action_score    top_driver
  all_in  SF-100477  NW10 2027-W09    0.811050      0.756135 capacity_risk
  all_in  SF-100477  NW10 2026-W34    0.811044      0.756129 capacity_risk
  all_in  SF-100477  NW10 2026-W49    0.811039      0.756125 capacity_risk
  all_in  SF-100477  NW10 2027-W03    0.811038      0.756124 capacity_risk
  all_in  SF-100477  NW10 2027-W05    0.811037      0.756123 capacity_risk
  all_in  SF-100477  NW10 2026-W35    0.811037      0.756123 capacity_risk
  all_in  SF-100477  NW10 2026-W29    0.811037      0.756123 capacity_risk
  all_in  SF-100477  NW10 2027-W06    0.811035      0.756121 capacity_risk
  all_in  SF-100477  NW10 2026-W38    0.811035      0.756121 capacity_risk
  all_in  SF-100477  NW10 2027-W07    0.811035      0.756121 capacity_risk
  all_in  SF-100477  NW10 2027-W01    0.811033      0.756119 sourcing_risk
  all_in  SF-100477  NW10 2027-W08    0.811032      0.756119 capacity_risk
  all_in  SF-100477  NW10 2026-W47    0.811031      0.756118 sourcing_risk
  all_in  SF-100477  NW10 2027-W04    0.811031      0.756117 sourcing_risk
  all_in  SF-100477  NW10 2026-W45    0.811030      0.756117 capacity_risk
  all_in  SF-100477  NW10 2026-W52    0.811030      0.756116 sourcing_risk
  all_in  SF-100477  NW10 2026-W30    0.811029      0.756116 capacity_risk
  all_in  SF-100477  NW10 2026-W50    0.811028      0.756115 sourcing_risk
  all_in  SF-100477  NW10 2026-W28    0.811028      0.756115 sourcing_risk
  all_in  SF-100477  NW10 2027-W10    0.811028      0.756115 sourcing_risk

## Notes

- `qa_guardrails_report.md` suggests subtracting penalties from `action_score_base`, but Wave 4 uses the canonical contract formula: QA enters through `data_quality_penalty` inside `risk_score`.
- all scores remain deterministic and bounded to `0..1`.
