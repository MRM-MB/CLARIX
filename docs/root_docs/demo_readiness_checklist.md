# Demo Readiness Checklist

## Pre-demo checks
- [ ] `streamlit run app.py` launches without errors
- [ ] All 8 pages render (Executive overview, Capacity planner, Bottlenecks, Sourcing & MRP, What-if planner, Ask Clarix, Logistics & Disruptions, Actions)
- [ ] project/data/processed/ contains: fact_integrated_risk_base.csv, fact_scenario_sourcing_weekly.csv, fact_scenario_logistics_weekly.csv, fact_capacity_bottleneck_summary.csv, dim_action_policy.csv, fact_data_quality_flags.csv
- [ ] Scenario selector changes update all pages correctly
- [ ] Actions page loads planner actions without error
- [ ] "Why this recommendation?" panel shows explanation for any selected project

## Data checks
- [ ] fact_integrated_risk_base.csv: >50k rows, all 4 scenarios present
- [ ] fact_scenario_sourcing_weekly.csv: >50k rows, shortage_flag column present
- [ ] fact_scenario_logistics_weekly.csv: >50k rows, synthetic_dependency_flag=True
- [ ] dim_action_policy.csv: exactly 9 rows, policy_version=v1

## Synthetic data warnings visible
- [ ] Logistics page shows synthetic data banner
- [ ] Actions page shows penalty context

## Fallback messages
- [ ] Missing pipeline files show st.warning (not crash)
- [ ] Empty dataframes show "No data available" (not blank screen)
