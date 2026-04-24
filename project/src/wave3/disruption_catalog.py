"""
disruption_catalog.py
=====================
Wave 3 Lara: Builds dim_disruption_scenario_synth with 8 disruption families.

One concern: define and expose the disruption catalog as a DataFrame.
Inner function _build_catalog() is I/O-free and fully testable.
"""

from __future__ import annotations

import pandas as pd

GENERATION_VERSION = "wave3_disruption_v1"
CATALOG_SEED = 42

# Explicit disruption definitions — all multipliers are documented and explainable.
# Fields:
#   transit_multiplier:              how much longer transit takes
#   shipping_cost_multiplier:        how much more expensive shipping becomes
#   available_capacity_multiplier:   fraction of original capacity remaining (0=total outage)
#   lead_time_multiplier:            how much longer procurement lead times become
#   reliability_penalty:             points subtracted from route reliability (0–1)
_DISRUPTION_ROWS: list[dict] = [
    {
        "disruption_family": "war_disruption",
        "scenario_name": "war_disruption__eastern_europe",
        "affected_region_or_lane": "EU_EAST",
        "affected_plants": "NW03,NW10",
        "affected_materials": "ALL",
        "transit_multiplier": 3.0,
        "shipping_cost_multiplier": 4.5,
        "available_capacity_multiplier": 0.50,
        "lead_time_multiplier": 2.5,
        "reliability_penalty": 0.60,
        "synthetic_generation_rule": (
            "Eastern Europe war scenario: NW03 (PL) and NW10 (LV) at 50% capacity; "
            "transit 3x from route closures; shipping cost 4.5x; lead time 2.5x; "
            "reliability down 60pp. Multipliers expert-set."
        ),
    },
    {
        "disruption_family": "lane_blockage",
        "scenario_name": "lane_blockage__suez",
        "affected_region_or_lane": "LANE_APAC_EU",
        "affected_plants": "NW05,NW15",
        "affected_materials": "ALL",
        "transit_multiplier": 2.2,
        "shipping_cost_multiplier": 2.8,
        "available_capacity_multiplier": 1.0,
        "lead_time_multiplier": 1.8,
        "reliability_penalty": 0.40,
        "synthetic_generation_rule": (
            "Suez Canal blockage: APAC→EU lanes (NW05 CN, NW15 VN) rerouted via Cape; "
            "transit 2.2x; cost 2.8x; lead time 1.8x; reliability down 40pp. "
            "Plant capacity unaffected. Based on 2021 Ever Given incident."
        ),
    },
    {
        "disruption_family": "border_delay",
        "scenario_name": "border_delay__us_tariff",
        "affected_region_or_lane": "BORDER_US",
        "affected_plants": "NW01,NW06,NW07",
        "affected_materials": "ALL",
        "transit_multiplier": 1.4,
        "shipping_cost_multiplier": 1.6,
        "available_capacity_multiplier": 1.0,
        "lead_time_multiplier": 1.5,
        "reliability_penalty": 0.20,
        "synthetic_generation_rule": (
            "US tariff / customs border delay: NW01, NW06, NW07 (US plants) face inbound delays; "
            "transit 1.4x; cost 1.6x from tariff surcharge; lead time 1.5x; "
            "reliability down 20pp. Capacity unaffected — delay is logistics-side only."
        ),
    },
    {
        "disruption_family": "plant_outage",
        "scenario_name": "plant_outage__nw05_fire",
        "affected_region_or_lane": "PLANT_NW05",
        "affected_plants": "NW05",
        "affected_materials": "ALL",
        "transit_multiplier": 1.0,
        "shipping_cost_multiplier": 1.0,
        "available_capacity_multiplier": 0.0,
        "lead_time_multiplier": 1.0,
        "reliability_penalty": 0.80,
        "synthetic_generation_rule": (
            "NW05 (CN) plant complete outage: capacity_multiplier=0.0 (total shutdown); "
            "logistics and lead time unaffected at plant level — no output to ship. "
            "reliability_penalty=0.80 reflects complete unreliability."
        ),
    },
    {
        "disruption_family": "labor_shortage",
        "scenario_name": "labor_shortage__eu_assembly",
        "affected_region_or_lane": "EU_ASSEMBLY",
        "affected_plants": "NW01,NW02,NW03",
        "affected_materials": "ALL",
        "transit_multiplier": 1.0,
        "shipping_cost_multiplier": 1.0,
        "available_capacity_multiplier": 0.65,
        "lead_time_multiplier": 1.3,
        "reliability_penalty": 0.10,
        "synthetic_generation_rule": (
            "EU assembly labor shortage: NW01, NW02, NW03 at 65% capacity; "
            "lead time 1.3x from slower throughput; logistics unaffected. "
            "Multiplier 0.65 = 35% capacity reduction, moderate disruption tier."
        ),
    },
    {
        "disruption_family": "energy_shock",
        "scenario_name": "energy_shock__eu_west",
        "affected_region_or_lane": "EU_WEST",
        "affected_plants": "NW02,NW08,NW09",
        "affected_materials": "ALL",
        "transit_multiplier": 1.0,
        "shipping_cost_multiplier": 1.2,
        "available_capacity_multiplier": 0.80,
        "lead_time_multiplier": 1.2,
        "reliability_penalty": 0.15,
        "synthetic_generation_rule": (
            "Western Europe energy shock: NW02 (DE), NW08 (ES), NW09 (CH) at 80% capacity; "
            "shipping cost 1.2x from higher fuel; lead time 1.2x; reliability down 15pp. "
            "Based on 2022 EU gas crisis analogue."
        ),
    },
    {
        "disruption_family": "fuel_price_spike",
        "scenario_name": "fuel_price_spike__global",
        "affected_region_or_lane": "GLOBAL",
        "affected_plants": "ALL",
        "affected_materials": "ALL",
        "transit_multiplier": 1.0,
        "shipping_cost_multiplier": 1.8,
        "available_capacity_multiplier": 1.0,
        "lead_time_multiplier": 1.1,
        "reliability_penalty": 0.05,
        "synthetic_generation_rule": (
            "Global fuel price spike: all plants and lanes affected; "
            "shipping cost 1.8x; slight lead time increase 1.1x from carrier surcharges; "
            "capacity and reliability minimally affected. Logistics-dominant disruption."
        ),
    },
    {
        "disruption_family": "maintenance_overrun",
        "scenario_name": "maintenance_overrun__nw02",
        "affected_region_or_lane": "PLANT_NW02",
        "affected_plants": "NW02",
        "affected_materials": "ALL",
        "transit_multiplier": 1.0,
        "shipping_cost_multiplier": 1.0,
        "available_capacity_multiplier": 0.75,
        "lead_time_multiplier": 1.0,
        "reliability_penalty": 0.05,
        "synthetic_generation_rule": (
            "NW02 (DE) planned maintenance overrun: 25% capacity reduction for affected weeks; "
            "logistics and sourcing unaffected; reliability slightly down. "
            "Multiplier 0.75 = 4-week maintenance window extending by 2 weeks."
        ),
    },
]

_COLUMN_ORDER = [
    "disruption_family",
    "scenario_name",
    "affected_region_or_lane",
    "affected_plants",
    "affected_materials",
    "transit_multiplier",
    "shipping_cost_multiplier",
    "available_capacity_multiplier",
    "lead_time_multiplier",
    "reliability_penalty",
    "synthetic_generation_rule",
    "generation_version",
    "random_seed",
]

DISRUPTION_FAMILIES = [r["disruption_family"] for r in _DISRUPTION_ROWS]


def _build_catalog() -> pd.DataFrame:
    """Build dim_disruption_scenario_synth. No I/O — pure transformation."""
    rows = []
    for r in _DISRUPTION_ROWS:
        row = dict(r)
        row["generation_version"] = GENERATION_VERSION
        row["random_seed"] = CATALOG_SEED
        rows.append(row)
    return pd.DataFrame(rows)[_COLUMN_ORDER]


def build_dim_disruption_scenario_synth() -> pd.DataFrame:
    """Public entry point: returns the full disruption catalog DataFrame."""
    return _build_catalog()
