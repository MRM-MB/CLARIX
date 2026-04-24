# frontend_risk_register.md
## Frontend Risk Register

Date: 2026-04-18
Severity: **CRITICAL / HIGH / MEDIUM / LOW**
Likelihood: **High / Medium / Low**

---

## Active risks

### R01 — Wave 6/7 CSVs missing at demo time
**Severity:** CRITICAL | **Likelihood:** Medium

**Description:** All Wave 7 pages depend on `project/data/processed/*.csv`. If the pipeline runners have not been executed, every Wave 7 page will show empty DataFrames or warnings, making the workflow half of the demo non-functional.

**Current state:** `demo_layer.py` emits `warnings.warn()` for missing files and returns empty DataFrames silently. App.py Wave 7 pages do not check for this and render broken charts with no user-visible explanation.

**Mitigation:**
1. Add `get_w7_data()` with `@st.cache_data` wrapper that returns `{}` when demo_layer unavailable.
2. Add a `st.info()` / `st.warning()` check at the top of every Wave 7 page: `if w7["planner_actions_v2"].empty: st.warning("Run the Wave 7 pipeline first: python -m project.src.wave7.runner"); st.stop()`
3. Pre-run all runners before the demo and commit the generated CSVs to `project/data/processed/`.

**Owner:** Wave 1 implementation (first task)

---

### R02 — `load_all_processed()` called without caching
**Severity:** HIGH | **Likelihood:** High (it will happen on every page switch)

**Description:** `load_all_processed()` reads up to 17 CSV files on each call. In the current app.py, Wave 7 pages call this inline with no `@st.cache_data` wrapper. Every sidebar navigation re-reads all CSVs, causing 2–5 second delays per page switch during the demo.

**Current state:** No caching wrapper exists. Each of the 5 Wave 7 pages re-reads independently.

**Mitigation:**
```python
@st.cache_data(show_spinner=False)
def get_w7_data():
    if _DEMO_LAYER_AVAILABLE:
        return load_all_processed()
    return {}
```
Call once at app top level, pass result to page functions.

**Owner:** Wave 1 implementation (second task after R01)

---

### R03 — Excel workbook load time blocks demo start
**Severity:** HIGH | **Likelihood:** High

**Description:** `load_canonical()` reads a 26 MB Excel file with 13 sheets. On first load (no parquet cache) this takes 15–45 seconds. If the cache is cleared or the demo runs on a fresh machine, the app will spin for a long time before showing anything.

**Current state:** Parquet cache exists (`data/.clarix_cache/`) but is `.gitignore`-able and may not be present on demo machine. The `st.cache_resource` spinner says "Loading workbook + building canonical tables..." — visible to judges.

**Mitigation:**
1. Pre-generate parquet cache on the demo machine before the presentation.
2. Add a startup progress message: `st.toast("Building data model from Excel — this takes ~30s on first run")`.
3. Ensure `.clarix_cache/` is either committed or regenerated in the demo setup script.

**Owner:** Demo setup procedure

---

### R04 — "Actions" page (Wave 6 draft) conflicts with "Final Actions" (Wave 7)
**Severity:** HIGH | **Likelihood:** High (already exists)

**Description:** Both "Actions" (L1078) and "Final Actions" (L1741) exist in the sidebar. They show overlapping data from different data sources. A demo judge seeing both will be confused about which is authoritative.

**Current state:** "Actions" loads `fact_planner_actions_v2` via `derive_planner_actions()` from demo_layer; "Final Actions" loads the same CSV directly. Two pages, same data, different presentation.

**Mitigation:** Remove "Actions" from the sidebar radio list and delete its `elif` block (L1078–L1269). Migrate any unique content (e.g. quality flags panel) into a tab in "Final Actions". This is a pure deletion — no new code needed.

**Owner:** Wave 1 implementation

---

### R05 — Sidebar has 13 items with no grouping
**Severity:** MEDIUM | **Likelihood:** Certain (already exists)

**Description:** A flat 13-item radio list with no visual grouping fails to communicate the workflow narrative. Demo judges may navigate randomly rather than following the intended story.

**Current state:** All 13 pages listed as a flat radio group.

**Mitigation:** Insert markdown section headers (`### WORKFLOW`, `### TOOLS`) between radio items. Since Streamlit's `st.radio` doesn't support grouping natively, use markdown above the radio and a reduced list (9 items after removing duplicates). Optionally use emoji step numbers (1. Overview, 2. Scope...) to make sequence obvious.

**Owner:** Wave 1 implementation (low-effort, high narrative impact)

---

### R06 — Explanation trace JSON not exposed in Actions page
**Severity:** MEDIUM | **Likelihood:** Certain (already exists)

**Description:** `fact_planner_actions_v2` contains an `explanation_trace` column with a rich JSON object showing `top_driver`, `action_selected`, `maint_severity`, `caution_carry_over`, `reroute_target`. This is the primary auditability feature of Wave 7 Lara but is not displayed anywhere in the UI.

