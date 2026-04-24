# design_system.md
## Clarix Design System — Wave 1

Date: 2026-04-18

---

## Design principles

1. **Workflow-first.** Every page is a step in a story. Visual hierarchy guides the eye from "what's happening" (KPIs) to "why" (charts) to "what to do" (actions/tables).
2. **Product-owner readable.** Numbers are rounded, labeled, and contextualized. No raw floats without units.
3. **Explainability visible but non-intrusive.** Reasoning is available (expandable), not primary.
4. **Synthetic data declared.** Any non-real data carries a badge. Never hidden.
5. **Demo-safe on projectors.** High contrast dark theme, large fonts for KPIs, red only for alarms.

---

## Color palette

Defined in `clarix/charts.py`. Imported as named constants.

### Semantic mapping

| Semantic | Constant | Hex | Use |
|----------|----------|-----|-----|
| Background primary | `BG` | `#0E1117` | App background |
| Background elevated | `BG_SOFT` | `#161B22` | Cards, panels |
| Background tinted | `SLATE_TINT` | `#21262D` | Nested cards |
| Panel border | `LINE` | `#30363D` | All borders |
| Primary text | `INK` | `#E6EDF3` | Headings, values |
| Secondary text | `INK_SOFT` | `#C9D1D9` | Labels, sub-text |
| Muted text | `MUTED` | `#8B949E` | Captions, axes |
| Alarm / critical | `ACCENT` | `#ef4444` | Critical alerts only |
| Brand red | `ACCENT_BRAND` | `#bb2727` | Active nav, borders |
| Warning | `ACCENT_SOFT` | `#fb7185` | Warn KPI values |
| Healthy / ok | `OK_GREEN` | `#22C55E` | Safe state |
| Neutral accent | `SLATE_SOFT` | `#64748B` | Info bars, neutral |

### KPI card modifiers (CSS classes)

| Class | Left border | Value color | Use case |
|-------|-------------|-------------|---------|
| `kpi-accent` | `#ef4444` | `#fb7185` | Critical metric (overload, high risk) |
| `kpi-warn` | `#fb7185` | `#fb7185` | Warning metric (shortfall, caution) |
| `kpi-ok` | `#22C55E` | `#22C55E` | Healthy metric |
| `kpi-slate` | `#64748B` | `#E6EDF3` | Neutral / count metric |

### Status pill classes

| Class | Background | Text | Use case |
|-------|------------|------|---------|
| `pill-ok` | green tint | `#4ADE80` | Feasible, on-time, healthy |
| `pill-warn` | red-pink tint | `#FCA5A5` | Warning state |
| `pill-crit` | red tint | `#FECACA` | Critical / infeasible |
| `pill-slate` | slate tint | `#CBD5E1` | Neutral / unknown |
| `pill-info` | blue tint | `#7DD3FC` | Informational |

---

## Typography

| Element | Font | Size | Weight | Color |
|---------|------|------|--------|-------|
| App name | Inter | 24px | 800 | `#ACCENT_DARK` |
| Page title | Inter | 26px | 800 | `INK` |
| Page subtitle | Inter | 12px | 600 | `MUTED` (uppercase) |
| Section header | Inter | 19px | 700 | `INK` |
| Section sub | Inter | 13px | 400 | `INK_SOFT` |
| KPI label | Inter | 11px | 700 | `MUTED` (uppercase) |
| KPI value | Inter | 30px | 800 | per variant |
| KPI sub | Inter | 12px | 400 | `INK_SOFT` |
| Body text | Inter | 14px | 400 | `INK` |
| Caption / badge | Inter | 11px | 600 | contextual |
| Code / trace | JetBrains Mono | 12px | 400 | `INK_SOFT` |

---

## Layout grid

| Pattern | Columns | Use |
|---------|---------|-----|
| KPI row | 4 equal | Top of every page |
| Two-up charts | 2 × 50% | Side-by-side charts |
| Full-width | 1 × 100% | Heatmaps, tables, action lists |
| Three-up metrics | 3 equal | Secondary metric rows |
| Sidebar | fixed ~280px | Nav + global filters |

Max content width: `1500px` (set via `.block-container`).

---

## Component specifications

### Page header
```
[logo 110px] | [title 26px/800] [subtitle 12px/600 uppercase muted]
────────────────────────────────────────────────────── (1px LINE border)
```

