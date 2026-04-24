# known_limitations_frontend.md
## Clarix — Known Frontend Limitations

Date: 2026-04-18  
Wave: 5 (Final)

---

## Critical Limitations (must address before production use)

### L01 — Wave 7 CSVs must be pre-generated
**Area:** Data pipeline  
**Symptom:** Advanced pages (Scope & Region, Quarter History, Capacity & Maintenance, Sourcing & Delivery, Logistics & Disruptions, Final Actions, Overview W7 layer) show `ui.empty_state()` or `st.stop()` if CSVs are missing.  
**Cause:** `_load_w7()` loads from `project/data/processed/` — if Wave 6/7 runners haven't been executed, the directory is empty or stale.  
**Mitigation:** Run `python -m project.src.wave6.runner` and `python -m project.src.wave7.runner` before demo. The demo script includes this step.  
**Fix path:** Add a startup check that detects missing CSVs and shows a one-time warning banner on the sidebar.

### L02 — Excel load is slow on cold start
**Area:** Performance  
**Symptom:** First page load takes ~10 seconds while `hackathon_dataset.xlsx` (~26 MB, 13 sheets) is parsed.  
**Cause:** `load_canonical()` reads all sheets regardless of which page is active.  
**Mitigation:** `@st.cache_resource` holds the parsed data in memory — all subsequent loads are instant. Pre-warm by loading one page before the demo.  
**Fix path:** Lazy-load sheets; only parse sheets needed by the active page.

---

## Functional Limitations

### L03 — Demo mode does not enforce filter state
**Area:** Demo mode  
**Symptom:** A presenter who changes scenario/plant/quarter mid-demo will see different data than the scripted story describes.  
**Cause:** `_render_demo_banner()` only shows the banner; it does not write to `st.session_state` to reset filters.  
**Mitigation:** All defaults are set to best demo values at startup (base scenario, Q1, first region). Demo script instructs presenter not to change them.  
**Fix path:** Add a `reset_filters_for_demo()` call inside the demo mode toggle button handler.

### L04 — Deprecated "Actions" page is dead code, not deleted
**Area:** Code hygiene  
**Location:** `app.py` ~line 1434, `elif page == "Actions":`  
**Symptom:** No user impact — the page is unreachable via the sidebar. The code block occupies ~80 lines.  
**Cause:** Kept to avoid accidental breakage during hackathon crunch.  
**Fix path:** Delete the `elif page == "Actions":` block after the demo.

### L05 — Final Actions filter state is not persisted across page navigations
**Area:** UX / filter state  
**Symptom:** Switching away from Final Actions and returning resets the scenario/type/plant/confidence filter bar.  
**Cause:** Filter widgets use local widget state (no `key=` bound to `st.session_state`).  
**Fix path:** Bind each filter widget with `key="fa_filter_scenario"` etc. and read from `st.session_state`.

### L06 — Ask Clarix history is reset on page navigation
**Area:** Agent / UX  
**Symptom:** Navigating away from Ask Clarix and returning clears the conversation history.  
**Cause:** `chat_history` is initialized to `[]` at the top of the page block rather than in a `if "chat_history" not in st.session_state` guard.  
**Fix path:** Move initialization to a top-of-app guard block.

### L07 — W7 scenario filter (`w7_scenario`) is global but not always visible
**Area:** Filter UX  
**Symptom:** Users changing the W7 scenario on one page may be surprised it affects other advanced pages.  
**Cause:** `w7_scenario` is a shared sidebar filter — intentional for consistency, but not labeled clearly.  
**Fix path:** Add a tooltip or help text to the W7 scenario widget explaining its scope.

---

## Data / Accuracy Limitations

### L08 — Shipping lanes, country cost indices, disruption scenarios are synthetic
**Area:** Data accuracy  
**Symptom:** Logistics & Disruptions page shows `SYNTHETIC` badges and a `ui.assumption_panel()` callout.  
**Cause:** Real Danfoss logistics data was not available in the hackathon dataset.  
**Impact:** Financial figures (landed cost proxy, disruption cost estimates) are illustrative only.

### L09 — Confidence scores are model-generated, not validated
**Area:** Data accuracy  
**Symptom:** Final Actions page shows `confidence` values (0–1) per planner action.  
**Cause:** Confidence is derived from Wave 7 `risk_score_v2` dimensions, not from historical planner accuracy.  
**Impact:** High-confidence actions should be treated as strong signals, not guarantees.

### L10 — Probability-weighted demand uses 10/25/50/75/90% buckets as-is
**Area:** Model accuracy  
**Symptom:** Demand forecasts do not reflect any ML calibration of the stated probabilities.  
**Cause:** Out-of-scope for the hackathon (HINTS.md explicitly notes this).  
**Impact:** Demand estimates may over- or under-weight projects near threshold probabilities.

---

## Brittle Areas

### B01 — `effective_capacity_timeline()` requires `work_center` column
**Area:** charts.py  
**Risk:** If `fact_effective_capacity_weekly_v2.csv` is generated without a `work_center` column, the Capacity & Maintenance page falls back to `ui.empty_state()` for that section.  
**Location:** `clarix/charts.py`, `effective_capacity_timeline()` function.

### B02 — `_DASH = "\u2014"` constant must remain before first f-string use
**Area:** app.py  
**Risk:** Python 3.11+ forbids backslash escapes inside f-string `{}` expressions. `_DASH` works around this. If someone removes the constant or moves it below the first f-string that uses it, a `SyntaxError` will result.  
**Location:** `app.py` line ~30.

### B03 — `_load_w7()` key schema must match page expectations
**Area:** Data adapter  
**Risk:** If `demo_layer.load_all_processed()` renames or drops a key, the affected page will receive an empty DataFrame and show `ui.empty_state()` rather than raising a visible error.  
**Location:** `app.py` `_load_w7()` function; `project/src/app/demo_layer.py` `_REAL_FILES`.

### B04 — Plotly version mismatch can cause silent chart failures
**Area:** Dependency  
**Risk:** `clarix/charts.py` uses `go.Figure` with Plotly 5.x API. Plotly 4.x has incompatible argument names.  
**Mitigation:** `requirements.txt` pins `plotly>=5.18`. Do not downgrade.

### B05 — Single-file app.py is large (~2600 lines)
**Area:** Maintainability  
**Risk:** Any syntax error anywhere in the file prevents the entire app from starting. Large edits have a higher chance of introducing whitespace or indentation errors.  
**Fix path:** After the hackathon, split into `pages/` directory using Streamlit multi-page app convention.
