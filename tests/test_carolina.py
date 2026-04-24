"""
tests/test_carolina.py — pytest suite for Carolina Wave 1 modules.

Run with:
    pytest tests/test_carolina.py -v
"""

import os
import sys

import pandas as pd
import pytest

# Ensure src is on the path when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.carolina.synthetic_logistics import (
    create_country_cost_index,
    create_service_level_policy,
    create_shipping_lanes,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hackathon_dataset.xlsx")
_DATA_AVAILABLE = os.path.exists(DATA_PATH)


def _load_bom():
    from src.carolina.bom_loader import load_bom
    return load_bom(DATA_PATH)


def _load_inventory():
    from src.carolina.inventory_loader import load_inventory
    return load_inventory(DATA_PATH)


def _load_procurement():
    from src.carolina.procurement_loader import load_procurement
    return load_procurement(DATA_PATH)


# ---------------------------------------------------------------------------
# Synthetic table tests (no data file required)
# ---------------------------------------------------------------------------


class TestSyntheticTables:
    def test_country_cost_index_has_synthetic_rule_column(self):
        df = create_country_cost_index()
        assert "synthetic_generation_rule" in df.columns

    def test_country_cost_index_has_15_rows(self):
        df = create_country_cost_index()
        assert len(df) == 15

    def test_shipping_lanes_has_225_rows(self):
        df = create_shipping_lanes()
        assert len(df) == 225, f"Expected 225 rows (15x15), got {len(df)}"

    def test_shipping_lanes_has_synthetic_rule_column(self):
        df = create_shipping_lanes()
        assert "synthetic_generation_rule" in df.columns

    def test_service_level_policy_has_4_rows(self):
        df = create_service_level_policy()
        assert len(df) == 4, f"Expected 4 revenue tiers, got {len(df)}"

    def test_service_level_policy_has_synthetic_rule_column(self):
        df = create_service_level_policy()
        assert "synthetic_generation_rule" in df.columns

    def test_service_level_policy_revenue_tiers(self):
        df = create_service_level_policy()
        assert set(df["revenue_tier"]) == {"Small", "Medium", "Large", "Strategic"}

    def test_shipping_lanes_same_country_short_transit(self):
        df = create_shipping_lanes()
        same = df[df["origin_country"] == df["destination_country"]]
        assert (same["transit_time_days_synth"] <= 3).all()

    def test_expedited_cost_gte_base_cost(self):
        df = create_shipping_lanes()
        assert (df["expedited_shipping_cost_synth"] >= df["base_shipping_cost_synth"]).all()

    def test_reproducibility_seed(self):
        df1 = create_country_cost_index(seed=42)
        df2 = create_country_cost_index(seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_all_3_synthetic_tables_have_rule_column(self):
        for fn in [create_country_cost_index, create_shipping_lanes, create_service_level_policy]:
            df = fn()
            assert "synthetic_generation_rule" in df.columns, (
                f"{fn.__name__} missing synthetic_generation_rule"
            )


# ---------------------------------------------------------------------------
# Real data tests (skipped if data file not present)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _DATA_AVAILABLE, reason="hackathon_dataset.xlsx not available")
class TestBomLoader:
    def test_no_duplicate_plant_header_component(self):
        df = _load_bom()
        dupes = df.duplicated(subset=["plant", "header_material", "component_material"])
        assert not dupes.any(), f"Found {dupes.sum()} duplicate (plant, header_material, component_material) rows"

    def test_required_columns_present(self):
        df = _load_bom()
        required = {"plant", "header_material", "component_material", "effective_component_qty", "scrap_factor"}
        assert required.issubset(set(df.columns))

    def test_no_null_header_or_component(self):
        df = _load_bom()
        assert df["header_material"].notna().all()
        assert df["component_material"].notna().all()

    def test_plant_codes_are_short(self):
        df = _load_bom()
        # Extracted codes like NW01 are short, not the full compound string
        assert df["plant"].str.len().max() <= 10


@pytest.mark.skipif(not _DATA_AVAILABLE, reason="hackathon_dataset.xlsx not available")
class TestInventoryLoader:
    def test_unique_by_plant_material(self):
        df = _load_inventory()
        dupes = df.duplicated(subset=["plant", "material"])
        assert not dupes.any(), f"Found {dupes.sum()} duplicate (plant, material) rows"

    def test_required_columns_present(self):
        df = _load_inventory()
        required = {"plant", "material", "stock_qty", "atp_qty", "in_transit_qty", "safety_stock_qty", "inventory_snapshot_date"}
        assert required.issubset(set(df.columns))

    def test_numeric_qty_columns_no_nulls(self):
        df = _load_inventory()
        for col in ["stock_qty", "atp_qty", "in_transit_qty", "safety_stock_qty"]:
            assert df[col].notna().all(), f"{col} has nulls after fillna"


@pytest.mark.skipif(not _DATA_AVAILABLE, reason="hackathon_dataset.xlsx not available")
class TestProcurementLoader:
    def test_reason_code_column_exists(self):
        df = _load_procurement()
        assert "reason_code" in df.columns

    def test_reason_code_valid_values_only(self):
        df = _load_procurement()
        valid = {"OK", "MISSING_LEAD_TIME"}
        assert set(df["reason_code"]).issubset(valid), (
            f"Unexpected reason_code values: {set(df['reason_code']) - valid}"
        )

    def test_required_columns_present(self):
        df = _load_procurement()
        required = {"plant", "material", "procurement_type", "lead_time_days_or_weeks", "order_policy_note", "reason_code"}
        assert required.issubset(set(df.columns))

    def test_order_policy_note_valid_values(self):
        df = _load_procurement()
        valid = {"External procurement", "In-house production", "Mixed procurement", "Unknown"}
        assert set(df["order_policy_note"]).issubset(valid)