**Current state:** The column exists in the DataFrame but is not rendered.

**Mitigation:** In the Actions & Recommendations page, add a `st.expander("Why this action?")` per row (or for the selected row in a table) that parses and displays the JSON fields as labelled key-value pairs. Use `json.loads(trace)` and format inline.

**Owner:** Wave 1 implementation

---

### R07 — Wave 6/7 sidebar filters appear/disappear conditionally
**Severity:** MEDIUM | **Likelihood:** Medium

**Description:** Region, Quarter, and Maintenance scenario filters are shown only when `page in _WAVE7_PAGES`. When navigating away from Wave 7 pages these controls vanish, causing layout shifts and confusing users who expect consistent sidebar structure.

**Current state:** `if page in _WAVE7_PAGES:` block in sidebar.

**Mitigation:** Always show Region selector (it's useful for the Overview too). Show Quarter and Maintenance scenario only on pages that actively use them, but keep them at the bottom of the sidebar so their appearance doesn't shift other controls upward.

**Owner:** Wave 1 implementation

---

### R08 — `derive_planner_actions()` in demo_layer is a stale fallback
**Severity:** MEDIUM | **Likelihood:** Low (only triggered if CSV missing)

**Description:** `derive_planner_actions()` in `demo_layer.py` re-derives planner actions from `risk_base` + `action_policy` at runtime. This is the Wave 4/5 logic, not Wave 7 Lara. If `fact_planner_actions_v2.csv` is missing, pages may silently fall back to inferior actions without the user knowing.

**Current state:** `demo_layer.py` exports `derive_planner_actions()` and app.py imports it. It is used in at least one page as a fallback.

**Mitigation:** Remove the fallback entirely. If `fact_planner_actions_v2.csv` is missing, show `st.warning` and stop. Never silently degrade to a different algorithm.

**Owner:** Wave 1 implementation

---

### R09 — ANTHROPIC_API_KEY absence silently degrades Ask Clarix
**Severity:** LOW | **Likelihood:** Medium

**Description:** Without the API key, Ask Clarix uses the deterministic fallback planner. The UI shows a warning but the degradation may surprise judges if the demo machine doesn't have the key set.

**Current state:** `_fallback_planner()` exists and handles the 3 main intent categories. The UI shows a pill "PLANNER MODE".

**Mitigation:** Add a dedicated "demo key check" in the demo setup checklist. Consider storing the key in a `.env` file and loading with `python-dotenv`. The fallback is already good — no code change needed, just operational awareness.

**Owner:** Demo setup procedure

---

### R10 — No synthetic vs real data visual indicator
**Severity:** LOW | **Likelihood:** Medium

**Description:** `dim_service_level_policy_synth.csv` is loaded from a different path (`processed/` root vs `project/data/processed/`). Users and judges cannot tell which parts of the data are real vs synthetic without reading the code.

**Current state:** No badge or indicator in the UI.

**Mitigation:** On pages that use synth data (currently only service_level_policy), add a small `SYNTHETIC` pill badge in the section header. The wave0.md UX principle "make synthetic vs real data visible but non-intrusive" requires this.

**Owner:** Wave 1 implementation (minor)

---

## Risk summary

| ID | Description | Severity | Likelihood | Status |
|----|-------------|----------|------------|--------|
| R01 | Wave 6/7 CSVs missing at demo time | CRITICAL | Medium | Open |
| R02 | `load_all_processed()` uncached | HIGH | High | Open |
| R03 | Excel load time blocks demo start | HIGH | High | Open |
| R04 | Duplicate Actions / Final Actions pages | HIGH | High | Open |
| R05 | Flat 13-item sidebar | MEDIUM | Certain | Open |
| R06 | Explanation trace not exposed | MEDIUM | Certain | Open |
| R07 | Sidebar filters layout shift | MEDIUM | Medium | Open |
| R08 | `derive_planner_actions()` stale fallback | MEDIUM | Low | Open |
| R09 | ANTHROPIC_API_KEY missing at demo | LOW | Medium | Open |
| R10 | No synthetic data indicator | LOW | Medium | Open |

---

## Recommended fix order (Wave 1 priority)

1. **R02** — Add `@st.cache_data` wrapper for `load_all_processed()` (5 min, unblocks all Wave 7 pages)
2. **R01** — Add graceful degradation guards on all Wave 7 pages (20 min, makes demo safe)
3. **R04** — Remove "Actions" page from sidebar, consolidate into Final Actions (15 min)
4. **R06** — Expose `explanation_trace` in Actions page (30 min, high demo value)
5. **R05** — Add sidebar section grouping (15 min, narrative clarity)
6. **R07** — Always-visible region filter (10 min)
7. **R08** — Remove `derive_planner_actions()` fallback (10 min)
8. **R03** — Add demo setup instructions for cache pre-warming (operational, no code)
9. **R10** — Add SYNTHETIC badge (10 min)
10. **R09** — Add `.env` setup to demo checklist (operational)
