"""Synthetic logistics reference dimensions aligned to project contracts."""

from __future__ import annotations

import numpy as np
import pandas as pd


GENERATION_VERSION = "wave1_seeded_v1"
DEFAULT_SEED = 42

_PLANT_COUNTRY_MAP = {
    "NW01": "US",
    "NW02": "DE",
    "NW03": "PL",
    "NW04": "IN",
    "NW05": "CN",
    "NW06": "US2",
    "NW07": "US3",
    "NW08": "ES",
    "NW09": "CH",
    "NW10": "LV",
    "NW11": "IL",
    "NW12": "BR",
    "NW13": "CL",
    "NW14": "AU",
    "NW15": "VN",
}


def build_dim_country_cost_index_synth(seed: int = DEFAULT_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    country_codes = list(_PLANT_COUNTRY_MAP.values())
    return pd.DataFrame(
        {
            "country_code": country_codes,
            "labor_cost_index_synth": rng.uniform(0.3, 1.5, len(country_codes)).round(4),
            "energy_cost_index_synth": rng.uniform(0.4, 1.3, len(country_codes)).round(4),
            "generation_logic": "seeded_uniform_country_indices",
            "generation_version": GENERATION_VERSION,
            "random_seed": seed,
        }
    )


def build_dim_shipping_lane_synth(seed: int = DEFAULT_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    country_codes = list(_PLANT_COUNTRY_MAP.values())
    rows = []
    for origin in country_codes:
        for destination in country_codes:
            same_country = origin == destination
            transit_days = int(rng.integers(1, 4) if same_country else rng.integers(4, 31))
            cost_index = float(rng.uniform(0.8, 2.5))
            reliability = float(rng.uniform(0.6, 0.99))
            rows.append(
                {
                    "lane_id": f"{origin}__{destination}",
                    "origin_country": origin,
                    "destination_country": destination,
                    "transit_days_synth": transit_days,
                    "lane_cost_index_synth": round(cost_index, 4),
                    "lane_reliability_synth": round(reliability, 4),
                    "generation_logic": "seeded_country_pair_matrix",
                    "generation_version": GENERATION_VERSION,
                    "random_seed": seed,
                }
            )
    return pd.DataFrame(rows)


def build_dim_service_level_policy_synth(seed: int = DEFAULT_SEED) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "revenue_tier": "Small",
                "urgency_band": "standard",
                "target_service_level_synth": 0.90,
                "expedite_days_threshold_synth": 14,
                "generation_logic": "deterministic_revenue_tier_policy",
                "generation_version": GENERATION_VERSION,
                "random_seed": seed,
            },
            {
                "revenue_tier": "Medium",
                "urgency_band": "priority",
                "target_service_level_synth": 0.94,
                "expedite_days_threshold_synth": 7,
                "generation_logic": "deterministic_revenue_tier_policy",
                "generation_version": GENERATION_VERSION,
                "random_seed": seed,
            },
            {
                "revenue_tier": "Large",
                "urgency_band": "priority",
                "target_service_level_synth": 0.97,
                "expedite_days_threshold_synth": 3,
                "generation_logic": "deterministic_revenue_tier_policy",
                "generation_version": GENERATION_VERSION,
                "random_seed": seed,
            },
            {
                "revenue_tier": "Strategic",
                "urgency_band": "critical",
                "target_service_level_synth": 0.995,
                "expedite_days_threshold_synth": 0,
                "generation_logic": "deterministic_revenue_tier_policy",
                "generation_version": GENERATION_VERSION,
                "random_seed": seed,
            },
        ]
    )
