"""
legacy_loader.py
================
Adapter wrapping clarix.data_loader into the new workflow architecture.

Decision: KEEP clarix.data_loader as the primary intake layer.
          Expose contract-shaped outputs here; callers never import clarix directly.

Field renames at the adapter boundary:
  pipeline: qty -> raw_qty  (contracts.md rule)
  dim_project: probability_pct/frac kept as-is (seed for dim_project_priority)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on path so clarix is importable regardless of cwd
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
from clarix.data_loader import load_canonical, CanonicalData  # noqa: E402

DEFAULT_XLSX = _REPO_ROOT / "data" / "hackathon_dataset.xlsx"


# ---------------------------------------------------------------------------
# Canonical loader (both naming conventions preserved for compatibility)
# ---------------------------------------------------------------------------

def get_canonical(xlsx_path: str | Path | None = None, *, use_cache: bool = True) -> CanonicalData:
    """Load CanonicalData via the legacy clarix loader (cached)."""
    path = str(xlsx_path or DEFAULT_XLSX)
    return load_canonical(path, use_cache=use_cache)


def load_legacy_canonical(
    xlsx_path: str | Path | None = None,
    *,
    use_cache: bool = True,
) -> CanonicalData:
    """Compatibility alias for get_canonical() — preserves upstream API."""
    return get_canonical(xlsx_path, use_cache=use_cache)


# ---------------------------------------------------------------------------
# Contract-shaped helpers
# ---------------------------------------------------------------------------

def get_pipeline_contract(data: CanonicalData) -> pd.DataFrame:
    """Return fact_pipeline_monthly with contract field renames applied."""
    df = data.fact_pipeline_monthly.copy()
    if "qty" in df.columns and "raw_qty" not in df.columns:
        df = df.rename(columns={"qty": "raw_qty"})
    return df


def read_raw_sheet(sheet_name: str, xlsx_path: str | Path | None = None, **kwargs) -> pd.DataFrame:
    """Read a raw workbook sheet without the canonical transform."""
    path = xlsx_path or DEFAULT_XLSX
    try:
        return pd.read_excel(path, sheet_name=sheet_name, **kwargs)
    except Exception as exc:
        import warnings
        warnings.warn(f"Could not read sheet '{sheet_name}': {exc}")
        return pd.DataFrame()
