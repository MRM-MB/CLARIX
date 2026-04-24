# Wave 1 — Lara Report: Operational Spine & Capacity Foundation

Generated: 2026-04-18

## Summary

Wave 1 delivers the four schema-stable outputs required by downstream Wave 2 agents:

| Output | Source | Module | Status |
|---|---|---|---|
| `bridge_material_tool_wc` | 2_6 Tool_material nr master | `wave1/operational_mapping.py` | Done |
| `fact_wc_capacity_weekly` | 2_1 Work Center Capacity Weekly | `wave1/capacity_baseline.py` | Done |
| `bridge_month_week_calendar` | 2_4 Model Calendar | `wave1/calendar_bridge.py` | Done |
| `dim_wc_scenario_limits` | 2_5 WC Schedule_limits | `wave1/scenario_limits.py` | Done |

All 22 unit tests pass. Integration tests require the real Excel file.

---

## Legacy Module Reuse Decisions

| Legacy component | Decision | Notes |
|---|---|---|
| `clarix.data_loader.load_canonical()` | **KEEP** | Primary intake layer; wrapped via `legacy_adapters/legacy_loader.py` |
| `CanonicalData` | **ADAPT** | Used as base; `fact_wc_capacity_weekly` and `bridge_material_tool_wc` fields extended |
| `clarix.data_loader._build_wc_capacity()` | **KEEP (adapted)** | Source for `fact_wc_capacity_weekly`; column renames + derived columns added |
| `clarix.data_loader._build_tool_master()` | **ADAPT** | Does not capture `Rev no` — 2_6 re-read directly in `operational_mapping.py` |
| `clarix.data_loader._build_wc_limits()` | **ADAPT** | Collapses 5 shift levels; `scenario_limits.py` re-reads 2_5 to preserve all levels |
| `clarix.engine.build_demand_by_wc_week()` | **ADAPT (Wave 2)** | Even-spread week allocation; replace with `bridge_month_week_calendar` in Wave 2 |
| `clarix.engine.build_utilization()` | **KEEP (Wave 2)** | Will consume `bridge_month_week_calendar` for weighted allocation |
| `clarix.engine.detect_bottlenecks()` | **KEEP (Wave 2)** | Unchanged; downstream consumer |
| `clarix.charts` | **KEEP** | No changes required |
| `notebooks/starter_notebook.ipynb` | **DEPRECATE** | Replaced by structured modules |

---

## New Modules Created

| Module | Purpose |
|---|---|
| `project/src/legacy_adapters/legacy_loader.py` | Thin adapter over `clarix.data_loader`; isolates legacy imports |
| `project/src/wave1/operational_mapping.py` | Builds enriched `bridge_material_tool_wc` with Rev no + reason codes |
| `project/src/wave1/capacity_baseline.py` | Builds `fact_wc_capacity_weekly` with derived remaining/missing columns |
| `project/src/wave1/calendar_bridge.py` | Builds `bridge_month_week_calendar` from 2_4; falls back to pandas date arithmetic |
| `project/src/wave1/scenario_limits.py` | Builds `dim_wc_scenario_limits` preserving all 5 shift-level variants from 2_5 |
| `project/src/wave1/runner.py` | Orchestrates all 4 outputs, validates, and saves parquet to `project/data/wave1/` |
| `project/tests/test_wave1_lara.py` | 22 unit tests + 5 integration tests (marked `@pytest.mark.integration`) |

---

## Validation Status

### Unit tests (22/22 pass — no Excel required)
- `fact_wc_capacity_weekly`: unique by `(plant, work_center, week)` ✓
- `bridge_month_week_calendar`: `allocation_weight` sums to 1.0 per `(plant, year, month)` ✓
- `bridge_material_tool_wc`: reason codes assigned for all mapping failures ✓
- `dim_wc_scenario_limits`: all 5 shift-level scenario names mapped correctly ✓

### Integration tests (require `hackathon_dataset.xlsx`)
Run with: `pytest project/tests/test_wave1_lara.py -m integration`

Validates:
- `bridge_material_tool_wc` > 1,000 rows
- `fact_wc_capacity_weekly` unique by `(plant, work_center, week)`
- Calendar bridge weights sum correctly
- Scenario limits have 5 levels per WC
- Revision mismatches surfaced explicitly

---

## Mapping Gaps (expected from real data)

From `backend_audit.md` and data dictionary:
- `#N/A` values in `2_6.Work center` → flagged as `MISSING_WORK_CENTER`
- `"Missing CT"` sentinel in cycle time → flagged as `MISSING_CYCLE_TIME`
- Same material with multiple `Rev no` at same plant → counted in `materials_with_revision_mismatch`
- All gaps appear in `reason_code` column; none silently dropped

---

## Calendar Bridge Notes

The `2_4 Model Calendar` sheet is transposed (rows = attributes, columns = days). The parser:
1. Tries to parse the real sheet for per-plant working-day-weighted allocation
2. Falls back to pandas date arithmetic if sheet schema is unreadable

**Fallback bridge** (`bridge_version = "pandas_calendar_fallback_v1"`):
- `allocation_weight` = calendar days in (week ∩ month) / calendar days in month
- `working_day_weight` = same as `allocation_weight` (no plant-specific working day data)
- Plant column = `"ALL"` (plant-agnostic)

**Real bridge** (`bridge_version = "2_4_working_day_weighted_v1"`):
- Per-plant `working_day_weight` derived from `Working Days NW01..NW15` rows
- `allocation_weight` still calendar-day based

Wave 2 consumer (`build_demand_by_wc_week()`) should join on `(year, month, week)` and optionally `plant` when the real bridge is available.

---

## Blockers for Wave 2

| Blocker | Severity | Notes |
|---|---|---|
| `build_demand_by_wc_week()` uses even-spread allocation | Medium | Replace with `bridge_month_week_calendar` in Wave 2; bridge contract is ready |
| `dim_wc_scenario_limits.weekly_time_variant` may be null if 2_5 column name varies | Low | Fallback to `available_hours_variant` is in place |
| Calendar bridge plant coverage depends on 2_4 column naming | Low | Fallback ensures weights are always valid |
| Logistics/disruption layer entirely absent | High | Wave 2/3 scope; synthetic dims required per `synthetic_data_policy.md` |

---

## How to Run

```bash
# Build all Wave 1 outputs (saves parquet to project/data/wave1/)
python3 -m project.src.wave1.runner

# With custom paths
python3 -m project.src.wave1.runner --xlsx data/hackathon_dataset.xlsx --out project/data/wave1/ --csv

# Unit tests only (no Excel required)
pytest project/tests/test_wave1_lara.py -m "not integration" -v

# Integration tests (requires Excel)
pytest project/tests/test_wave1_lara.py -m integration -v
```
