# Disruption Engine Report

Date: 2026-04-18

## Inputs

- `fact_integrated_risk_base` (Luigi Wave 3 output)
- `dim_disruption_scenario_synth` (Wave 3 Lara synthetic catalog)

## Disruption Catalog

- disruption families: `8`
- total scenarios: `8`

| scenario_name | family | affected_plants | cap_mult | lt_mult | rel_pen |
|---|---|---|---|---|---|
| war_disruption__eastern_europe | war_disruption | NW03,NW10 | 0.5 | 2.5 | 0.6 |
| lane_blockage__suez | lane_blockage | NW05,NW15 | 1.0 | 1.8 | 0.4 |
| border_delay__us_tariff | border_delay | NW01,NW06,NW07 | 1.0 | 1.5 | 0.2 |
| plant_outage__nw05_fire | plant_outage | NW05 | 0.0 | 1.0 | 0.8 |
| labor_shortage__eu_assembly | labor_shortage | NW01,NW02,NW03 | 0.65 | 1.3 | 0.1 |
| energy_shock__eu_west | energy_shock | NW02,NW08,NW09 | 0.8 | 1.2 | 0.15 |
| fuel_price_spike__global | fuel_price_spike | ALL | 1.0 | 1.1 | 0.05 |
| maintenance_overrun__nw02 | maintenance_overrun | NW02 | 0.75 | 1.0 | 0.05 |

## Resilience Impact

- impact rows: `114548`
- affected plants: `['NW01', 'NW02', 'NW03', 'NW04', 'NW05', 'NW06', 'NW07', 'NW08', 'NW09', 'NW10', 'NW11', 'NW12', 'NW13', 'NW14', 'NW15']`
- mitigation candidate distribution: `{'no_action_needed': 68424, 'reroute': 42204, 'reschedule': 3920}`

## Average Disruption Risk by Scenario

```
{'border_delay__us_tariff': 0.0017, 'energy_shock__eu_west': 0.0078, 'fuel_price_spike__global': 0.0033, 'labor_shortage__eu_assembly': 0.003, 'lane_blockage__suez': 0.0233, 'maintenance_overrun__nw02': 0.0025, 'plant_outage__nw05_fire': 0.0694, 'war_disruption__eastern_europe': 0.0514}
```

## Validation

- all disruption multipliers are explicit and documented
- before/after deltas are computed per (scenario × plant × week × disruption)
- mitigation candidates assigned by dominant delta dimension
- no hidden logic — every output row carries an explanation_note
- all disruption rows are synthetic — labeled with generation_version

## Synthetic Dependency Warning

All disruption parameters (multipliers, affected plants, reliability penalties) are
synthetic expert estimates. Replace with real incident data before using for
operational planning decisions.
