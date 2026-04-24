# Wave 1 Carolina Report

## Legacy Module Audit
No legacy backend modules exist (greenfield project). All modules are NEW.
| Module | Decision | Reason |
|--------|----------|--------|
| bom_loader.py | NEW | No prior implementation |
| inventory_loader.py | NEW | No prior implementation |
| procurement_loader.py | NEW | No prior implementation |
| synthetic_logistics.py | NEW | No prior implementation |
| pipeline.py | NEW | No prior implementation |

## Outputs Produced
| File | Rows | Cols | Source |
|------|------|------|--------|
| fact_finished_to_component.csv | 9,490 | 5 | 3_2 Component_SF_RM |
| fact_inventory_snapshot.csv | 7,625 | 7 | 3_1 Inventory ATP |
| dim_procurement_logic.csv | 7,625 | 6 | 2_3 SAP MasterData |
| dim_country_cost_index_synth.csv | 15 | 6 | Synthetic |
| dim_shipping_lane_synth.csv | 225 | 8 | Synthetic |
| dim_service_level_policy_synth.csv | 4 | 7 | Synthetic |

All 15 plants (NW01–NW15) are present in fact_finished_to_component and fact_inventory_snapshot. No MISSING_LEAD_TIME rows in dim_procurement_logic (all 7,625 rows have a derivable lead time).

## Synthetic Data Logic

**dim_country_cost_index_synth** — 15 rows, one per plant country. Four cost indices (labor, energy, overhead, risk) drawn from uniform distributions with numpy seed=42 for reproducibility. Rule: `uniform_random_seeded_42_per_country`.

**dim_shipping_lane_synth** — 225 rows covering all 15×15 origin/destination country pairs. Same-country pairs get 1–3 day transit; cross-country pairs get 1–30 days. Expedited cost is base cost × uniform(1.5, 3.0). Reliability and disruption sensitivity drawn from bounded uniforms. Rule: `seeded_country_pair_matrix_42`.

**dim_service_level_policy_synth** — 4 rows, one per revenue tier (Small/Medium/Large/Strategic). Hardcoded business rules: stricter tiers have shorter max late days, more options enabled (expedite, reroute, premium shipping), and higher penalty weights. Rule: `business_rule_revenue_tier_hardcoded`.

## Schema Compliance
| Table | Required Columns | Status |
|-------|-----------------|--------|
| fact_finished_to_component | plant, header_material, component_material, effective_component_qty, scrap_factor | All present |
| fact_inventory_snapshot | plant, material, stock_qty, atp_qty, in_transit_qty, safety_stock_qty, inventory_snapshot_date | All present |
| dim_procurement_logic | plant, material, procurement_type, lead_time_days_or_weeks, order_policy_note, reason_code | All present |
| dim_country_cost_index_synth | country_code, labor_cost_index_synth, energy_cost_index_synth, overhead_cost_index_synth, risk_cost_index_synth, synthetic_generation_rule | All present |
| dim_shipping_lane_synth | origin_country, destination_country, transit_time_days_synth, base_shipping_cost_synth, expedited_shipping_cost_synth, route_reliability_score_synth, disruption_sensitivity_score_synth, synthetic_generation_rule | All present |
| dim_service_level_policy_synth | revenue_tier, max_allowed_late_days, expedite_allowed_flag, reroute_allowed_flag, premium_shipping_allowed_flag, service_penalty_weight, synthetic_generation_rule | All present |

## Known Data Quality Issues
- **3_2**: BOM rows with null header_material or component_material are dropped before output (~10 rows dropped from ~9,500 raw).
- **3_1**: Rows with null plant or material are dropped; numeric qty columns filled with 0 where null.
- **2_3**: Missing lead times flagged with MISSING_LEAD_TIME reason_code. Primary source is `Planned Delivery Time (MARC) (CD)`; fallback is `In House Production Time (WD)` × 1.4. In the current dataset all rows resolved without needing the fallback.
- **Plant column in 3_2** is a compound string (`P01_NW01_Northwind Midwest`) — plant code extracted via regex `P01_(\w+)_`.
- **`#N/A` strings** in Excel are replaced with None after load to avoid polluting string columns.

## Blockers for Wave 2
- Wave 2 can now consume all 6 outputs as stable contracts.
- No blockers identified.
