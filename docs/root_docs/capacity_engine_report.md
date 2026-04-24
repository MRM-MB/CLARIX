# Wave 2 — Lara: Capacity Engine Report

Generated: 2026-04-18

## Summary

Wave 2 delivers the capacity overlay and bottleneck engine on top of Wave 1's operational spine.

| Output | Module | Status |
|---|---|---|
| `fact_translated_project_demand_weekly` | `wave2/demand_translation.py` | Done |
| `fact_scenario_capacity_weekly` | `wave2/capacity_overlay.py` | Done |
| `fact_capacity_bottleneck_summary` | `wave2/bottleneck_engine.py` | Done |

All 20 unit tests pass. Integration tests require the real Excel file.

---

## Architecture (open-scaffold pattern)

Each module owns one concern and exposes a testable inner function (`_translate`, `_overlay`, `_summarise`) so tests run without I/O:

```
fact_pipeline_monthly  (Luigi Wave 1)
        │
        ▼
build_scenario_project_demand_seed()   ← 3 scenarios: all_in, expected_value, high_confidence
        │
        ├── × bridge_month_week_calendar  (Lara Wave 1 — working-day-weighted allocation)
        │         monthly qty → weekly qty (allocation_weight per plant/month/week)
        │
        ├── × bridge_material_tool_wc    (Lara Wave 1 — cycle times + WC resolution)
        │         weekly qty → weekly hours (qty × cycle_time_min / 60)
        │
        ▼
fact_translated_project_demand_weekly
        │
        ├── + fact_wc_capacity_weekly    (Lara Wave 1 — approved baseline load)
        ├── + dim_wc_scenario_limits     (Lara Wave 1 — upside/downside shift variants)
        │
        ▼
fact_scenario_capacity_weekly
  (scenario × plant × WC × year × week)
  Fields: incremental_load, planned_load, total_load, available,
          remaining, overload_hours, overload_pct, bottleneck_flag
        │
        ▼
fact_capacity_bottleneck_summary
  (scenario × plant × WC)
  Fields: severity, top_driver_project_count,
          suggested_capacity_lever, explanation_note
```

---

## Inputs Consumed

| Input | Source | Used for |
|---|---|---|
| `fact_pipeline_monthly` | Luigi `build_fact_pipeline_monthly()` | Base demand rows |
| `scenario_project_demand_seed` | Luigi `build_scenario_project_demand_seed()` | 3 scenario variants |
| `bridge_month_week_calendar` | Lara Wave 1 | Month → week allocation weights |
| `bridge_material_tool_wc` | Lara Wave 1 | WC routing + cycle times |
| `fact_wc_capacity_weekly` | Lara Wave 1 | Approved baseline load + available hours |
| `dim_wc_scenario_limits` | Lara Wave 1 | Upside/downside capacity variants |

---

## Output Schemas

### `fact_translated_project_demand_weekly`
Grain: `scenario × plant × material × work_center × year × week`

| Column | Notes |
|---|---|
| `scenario_name` | all_in / expected_value / high_confidence |
| `scenario_confidence` | 1.0 / 0.5 / 0.9 or 0.6 |
| `project_id` | from pipeline |
| `plant` | NW01..NW15 |
| `material` | SAP code |
| `work_center` | full WC code P01_{plant}_{wc} |
| `year`, `week` | ISO year/week |
| `demand_qty` | pieces/week (monthly qty × allocation_weight) |
| `demand_hours` | hours/week (qty × cycle_time_min / 60) |
| `reason_code` | TRANSLATED / NO_TOOL_MAPPING / MISSING_CYCLE_TIME |

### `fact_scenario_capacity_weekly`
Grain: `scenario × plant × work_center × year × week`

| Column | Notes |
|---|---|
| `incremental_load_hours` | pipeline demand hours (new, not yet approved) |
| `planned_load_hours` | approved baseline from fact_wc_capacity_weekly |
| `total_load_hours` | planned + incremental |
| `available_capacity_hours` | baseline or variant (upside_1/upside_2) |
| `remaining_capacity_hours` | max(0, available − total) |
| `overload_hours` | max(0, total − available) |
| `overload_pct` | total / available (>85% = warning, >100% = critical) |
| `bottleneck_flag` | True when overload_pct ≥ 0.85 |

Also produces `{scenario}__upside_1` and `{scenario}__upside_2` rows showing what shift-level changes would unlock.

### `fact_capacity_bottleneck_summary`
Grain: `scenario × plant × work_center`

| Column | Notes |
|---|---|
| `bottleneck_severity` | warning / critical |
| `top_driver_project_count` | distinct projects driving demand at this WC |
| `suggested_capacity_lever` | upside_1 / upside_2 / no_lever_available |
| `explanation_note` | human-readable: severity, utilisation%, overload hours, lever |

---

## Validation Status

### Unit tests (20/20 pass — no Excel required)
- `fact_translated_project_demand_weekly`: demand_qty positive, monthly qty conserved ✓
- `fact_scenario_capacity_weekly`: unique at grain, overload ≥ 0, total = planned + incremental ✓
- Overload calculation reproducible (deterministic given fixed inputs) ✓
- Bottleneck severity bands consistent with thresholds ✓
- Capacity variants produce additional scenario rows ✓
- Empty bottleneck input returns empty summary ✓

### Integration tests (require `hackathon_dataset.xlsx`)
```bash
pytest project/tests/test_wave2_lara.py -m integration
```

---

## Legacy Module Decisions

| Legacy component | Decision | Notes |
|---|---|---|
| `clarix.engine.build_demand_by_wc_week()` | **REPLACE** | Even-spread allocation replaced by `demand_translation.py` with calendar-weighted allocation |
| `clarix.engine.build_utilization()` | **REPLACE** | Logic preserved, but now consumes `fact_translated_project_demand_weekly` instead of raw pipeline |
| `clarix.engine.detect_bottlenecks()` | **REPLACE** | Logic preserved in `bottleneck_engine.py` with richer output (levers, explanation notes) |
| `clarix.engine._apply_scenario()` | **REPLACE** | Replaced by Luigi's `build_scenario_project_demand_seed()` |
| `clarix.engine.SCENARIOS` | **ADAPT** | Names standardised to contracts.md (expected → expected_value, monte_carlo → monte_carlo_light) |

---

## Blockers for Wave 3

| Blocker | Severity | Notes |
|---|---|---|
| `fact_translated_project_demand_weekly` may be sparse if `bridge_month_week_calendar` falls back to `plant="ALL"` | Medium | Calendar bridge fallback lacks per-plant working-day weights; integration with real 2_4 sheet resolves this |
| `dim_wc_scenario_limits.available_hours_variant` nulls for some WCs | Low | Lever suggestion falls back to `no_lever_available` safely |
| Logistics and disruption risk layers absent | High | Wave 3 scope — `fact_integrated_risk` and `fact_planner_actions` not yet built |
| Agent tools not yet wired to Wave 2 outputs | High | `clarix.agent` still calls legacy engine functions; needs adapter update |

---

## How to Run

```bash
# Build all Wave 2 outputs (saves parquet to project/data/wave2/)
python3 -m project.src.wave2.runner

# With custom paths
python3 -m project.src.wave2.runner --xlsx data/hackathon_dataset.xlsx --out project/data/wave2/ --csv

# Unit tests only
pytest project/tests/test_wave2_lara.py -m "not integration" -v

# Integration tests (requires Excel)
pytest project/tests/test_wave2_lara.py -m integration -v
```