### KPI card
```
┌─────────────────────────────────┐
│ LABEL (11px uppercase muted)    │ ← left accent border (4px)
│ VALUE (30px/800)                │
│ sub (12px ink-soft)             │
└─────────────────────────────────┘
```

### Section header
```
▌ TITLE (19px/700)    ← 4px accent-brand bar on left
  subtitle (13px ink-soft, indented 14px)
```

### Data source strip
```
[REAL] fact_planner_actions_v2  |  [SYNTHETIC] transit times  |  [DERIVED] risk scores
(11px muted, pills inline, top of page body)
```

### Empty state
```
┌─────────────────────────────────────────────┐
│         (icon or emoji)                      │
│   Title (16px/700 ink)                       │
│   Message (13px ink-soft)                    │
│   Hint: command or action (12px muted code)  │
└─────────────────────────────────────────────┘
```

### Explanation / "Why this recommendation?" panel
```
┌────────────────────────────────────────────────────────┐
│ ▌ PROJECT_ID  [MEDIUM CAUTION pill]                     │ ← 4px accent-brand left border
│                                                         │
│ Recommended action: buy_now                             │
│ Reason: Sourcing risk above threshold (0.75)            │
│ Expected effect: reduce_shortage                        │
│ Quarter caution: carried from Q1 service violation      │
└────────────────────────────────────────────────────────┘
  [▼ Full explanation trace]     (collapsible expander)
  [▼ Service memory history]     (collapsible expander)
```

### Assumption panel
```
┌──────────────────────────────────────────────────────┐
│ ⚠  ASSUMPTION NOTE (bg: slate-wash, left: slate)    │
│    Text in 13px ink                                   │
└──────────────────────────────────────────────────────┘
```

---

## Chart conventions

All charts follow the `_theme()` contract from `clarix/charts.py`:
- `template="plotly_dark"`
- `paper_bgcolor=BG_SOFT`, `plot_bgcolor=BG_SOFT`
- `font=dict(family="Inter, Segoe UI", size=12, color=INK)`
- Grid: `gridcolor=LINE`
- Legend: horizontal, above chart

### Color usage rules in charts

| Situation | Color |
|-----------|-------|
| Critical / overload | `ACCENT` (#ef4444) |
| Warning / elevated | `ACCENT_SOFT` (#fb7185) |
| Healthy / ok | `OK_GREEN` (#22C55E) |
| Neutral bar / line | `SLATE_SOFT` (#64748B) |
| Background bar (capacity) | `SLATE_TINT` (#21262D) |
| Sequential scale (low→high risk) | `[SLATE_DARK, ACCENT_SOFT, ACCENT]` |

### Chart height standards

| Chart type | Height |
|------------|--------|
| Donut / pie | 160px |
| Scenario compare bar | 320px |
| Funnel | 320px |
| Line / area | 380px |
| Table | 80 + (28 × rows), max 600px |
| Heatmap | max(380, 22 × n_wcs) |
| Scatter | 450px |
| Treemap | 440px |
| Horizontal action bar | 400px |

---

## Interaction model

| Interaction | Component | Behavior |
|-------------|-----------|---------|
| Page navigation | `st.radio` sidebar | Full page re-render |
| Filter change | `st.selectbox` sidebar | All cached queries invalidate and re-run |
| WC drilldown | `st.selectbox` in page | Local re-render of drilldown chart only |
| Feasibility run | `st.button` primary | `st.spinner` + `st.session_state` result |
| Explanation expand | `st.expander` | In-place expand/collapse |
| Basket clear | `st.button` | `st.session_state.basket = []` + `st.rerun()` |
| Chat submit | `st.chat_input` | Append + `st.rerun()` |
| Cache reset | `st.button` primary sidebar | Clear all caches + `st.rerun()` |

---

## Accessibility and demo-safety

- Minimum font size: 11px (labels) — readable on 1080p projected screen at 6 meters
- Color: never use color as the only differentiator — always pair with text label or pill
- Alarm red (`ACCENT`) reserved for genuine critical states only — no decorative use
- All KPI values use `font-weight: 800` — clearly readable at a distance
- Chart titles always present — no chart without a label
- Empty states always explain WHY and WHAT TO DO — no blank pages
