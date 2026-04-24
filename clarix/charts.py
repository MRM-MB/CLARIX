"""
clarix.charts
=============
Plotly chart factories shared across pages. All return go.Figure with consistent theme.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Brand palette - DARK MODE (blends with Streamlit's dark chrome)
# Primary surfaces are GitHub-dark inspired; red is reserved for ALARM only.
SLATE        = "#475569"   # mid-slate accent (lines, mid bars)
SLATE_DARK   = "#1E293B"   # deep panel
SLATE_SOFT   = "#64748B"   # soft text / mid bars
SLATE_TINT   = "#21262D"   # elevated panel (cards inside cards)
SLATE_WASH   = "#161B22"   # secondary panel background

ACCENT       = "#ef4444"   # alarm red (brighter on dark to keep contrast)
ACCENT_DARK  = "#dc2626"   # deep red (worst alarm)
ACCENT_SOFT  = "#fb7185"   # soft red (warn highlight on dark)
ACCENT_WASH  = "#2A1414"   # dark red-tinted bg for callouts
ACCENT_BRAND = "#bb2727"   # original brand red (for borders / pure brand)

OK_GREEN     = "#22C55E"   # safe / healthy on dark
OK_GREEN_SOFT= "#86EFAC"

INK          = "#E6EDF3"   # main text on dark
INK_SOFT     = "#C9D1D9"   # secondary text
MUTED        = "#8B949E"   # tertiary text / axes
LINE         = "#30363D"   # gridlines / borders
BG           = "#0E1117"   # primary dark bg (matches Streamlit)
BG_SOFT      = "#161B22"   # panel bg (matches Streamlit secondary)

# Aliases (for legacy references)
NAVY         = SLATE_DARK
NAVY_SOFT    = SLATE_SOFT
GOLD         = ACCENT_SOFT
TEAL         = SLATE_SOFT
GREEN        = OK_GREEN
WARN         = ACCENT_SOFT
CRIT         = ACCENT_DARK
GREY         = MUTED
GREY_SOFT    = LINE

# Heatmap stops normalized to zmin=0, zmax=1.5
# Cool dark for healthy -> warm for warn -> red for critical -> deep red overload
UTIL_SCALE = [
    [0.00,           SLATE_DARK],
    [0.50 / 1.5,     "#3B4252"],   # mid slate
    [0.85 / 1.5,     "#9C2A2A"],   # mid red - first warning
    [1.00 / 1.5,     ACCENT],      # red - critical
    [1.00,           ACCENT_DARK], # deep red - overload
]


def _theme(fig: go.Figure, *, height: int = 420, title: str | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=10, r=10, t=50 if title else 20, b=10),
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=INK),
        title=dict(text=title, font=dict(size=15, color=INK)) if title else None,
        plot_bgcolor=BG_SOFT, paper_bgcolor=BG_SOFT,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(color=INK_SOFT)),
    )
    fig.update_xaxes(showgrid=True, gridcolor=LINE, zeroline=False, color=INK_SOFT)
    fig.update_yaxes(showgrid=True, gridcolor=LINE, zeroline=False, color=INK_SOFT)
    return fig


def utilization_heatmap(util: pd.DataFrame, *, top_n: int = 25, title: str | None = None) -> go.Figure:
    if util.empty:
        return _theme(go.Figure(), title=title or "No data")
    # rank by peak utilization
    peak = util.groupby("work_center")["utilization"].max().sort_values(ascending=False)
    keep = peak.head(top_n).index.tolist()
    sub = util[util["work_center"].isin(keep)].copy()
    sub["yearweek"] = sub["year"].astype(str) + "-W" + sub["week"].astype(str).str.zfill(2)
    pivot = (sub.pivot_table(index="work_center", columns="yearweek",
                              values="utilization", aggfunc="max")
                .reindex(keep))
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=UTIL_SCALE, zmin=0, zmax=1.5,
        colorbar=dict(title="Util", tickformat=".0%"),
        hovertemplate="<b>%{y}</b><br>%{x}<br>Utilization: %{z:.0%}<extra></extra>",
    ))
    return _theme(fig, height=max(380, 22 * len(keep)), title=title)


def utilization_lines(util: pd.DataFrame, work_center: str, *, title: str | None = None) -> go.Figure:
    sub = util[util["work_center"] == work_center].sort_values(["year", "week"])
    if sub.empty:
        return _theme(go.Figure(), title=f"{work_center}: no data")
    sub = sub.copy()
    sub["yearweek"] = sub["year"].astype(str) + "-W" + sub["week"].astype(str).str.zfill(2)
    fig = go.Figure()
    fig.add_bar(x=sub["yearweek"], y=sub["available_hours"], name="Available capacity (h)",
                marker_color=SLATE_TINT, hovertemplate="%{y:.1f}h<extra>capacity</extra>")
    fig.add_bar(x=sub["yearweek"], y=sub["demand_hours"], name="Demand (h)",
                marker_color=SLATE_SOFT, hovertemplate="%{y:.1f}h<extra>demand</extra>")
    fig.add_hline(y=sub["available_hours"].max() * 0.85, line_dash="dot", line_color=ACCENT_SOFT,
                  annotation_text="warn 85%", annotation_position="top left",
                  annotation_font_color=ACCENT_DARK)
    fig.add_hline(y=sub["available_hours"].max(), line_dash="dash", line_color=ACCENT,
                  annotation_text="100% capacity", annotation_position="top right",
                  annotation_font_color=ACCENT_DARK)
    fig.update_layout(barmode="overlay", bargap=0.05)
    return _theme(fig, height=380, title=title or work_center)


def scenario_compare_bar(rows: list[dict]) -> go.Figure:
    if not rows:
        return _theme(go.Figure())
    df = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_bar(x=df["label"], y=df["peak_util"], name="Peak utilization",
                marker_color=[ACCENT_DARK if v >= 1 else ACCENT_SOFT if v >= 0.85 else SLATE_SOFT
                              for v in df["peak_util"]],
                hovertemplate="%{y:.1%}<extra>peak util</extra>",
                text=[f"{v:.0%}" for v in df["peak_util"]], textposition="outside",
                textfont=dict(color=INK))
    fig.update_yaxes(tickformat=".0%")
    fig.add_hline(y=1.0, line_dash="dot", line_color=ACCENT_DARK,
                  annotation_text="100% critical", annotation_position="right",
                  annotation_font_color=ACCENT_DARK)
    fig.add_hline(y=0.85, line_dash="dot", line_color=ACCENT_SOFT,
                  annotation_text="85% warn", annotation_position="right",
                  annotation_font_color=ACCENT_DARK)
    return _theme(fig, height=320, title="Peak utilization by scenario")


def pipeline_funnel(pipe: pd.DataFrame) -> go.Figure:
    if pipe.empty:
        return _theme(go.Figure())
    total = pipe["qty"].sum()
    expected = pipe["expected_qty"].sum()
    high = pipe.loc[pipe["probability_frac"] >= 0.7, "qty"].sum()
    fig = go.Figure(go.Funnel(
        y=["All-in pipeline", "Expected value (qty x prob)", "High-confidence (>=70%)"],
        x=[total, expected, high],
        textinfo="value+percent initial",
        textfont=dict(color="#FFFFFF", size=13),
        marker=dict(color=[SLATE_SOFT, SLATE, SLATE_DARK],
                    line=dict(color=BG, width=1)),
    ))
    return _theme(fig, height=320, title="Pipeline scenario funnel (pcs across horizon)")


def plant_demand_treemap(pipe: pd.DataFrame) -> go.Figure:
    if pipe.empty:
        return _theme(go.Figure())
    df = (pipe.groupby(["plant", "type", "material_description"], as_index=False)["expected_qty"].sum())
    df = df[df["expected_qty"] > 0]
    fig = px.treemap(df, path=["plant", "type", "material_description"],
                     values="expected_qty", color="expected_qty",
                     color_continuous_scale=[SLATE_DARK, SLATE_SOFT, ACCENT_SOFT],
                     )
    fig.update_traces(root_color=BG_SOFT,
                      marker=dict(line=dict(color=BG, width=1)),
                      textfont=dict(size=12, family="Inter", color="#FFFFFF"))
    fig.update_layout(coloraxis_showscale=False)
    return _theme(fig, height=440, title="Expected demand by plant > type > material")


def sourcing_table_fig(sourcing: pd.DataFrame) -> go.Figure:
    if sourcing.empty:
        fig = go.Figure()
        fig.add_annotation(text="No component shortfalls detected.",
                           xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=14, color=GREY))
        return _theme(fig, height=200)
    df = sourcing.copy()
    if "order_by" in df.columns:
        df["order_by"] = pd.to_datetime(df["order_by"]).dt.strftime("%Y-%m-%d")
    if "period_date" in df.columns:
        df["period_date"] = pd.to_datetime(df["period_date"]).dt.strftime("%Y-%m")
    cols = [c for c in ["plant", "component_material", "component_description", "period_date",
                         "order_by", "lead_time_weeks", "component_demand_qty",
                         "atp_today", "safety_stock", "shortfall"] if c in df.columns]
    df = df[cols]
    fig = go.Figure(data=[go.Table(
        header=dict(values=cols, fill_color=SLATE_DARK, font=dict(color=INK, size=12),
                    align="left", height=32),
        cells=dict(values=[df[c] for c in cols],
                   fill_color=[[BG_SOFT, SLATE_TINT] * len(df)],
                   align="left", font=dict(size=11, color=INK), height=28),
    )])
    return _theme(fig, height=min(80 + 28 * len(df), 600))


def kpi_donut(value: float, total: float, label: str, color: str = NAVY) -> go.Figure:
    pct = 0.0 if total <= 0 else value / total
    fig = go.Figure(go.Pie(
        values=[pct, max(0, 1 - pct)],
        hole=0.75,
        marker=dict(colors=[color, GREY_SOFT]),
        textinfo="none", sort=False, direction="clockwise",
    ))
    fig.update_layout(
        showlegend=False,
        annotations=[dict(text=f"<b>{pct:.0%}</b><br><span style='font-size:11px;color:{GREY}'>{label}</span>",
                           x=0.5, y=0.5, font_size=20, showarrow=False)],
        margin=dict(l=0, r=0, t=0, b=0), height=160,
        paper_bgcolor=BG, plot_bgcolor=BG,
    )
    return fig


# ---------------------------------------------------------------------------
# Wave 1 additions — new chart factories
# ---------------------------------------------------------------------------

# Color map for action types (11 families) — brand palette only:
# red family for urgent/buy/escalate, green family for protective, slate for neutral/wait
_ACTION_COLORS: dict[str, str] = {
    "buy_now":                  ACCENT,         # #ef4444 red
    "escalate":                 ACCENT_DARK,    # #dc2626 deep red
    "hedge_inventory":          ACCENT_SOFT,    # #fb7185 soft red
    "upshift":                  "#F87171",      # light red
    "expedite_shipping":        "#B91C1C",      # crimson
    "split_production":         SLATE,          # neutral slate
    "reschedule":               SLATE_SOFT,     # lighter slate
    "reroute":                  SLATE_DARK,     # darker slate
    "shift_maintenance":        "#64748B",      # slate-500
    "protect_capacity_window":  OK_GREEN,       # #22c55e green
    "wait":                     MUTED,          # #8B949E grey
}

_CAUTION_COLORS: dict[str, str] = {
    "high":   ACCENT,
    "medium": ACCENT_SOFT,
    "low":    OK_GREEN,
}


def pipeline_timeline_bar(pq_df: pd.DataFrame, *, title: str | None = None) -> go.Figure:
    """Stacked bar: expected quantity per quarter, stacked by plant.

    Input: fact_pipeline_quarterly — columns: quarter_id, plant, expected_qty_quarter
    """
    if pq_df.empty or "quarter_id" not in pq_df.columns:
        return _theme(go.Figure(), title=title or "Pipeline by Quarter — no data")

    grp = (pq_df.groupby(["quarter_id", "plant"], as_index=False)["expected_qty_quarter"].sum()
           .sort_values("quarter_id"))
    plants = sorted(grp["plant"].dropna().unique().tolist())
    quarters = sorted(grp["quarter_id"].unique().tolist())

    colors = [SLATE_SOFT, ACCENT_SOFT, "#38BDF8", "#34D399", "#FBBF24",
              "#A855F7", "#F97316", ACCENT, SLATE, OK_GREEN]

    fig = go.Figure()
    for i, p in enumerate(plants):
        sub = grp[grp["plant"] == p].set_index("quarter_id")["expected_qty_quarter"]
        fig.add_bar(
            x=quarters,
            y=[float(sub.get(q, 0)) for q in quarters],
            name=p,
            marker_color=colors[i % len(colors)],
            hovertemplate=f"<b>{p}</b><br>%{{x}}<br>%{{y:,.1f}} pcs<extra></extra>",
        )
    fig.update_layout(barmode="stack")
    return _theme(fig, height=360, title=title or "Expected qty by quarter (probability-weighted)")


def maintenance_impact_bar(maint_df: pd.DataFrame, *, title: str | None = None) -> go.Figure:
    """Grouped bar: avg_maintenance_reduction_hours by plant × work_center, colored by severity.

    Input: fact_maintenance_impact_summary
    """
    if maint_df.empty or "avg_maintenance_reduction_hours" not in maint_df.columns:
        return _theme(go.Figure(), title=title or "Maintenance Impact — no data")

    df = maint_df.copy()
    df["wc_label"] = df["plant"].astype(str) + " / " + df["work_center"].astype(str)
    df["avg_maintenance_reduction_hours"] = pd.to_numeric(
        df["avg_maintenance_reduction_hours"], errors="coerce").fillna(0.0)
    df = df.sort_values("avg_maintenance_reduction_hours", ascending=True).tail(25)

    severity_color = df["impact_severity"].map(
        {"high": ACCENT, "medium": "#F97316", "low": OK_GREEN}
    ).fillna(SLATE_SOFT).tolist() if "impact_severity" in df.columns else SLATE_SOFT

    fig = go.Figure(go.Bar(
        x=df["avg_maintenance_reduction_hours"],
        y=df["wc_label"],
        orientation="h",
        marker_color=severity_color,
        hovertemplate="<b>%{y}</b><br>%{x:.1f}h avg reduction<extra></extra>",
    ))
    fig.update_xaxes(title="Avg reduction hours / week")
    return _theme(fig, height=max(300, 22 * len(df) + 80),
                  title=title or "Maintenance capacity reduction by work center")


def effective_capacity_timeline(
    eff_cap_df: pd.DataFrame,
    plant: str,
    scenario: str,
    *,
    work_center: str | None = None,
    title: str | None = None,
) -> go.Figure:
    """Line chart: effective available capacity vs total load hours over weeks.

    Bottleneck weeks shown as red markers.
    Input: fact_effective_capacity_weekly_v2
    """
    df = eff_cap_df.copy()
    if df.empty:
        return _theme(go.Figure(), title=title or "Effective Capacity — no data")

    if "plant" in df.columns:
        df = df[df["plant"] == plant]
    if "scenario" in df.columns:
        df = df[df["scenario"] == scenario]
    if work_center and "work_center" in df.columns:
        df = df[df["work_center"] == work_center]

    if df.empty:
        return _theme(go.Figure(), title=title or f"{plant} / {scenario} — no data")

    agg = (df.groupby("week", as_index=False)
           .agg(eff_cap=("effective_available_capacity_hours", "sum"),
                load=("total_load_hours", "sum"),
                bottleneck=("bottleneck_flag", "max")))
    agg = agg.sort_values("week")

    fig = go.Figure()
    fig.add_scatter(x=agg["week"], y=agg["eff_cap"], name="Effective capacity",
                    mode="lines", line=dict(color=OK_GREEN, width=2),
                    hovertemplate="%{x}<br>%{y:.1f}h capacity<extra></extra>")
    fig.add_scatter(x=agg["week"], y=agg["load"], name="Total load",
                    mode="lines", line=dict(color=ACCENT_SOFT, width=2),
                    hovertemplate="%{x}<br>%{y:.1f}h load<extra></extra>")

    bot_weeks = agg[agg["bottleneck"] == True]
    if not bot_weeks.empty:
        fig.add_scatter(x=bot_weeks["week"], y=bot_weeks["load"],
                        name="Bottleneck", mode="markers",
                        marker=dict(color=ACCENT, size=8, symbol="x"),
                        hovertemplate="<b>Bottleneck</b><br>%{x}<extra></extra>")

    fig.update_xaxes(title="Week", tickangle=-45)
    fig.update_yaxes(title="Hours")
    return _theme(fig, height=380, title=title or f"Effective capacity vs load — {plant} / {scenario}")


def delivery_commitment_chart(commit_df: pd.DataFrame, *, title: str | None = None) -> go.Figure:
    """Line chart: on-time feasible % and avg service violation risk by week.

    Input: fact_delivery_commitment_weekly
    """
    if commit_df.empty or "week" not in commit_df.columns:
        return _theme(go.Figure(), title=title or "Delivery Commitments — no data")

    df = commit_df.copy()
    has_on_time = "on_time_feasible_flag" in df.columns
    has_risk = "service_violation_risk" in df.columns

    if not has_on_time and not has_risk:
        return _theme(go.Figure(), title=title or "Delivery — missing columns")

    agg: dict[str, object] = {}
    if has_on_time:
        agg["on_time_pct"] = ("on_time_feasible_flag", "mean")
    if has_risk:
        agg["avg_risk"] = ("service_violation_risk", "mean")

    grp = df.groupby("week", as_index=False).agg(**agg).sort_values("week")

    fig = go.Figure()
    if has_on_time:
        fig.add_scatter(
            x=grp["week"], y=grp["on_time_pct"] * 100,
            name="On-time feasible %", mode="lines+markers",
            line=dict(color=OK_GREEN, width=2),
            hovertemplate="%{x}<br>%{y:.1f}% on-time<extra></extra>",
            yaxis="y",
        )
    if has_risk:
        fig.add_scatter(
            x=grp["week"], y=grp["avg_risk"],
            name="Avg service violation risk", mode="lines",
            line=dict(color=ACCENT_SOFT, width=2, dash="dot"),
            hovertemplate="%{x}<br>%{y:.3f} risk<extra></extra>",
            yaxis="y2",
        )
    fig.update_layout(
        yaxis=dict(title="On-time %", range=[0, 105], tickformat=".0f",
                   showgrid=True, gridcolor=LINE),
        yaxis2=dict(title="Avg risk", range=[0, 1.05], overlaying="y",
                    side="right", showgrid=False),
    )
    fig.update_xaxes(tickangle=-45)
    return _theme(fig, height=380, title=title or "Delivery commitments by week")


def risk_rollforward_waterfall(rollforward_df: pd.DataFrame, *, title: str | None = None) -> go.Figure:
    """Bar chart showing distribution of carry-forward caution levels.

    Input: fact_delivery_risk_rollforward — column: recommended_caution_level
    """
    if rollforward_df.empty or "recommended_caution_level" not in rollforward_df.columns:
        return _theme(go.Figure(), title=title or "Risk Roll-Forward — no data")

    counts = (rollforward_df["recommended_caution_level"]
              .value_counts()
              .reindex(["high", "medium", "low"], fill_value=0)
              .reset_index())
    counts.columns = ["level", "count"]

    fig = go.Figure(go.Bar(
        x=counts["level"],
        y=counts["count"],
        marker_color=[_CAUTION_COLORS.get(lv, SLATE_SOFT) for lv in counts["level"]],
        text=counts["count"],
        textposition="outside",
        textfont=dict(color=INK),
        hovertemplate="<b>%{x}</b><br>%{y} projects<extra></extra>",
    ))
    fig.update_xaxes(title="Caution level")
    fig.update_yaxes(title="Projects")
    return _theme(fig, height=320, title=title or "Carry-forward caution level distribution")


def action_score_bar(
    actions_df: pd.DataFrame,
    *,
    top_n: int = 20,
    title: str | None = None,
) -> go.Figure:
    """Horizontal bar: top-N actions sorted by action_score, colored by action_type.

    Input: fact_planner_actions_v2
    """
    if actions_df.empty or "action_score" not in actions_df.columns:
        return _theme(go.Figure(), title=title or "Actions — no data")

    df = actions_df.copy()
    df["action_score"] = pd.to_numeric(df["action_score"], errors="coerce").fillna(0.0)
    df = df.nlargest(top_n, "action_score")

    label_col = "project_id" if "project_id" in df.columns else df.columns[0]
    if "plant" in df.columns:
        df["_label"] = df[label_col].astype(str) + " · " + df["plant"].astype(str)
    else:
        df["_label"] = df[label_col].astype(str)

    colors = [_ACTION_COLORS.get(str(a), SLATE_SOFT) for a in df.get("action_type", ["wait"] * len(df))]

    fig = go.Figure(go.Bar(
        x=df["action_score"],
        y=df["_label"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}" for v in df["action_score"]],
        textposition="outside",
        textfont=dict(color=INK, size=10),
        hovertemplate=(
            "<b>%{y}</b><br>Score: %{x:.3f}"
            "<extra></extra>"
        ),
    ))
    fig.update_xaxes(range=[0, 1.05], title="Action score")
    fig.update_yaxes(autorange="reversed")
    return _theme(fig, height=max(350, 26 * len(df) + 60),
                  title=title or f"Top {top_n} actions by score")


def action_type_donut(actions_df: pd.DataFrame, *, title: str | None = None) -> go.Figure:
    """Donut: distribution of action_type counts.

    Input: fact_planner_actions_v2
    """
    if actions_df.empty or "action_type" not in actions_df.columns:
        return _theme(go.Figure(), title=title or "Action types — no data")

    counts = actions_df["action_type"].value_counts()
    colors = [_ACTION_COLORS.get(str(a), SLATE_SOFT) for a in counts.index]

    fig = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=BG, width=1)),
        textinfo="label+percent",
        textfont=dict(size=11, color=INK),
        hovertemplate="<b>%{label}</b><br>%{value} actions (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return _theme(fig, height=360, title=title or "Action type distribution")


def lead_time_breakdown_bar(
    df: pd.DataFrame,
    *,
    title: str | None = None,
) -> go.Figure:
    """Horizontal stacked bar: Sourcing / Production / Transit days per project.

    Input columns: project_name, sourcing_days, production_days, transit_days,
                   deadline_days (optional — days from today to requested delivery).
    """
    if df.empty:
        return _theme(go.Figure(), title=title or "Lead time breakdown — no data")

    _SOURCING_CLR    = "#E07B39"
    _PRODUCTION_CLR  = "#4A6FA5"
    _TRANSIT_CLR     = "#2A9D8F"

    projects = df["project_name"].tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Sourcing",
        y=projects,
        x=df["sourcing_days"].tolist(),
        orientation="h",
        marker_color=_SOURCING_CLR,
        hovertemplate="<b>%{y}</b><br>Sourcing: %{x:.0f} days<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Production",
        y=projects,
        x=df["production_days"].tolist(),
        orientation="h",
        marker_color=_PRODUCTION_CLR,
        hovertemplate="<b>%{y}</b><br>Production: %{x:.0f} days<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Transit",
        y=projects,
        x=df["transit_days"].tolist(),
        orientation="h",
        marker_color=_TRANSIT_CLR,
        hovertemplate="<b>%{y}</b><br>Transit: %{x:.0f} days<extra></extra>",
    ))

    # Deadline line — use the minimum deadline across projects for a single reference
    if "deadline_days" in df.columns:
        _valid_deadlines = df["deadline_days"].dropna()
        if not _valid_deadlines.empty:
            _dl = float(_valid_deadlines.min())
            if _dl > 0:
                fig.add_vline(
                    x=_dl,
                    line_dash="dash",
                    line_color="#E63946",
                    line_width=2,
                    annotation_text=f"Nearest deadline ({_dl:.0f}d)",
                    annotation_position="top right",
                    annotation_font=dict(color="#E63946", size=11),
                )
                # Mark at-risk projects
                _totals = df["sourcing_days"] + df["production_days"] + df["transit_days"]
                for _i, (_proj, _total) in enumerate(zip(projects, _totals)):
                    _proj_dl = df.iloc[_i].get("deadline_days")
                    if pd.notna(_proj_dl) and _total > float(_proj_dl):
                        fig.add_annotation(
                            x=_total,
                            y=_proj,
                            text="\u26a0\ufe0f At risk",
                            showarrow=False,
                            xanchor="left",
                            xshift=6,
                            font=dict(color="#E63946", size=11),
                        )

    fig.update_layout(
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5,
                    font=dict(size=11, color=INK)),
        xaxis_title="Days",
        margin=dict(l=10, r=10, t=40, b=60),
    )
    fig.update_yaxes(autorange="reversed")
    return _theme(fig, height=max(280, 52 * len(df) + 100), title=title or "Lead Time Breakdown")
