# Wave 6 Carolina Report — Delivery Commitment & Service Memory

## Inputs Used

| File | Source | Rows (approx) |
|------|--------|---------------|
| `project/data/processed/fact_scoped_logistics_weekly.csv` | Wave 5 Carolina (scoped filter) | ~variable |
| `project/data/processed/fact_material_decision_history.csv` | Wave 5 Carolina (decision history) | ~variable |
| `project/data/processed/fact_logistics_quarterly_snapshot.csv` | Wave 5 Carolina (quarterly snapshot) | ~variable |
| `processed/dim_service_level_policy_synth.csv` | Wave 1 Carolina (synthetic) | 4 |

## fact_delivery_commitment_weekly

- **Grain:** scope_id × scenario × project_id × plant × week
- **Output:** `project/data/processed/fact_delivery_commitment_weekly.csv`
- **requested_delivery_date:** week_date + 28 days (SYNTHETIC ASSUMPTION — 4-week forward delivery window; no real customer commit dates available)
- **production_time_proxy_days:** 14 days (SYNTHETIC CONSTANT — no SAP production lead-time data in scope)
- **total_commitment_time_days:** transit_time_days + production_time_proxy_days
- **revenue_tier derivation:** logistics_risk_score < 0.2 → Small, 0.2–0.4 → Medium, 0.4–0.6 → Large, >= 0.6 → Strategic
- **service_violation_risk:** lateness_exposure / days_until_deadline, clipped [0, 1]
  - lateness_exposure = max(0, total_commitment_time_days − days_until_deadline)
  - days_until_deadline = 28 days (fixed, because requested_delivery_date = week_date + 28)
- **on_time_feasible_flag:** total_commitment_time_days <= (days_until_deadline + max_allowed_late_days from service policy)
- **expedite_option_flag:** expedite_allowed_flag from service policy joined on revenue_tier
- **synthetic_delivery_assumption = True** on all rows (both assumptions labeled per governance)

## fact_quarter_service_memory

- **Grain:** scope_id × quarter_id × project_id (expected_value scenario only)
- **Output:** `project/data/processed/fact_quarter_service_memory.csv`
- **Scenario filter:** expected_value only — deterministic base for carry-over analysis
- **prior_on_time_feasible_flag:** True if mean(on_time_feasible_flag) >= 0.5 across the quarter's weeks
- **prior_expedite_flag:** True if mean(expedite_option_flag) >= 0.3 (expedite needed often)
- **prior_service_violation_risk:** mean(service_violation_risk) from delivery_commitment for the same grain
- **carry_over_service_caution_flag triggers:**
  - prior_on_time_feasible_flag = False (majority of weeks infeasible), OR
  - prior_service_violation_risk > 0.4
- **explanation_note logic:**
  - carry_over AND violation > 0.4: "High service violation risk in {Q} — apply caution buffer in next quarter"
  - carry_over AND not on_time: "Majority of weeks infeasible in {Q} — consider rerouting or upshift"
  - otherwise: "Service levels met in {Q} — maintain current approach"

## fact_delivery_risk_rollforward

- **Grain:** scope_id × source_quarter_id × project_id
- **Output:** `project/data/processed/fact_delivery_risk_rollforward.csv`
- **Source:** Q1 service memory rows forward-projected to Q2 planning caution
- **carry_forward_quarter_id:** same year, Q2 (e.g., "2026-Q1" → "2026-Q2")
- **recommended_caution_level:** high / medium / low
  - high: carry_over=True AND prior_service_violation_risk > 0.6
  - medium: carry_over=True AND prior_service_violation_risk > 0.3
  - low: carry_over=False
- **caution_explanation:**
  - high: "Q1 had critical service failures — add 2-week buffer to Q2 lead times"
  - medium: "Q1 had moderate risk — add 1-week buffer and monitor expedite options"
  - low: "Q1 was clean — proceed with standard Q2 planning"
- **Logistics snapshot join:** Q2 avg_transit_time_days joined as an informational signal (does not change caution level calculation)

## Synthetic Dependency Visibility

| Field | Synthetic? | Label mechanism |
|-------|-----------|-----------------|
| requested_delivery_date | YES — week + 28 days | `synthetic_delivery_assumption=True` column |
| production_time_proxy_days | YES — constant 14 | `synthetic_delivery_assumption=True` column; hardcoded with comment |
| logistics dimensions (transit, cost, risk) | YES — inherited from Wave 2 | `synthetic_dependency_flag=True` (passthrough) |
| service_violation_risk | DERIVED from synthetic inputs | labeled via synthetic_delivery_assumption |
| recommended_caution_level | DERIVED from service memory | downstream of synthetic chain |

All three output tables carry explicit synthetic labeling fields. No silent synthetic drops.

## Blockers for Wave 7

None. All 3 outputs are stable and ready for downstream consumption:

- `fact_delivery_commitment_weekly` — weekly commit feasibility per project × plant
- `fact_quarter_service_memory` — quarterly service caution signals per project
- `fact_delivery_risk_rollforward` — Q1→Q2 caution level recommendations

## Test Coverage

31 tests pass (unit + integration):
- `week_to_date` and `week_to_quarter` mapping correctness
- All required columns present on each output table
- `service_violation_risk` in [0, 1]
- `total_commitment_time_days > 0` for all rows
- Uniqueness on all natural keys
- `carry_over_service_caution_flag` is boolean
- `explanation_note` never null
- `recommended_caution_level` only contains: high, medium, low
- `carry_forward_quarter_id` always ends in Q2
- Integration tests against real processed CSVs (skipped if files missing)
