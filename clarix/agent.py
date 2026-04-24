"""
clarix.agent
============
LLM tool-use loop. Five tools backed by clarix.engine.
Falls back to a deterministic planner answer if no supported API key is set.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .data_loader import CanonicalData, load_canonical
from .engine import (
    SCENARIOS,
    build_utilization,
    detect_bottlenecks,
    explain_constraint,
    sourcing_recommendations,
)

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

TOOLS = [
    {
        "name": "get_capacity_forecast",
        "description": "Return a weekly capacity-vs-demand table. Use when the user asks about utilization, load, or capacity at a work center, plant, or globally.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "enum": list(SCENARIOS.keys()), "default": "expected"},
                "plant": {"type": "string", "description": "Optional plant code like NW01, NW12. Omit for all plants."},
                "min_utilization": {"type": "number", "description": "Filter rows where utilization >= this (e.g. 0.85).", "default": 0.0},
                "limit": {"type": "integer", "default": 25},
            },
        },
    },
    {
        "name": "run_scenario",
        "description": "Compare the four named scenarios (all_in, expected, high_confidence, monte_carlo) and return overall demand hours, peak utilization, and bottleneck count for each.",
        "input_schema": {
            "type": "object",
            "properties": {"plant": {"type": "string", "description": "Optional plant filter"}},
        },
    },
    {
        "name": "get_bottlenecks",
        "description": "Return ranked list of work centers exceeding 85% utilization in any week of the horizon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "enum": list(SCENARIOS.keys()), "default": "expected"},
                "plant": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "get_sourcing_recommendations",
        "description": "Return ranked component purchase recommendations (order-by date and shortfall qty) based on BOM explosion vs ATP inventory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "enum": list(SCENARIOS.keys()), "default": "expected"},
                "plant": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "explain_constraint",
        "description": "Explain why a specific work center is overloaded - returns top contributing projects and weekly numbers. Use when the user asks 'why is X overloaded' or 'what is driving the load on Y'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "work_center": {"type": "string", "description": "Full work center code, e.g. P01_NW12_PRESS_1"},
                "scenario": {"type": "string", "enum": list(SCENARIOS.keys()), "default": "expected"},
                "year": {"type": "integer"},
                "week": {"type": "integer"},
            },
            "required": ["work_center"],
        },
    },
]

SYSTEM_PROMPT = """You are CLARIX, an industrial planning copilot for Danfoss Climate Solutions.
You help production planners and supply-chain leads reason about capacity, bottlenecks, and component sourcing using the Probabilistic Capacity-and-Sourcing Engine.

Rules:
- ALWAYS call a tool to fetch data before answering quantitatively. Never invent numbers.
- Default scenario is 'expected' (qty x probability). Mention which scenario you used.
- Bottleneck thresholds: utilization >= 85% is a warning, >= 100% is critical.
- Be concise and end with a single concrete recommendation.
- Format numbers with thousand separators and units (hours, pcs, EUR, weeks).

When answering scenario comparison questions:
1. Always compare ALL scenarios side-by-side, highlighting their status (OK/WARNING/CRITICAL).
2. Calculate and explain deltas between scenarios to show impact of uncertainty.
3. Provide a strategic recommendation tied to the expected scenario's health.
4. If expected scenario is overloaded (>100%), recommend immediate actions like bottleneck review & component sourcing.
5. If expected scenario is near capacity (85-100%), recommend contingency planning.
6. If expected scenario is healthy (<85%), recommend protecting timelines and preparing for pessimistic case.
"""


# -----------------------------------------------------------------------------
# Tool dispatch
# -----------------------------------------------------------------------------
def _df_to_records(df: pd.DataFrame, limit: int = 25) -> list[dict]:
    if df is None or df.empty:
        return []
    out = df.head(limit).copy()
    for c in out.select_dtypes(include=["datetime64[ns]"]).columns:
        out[c] = out[c].dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


def call_tool(name: str, args: dict, data: CanonicalData) -> dict:
    args = args or {}
    if name == "get_capacity_forecast":
        df = build_utilization(data, args.get("scenario", "expected"), plant=args.get("plant"))
        if df.empty:
            return {"rows": [], "note": "no data"}
        df = df[df["utilization"] >= float(args.get("min_utilization", 0.0))]
        df = df.sort_values("utilization", ascending=False)
        cols = ["work_center", "plant", "year", "week", "available_hours", "demand_hours", "utilization", "status"]
        return {"rows": _df_to_records(df[cols].round(3), int(args.get("limit", 25)))}
    if name == "run_scenario":
        out = []
        for sc in SCENARIOS:
            u = build_utilization(data, sc, plant=args.get("plant"))
            if u.empty:
                out.append({"scenario": sc, "label": SCENARIOS[sc]["label"], "peak_util": 0, "weeks_critical": 0, "total_demand_hours": 0})
                continue
            out.append({
                "scenario": sc,
                "label": SCENARIOS[sc]["label"],
                "peak_util": round(float(u["utilization"].max()), 3),
                "weeks_critical": int((u["utilization"] >= 1.0).sum()),
                "total_demand_hours": round(float(u["demand_hours"].sum()), 1),
            })
        return {"rows": out}
    if name == "get_bottlenecks":
        u = build_utilization(data, args.get("scenario", "expected"), plant=args.get("plant"))
        b = detect_bottlenecks(u)
        return {"rows": _df_to_records(b.round(3), int(args.get("limit", 10)))}
    if name == "get_sourcing_recommendations":
        s = sourcing_recommendations(data, args.get("scenario", "expected"), plant=args.get("plant"),
                                     top_n=int(args.get("limit", 10)))
        if s is None or s.empty:
            return {"rows": [], "note": "No component shortfalls detected for this scenario."}
        cols = ["plant", "component_material", "component_description", "period_date", "order_by",
                "lead_time_weeks", "component_demand_qty", "atp_today", "safety_stock", "shortfall"]
        cols = [c for c in cols if c in s.columns]
        return {"rows": _df_to_records(s[cols].round(2), int(args.get("limit", 10)))}
    if name == "explain_constraint":
        return explain_constraint(
            data,
            args["work_center"],
            scenario=args.get("scenario", "expected"),
            year=args.get("year"),
            week=args.get("week"),
        )
    return {"error": f"unknown tool {name}"}


# -----------------------------------------------------------------------------
# Agent loop
# -----------------------------------------------------------------------------
@dataclass
class AgentTurn:
    role: str             # 'assistant' | 'tool'
    content: str
    tool_name: str | None = None
    tool_args: dict | None = None


def _active_provider() -> str:
    """Return 'anthropic', 'gemini', or 'none' based on env vars."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return "none"


def run_agent(user_msg: str, data: CanonicalData, *, history: list | None = None,
              model: str = DEFAULT_MODEL, max_iter: int = 6) -> tuple[str, list[AgentTurn]]:
    """Run the tool-use loop. Returns (final_text, trace).

    Picks the provider automatically:
      - ANTHROPIC_API_KEY  -> Claude tool-use
      - GEMINI_API_KEY     -> Google Gemini function calling
      - none               -> deterministic fallback
    """
    trace: list[AgentTurn] = []
    try:
        provider = _active_provider()

        if provider == "anthropic":
            try:
                return _run_anthropic(user_msg, data, history=history, model=model,
                                      max_iter=max_iter, trace=trace)
            except Exception as e:
                trace.append(AgentTurn("assistant", f"Anthropic error: {e}; falling back."))
                return _fallback_planner(user_msg, data, trace)

        if provider == "gemini":
            try:
                return _run_gemini(user_msg, data, history=history,
                                   max_iter=max_iter, trace=trace)
            except Exception as e:
                trace.append(AgentTurn("assistant", f"Gemini error: {e}; falling back."))
                return _fallback_planner(user_msg, data, trace)

        return _fallback_planner(user_msg, data, trace)
    except Exception as e:
        trace.append(AgentTurn("assistant", f"Planner error: {e}; returning safe fallback."))
        return _safe_fallback_message(), trace


# -----------------------------------------------------------------------------
# Anthropic backend
# -----------------------------------------------------------------------------
def _run_anthropic(user_msg: str, data: CanonicalData, *, history, model,
                   max_iter, trace) -> tuple[str, list[AgentTurn]]:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = list(history or []) + [{"role": "user", "content": user_msg}]

    for _ in range(max_iter):
        resp = client.messages.create(
            model=model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        text_blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]

        if resp.stop_reason == "tool_use" and tool_uses:
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for tu in tool_uses:
                trace.append(AgentTurn("assistant", "calling tool",
                                       tool_name=tu.name, tool_args=tu.input))
                result = call_tool(tu.name, tu.input, data)
                trace.append(AgentTurn("tool", json.dumps(result, default=str)[:600],
                                       tool_name=tu.name))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result, default=str),
                })
            messages.append({"role": "user", "content": tool_results})
            continue

        final = "\n".join(text_blocks).strip() or "(no answer)"
        trace.append(AgentTurn("assistant", final))
        return final, trace

    return "(agent stopped: max iterations reached)", trace


# -----------------------------------------------------------------------------
# Gemini backend (Google Generative AI SDK)
# -----------------------------------------------------------------------------
def _gemini_tools_spec():
    """Convert our TOOLS list to Gemini function declarations."""
    import google.generativeai as genai
    decls = []
    for t in TOOLS:
        # Gemini accepts a JSON-Schema-like spec but rejects unknown keys.
        props = {}
        for pname, pspec in t["input_schema"].get("properties", {}).items():
            p = {"type": pspec.get("type", "string").upper()}
            if "description" in pspec:
                p["description"] = pspec["description"]
            if "enum" in pspec:
                p["enum"] = pspec["enum"]
            props[pname] = p
        decls.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": {
                "type": "OBJECT",
                "properties": props,
                "required": t["input_schema"].get("required", []),
            },
        })
    return [genai.protos.Tool(function_declarations=decls)]


def _run_gemini(user_msg: str, data: CanonicalData, *, history, max_iter,
                trace) -> tuple[str, list[AgentTurn]]:
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        system_instruction=SYSTEM_PROMPT,
        tools=_gemini_tools_spec(),
    )
    chat = model.start_chat(history=[])  # ignore prior history for simplicity
    msg: Any = user_msg

    for _ in range(max_iter):
        resp = chat.send_message(msg)
        # Pull function-call parts (if any)
        parts = []
        try:
            parts = resp.candidates[0].content.parts
        except Exception:
            parts = []

        fcalls = [p.function_call for p in parts if getattr(p, "function_call", None) and p.function_call.name]
        if fcalls:
            tool_responses = []
            for fc in fcalls:
                args = {k: v for k, v in (fc.args or {}).items()}
                trace.append(AgentTurn("assistant", "calling tool",
                                       tool_name=fc.name, tool_args=args))
                result = call_tool(fc.name, args, data)
                trace.append(AgentTurn("tool", json.dumps(result, default=str)[:600],
                                       tool_name=fc.name))
                tool_responses.append(genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fc.name,
                        response={"result": json.dumps(result, default=str)},
                    )
                ))
            msg = tool_responses
            continue

        # Otherwise final text
        try:
            final = resp.text.strip()
        except Exception:
            final = "(no answer)"
        trace.append(AgentTurn("assistant", final))
        return final, trace

    return "(agent stopped: max iterations reached)", trace


# -----------------------------------------------------------------------------
# Fallback when no API key is available - still useful for demo
# -----------------------------------------------------------------------------
def _safe_fallback_message() -> str:
    return (
        "Clarix hit an internal error while preparing the answer.\n\n"
        "You can still use the app without Anthropic if `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set. "
        "If no LLM key is configured, planner mode should still answer with a deterministic summary."
    )


def _extract_plant(user_msg: str) -> str | None:
    match = re.search(r"\b(NW\d{2})\b", user_msg.upper())
    return match.group(1) if match else None


def _has_llm_key() -> bool:
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )


def _provider_tip() -> str:
    if _has_llm_key():
        return (
            "full conversational mode is already configured, but the LLM provider is not available right now"
        )
    return "set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` for full conversational answers"


def _looks_like_general_knowledge_question(user_msg: str) -> bool:
    msg = user_msg.lower().strip()
    domain_markers = [
        "plant", "work center", "workcentre", "factory", "capacity", "utilization",
        "bottleneck", "constraint", "scenario", "risk", "load", "inventory",
        "component", "supplier", "sourcing", "procurement", "material", "project",
        "delivery", "schedule", "overload", "shortfall", "order", "bom",
    ]
    if any(marker in msg for marker in domain_markers):
        return False
    patterns = [
        r"^(what is|what's|who is|where is|when is|tell me about|define)\b",
        r"^(cos[ 'eè]+|che cos[ 'eè]+)\b",
    ]
    return any(re.search(pattern, msg) for pattern in patterns)


def _format_out_of_scope_answer(user_msg: str) -> str:
    recommendation = (
        "ask a planning question, or retry when the conversational provider is available again"
        if _has_llm_key()
        else f"ask a planning question, or enable full conversational mode with {_provider_tip()}"
    )
    availability_note = (
        "Full conversational mode is already configured, but Clarix is currently answering through the deterministic planner fallback.\n\n"
        if _has_llm_key()
        else ""
    )
    return (
        f"Clarix is in planner mode and your question looks outside the manufacturing planning scope: "
        f"\"{user_msg.strip()}\".\n\n"
        f"{availability_note}"
        "In planner mode I can answer deterministically about capacity, bottlenecks, sourcing, scenarios, "
        "work centers, plants, and supply risk. I should not answer a general-knowledge question by showing "
        "manufacturing KPIs that are unrelated to what you asked.\n\n"
        f"Recommendation: {recommendation}."
    )


def _is_definition_question(user_msg: str) -> bool:
    msg = user_msg.lower().strip()
    definition_prefixes = [
        "what is", "what's", "define", "meaning of",
        "cos'è", "cos e", "che cos'è", "che cos e",
    ]
    domain_terms = [
        "bottleneck", "work center", "workcentre", "capacity", "utilization",
        "scenario", "sourcing", "shortfall", "atp", "inventory", "lead time",
        "risk", "planner action", "plant",
    ]
    return any(msg.startswith(prefix) for prefix in definition_prefixes) and any(
        term in msg for term in domain_terms
    )


def _is_app_help_question(user_msg: str) -> bool:
    msg = user_msg.lower().strip()
    help_markers = [
        "how do i use", "how to use", "how can i use", "how does this app work",
        "how does the app work", "what can i ask", "how do i ask", "help",
        "what does this app do", "come si usa", "come uso", "cosa posso chiedere",
        "how can i change the plan", "how do i change the plan", "change the plan",
        "modify the plan", "update the plan", "edit the plan", "change plan",
    ]
    app_markers = ["app", "clarix", "ask clarix", "dashboard", "planner mode"]
    return any(marker in msg for marker in help_markers) and (
        any(marker in msg for marker in app_markers) or "help" == msg
    )


def _format_definition_answer(user_msg: str) -> str:
    msg = user_msg.lower()
    definitions = {
        "bottleneck": (
            "A bottleneck is the work center or resource that limits flow because demand is higher than available capacity. "
            "In Clarix, a work center becomes a bottleneck when weekly utilization gets too high, especially above the 85% warning level or 100% critical level."
        ),
        "work center": (
            "A work center is a specific production resource where manufacturing work happens, for example a press, lathe, extrusion line, or grinding cell."
        ),
        "capacity": (
            "Capacity is the amount of production time available at a work center, usually expressed in hours per week."
        ),
        "utilization": (
            "Utilization is demand hours divided by available hours for a work center in a given week. It shows how loaded the resource is."
        ),
        "scenario": (
            "A scenario is an alternate planning view of demand. Clarix compares scenarios like all-in, expected value, high-confidence, and Monte Carlo light to show how uncertainty changes risk."
        ),
        "sourcing": (
            "Sourcing is the material supply decision layer: what components are needed, when they must be ordered, and where shortages could block production."
        ),
        "shortfall": (
            "A shortfall is the gap between required component demand and the inventory available after respecting safety stock."
        ),
        "atp": (
            "ATP means available-to-promise: the inventory that is effectively available to support future demand."
        ),
        "lead time": (
            "Lead time is the time needed to obtain or produce a material before it can be used, usually measured in weeks."
        ),
        "planner action": (
            "A planner action is an explainable recommendation such as buy, wait, reroute, upshift, reschedule, expedite, or escalate."
        ),
        "risk": (
            "Risk is the combined operational exposure across capacity, sourcing, logistics, disruption, lead time, and data quality drivers."
        ),
        "inventory": (
            "Inventory is the stock currently available or reserved for materials and components, used to assess whether future demand can be covered."
        ),
        "plant": (
            "A plant is a manufacturing site, identified in this app by codes like NW01 or NW12."
        ),
    }
    for term, explanation in definitions.items():
        if term in msg:
            return (
                f"{explanation}\n\n"
                "Recommendation: ask a follow-up like `show me the current bottlenecks` or "
                "`compare all scenarios` if you want to apply that concept to the current data."
            )
    return (
        "That looks like a planning-term definition request, but I could not map the term to one of the built-in Clarix concepts.\n\n"
        "Try asking about: bottleneck, work center, capacity, utilization, scenario, sourcing, shortfall, ATP, or planner action."
    )


def _format_app_help_answer() -> str:
    return (
        "Clarix is a manufacturing planning app. The main ways to use it are:\n\n"
        "- Executive Dashboard: overall risk, bottlenecks, sourcing pressure, and scenario comparison.\n"
        "- Ask Clarix: ask natural-language questions about capacity, bottlenecks, sourcing, scenarios, plants, or work centers.\n"
        "- Logistics & Disruptions: inspect shipping, landed-cost, and disruption impacts.\n"
        "- Maintenance and sourcing pages: drill into capacity loss, shortages, and planner actions.\n\n"
        "Useful questions you can ask here:\n"
        "- `What are the top bottlenecks under the expected scenario?`\n"
        "- `Compare all four scenarios.`\n"
        "- `Why is the worst work center overloaded?`\n"
        "- `Which components do we need to order in the next 8 weeks?`\n"
        "- `What does bottleneck mean?`\n\n"
        "Recommendation: start with a scenario comparison, then drill into the worst bottleneck or top sourcing shortfall."
    )


def _is_plan_change_question(user_msg: str) -> bool:
    msg = user_msg.lower().strip()
    plan_markers = [
        "change the plan", "modify the plan", "update the plan", "edit the plan",
        "how can i change the plan", "how do i change the plan",
        "how can i change plan", "how do i change plan",
    ]
    return any(marker in msg for marker in plan_markers)


def _format_plan_change_answer() -> str:
    return (
        "You cannot directly overwrite the baseline production plan from Ask Clarix, but you can test planning changes in the UI.\n\n"
        "How to change the plan in the app:\n"
        "- Use the sidebar filters to change scenario and plant scope.\n"
        "- Open the `What-if planner` page.\n"
        "- Add one or more candidate projects in the `Add a candidate project` section.\n"
        "- Set plant, material, quarter, quantity, win probability, and spread.\n"
        "- Click `Add to basket`, then `Run feasibility check`.\n"
        "- Review the verdicts: feasible, at risk, or infeasible, plus the worst work center and overload added.\n"
        "- Use `Clear basket` to reset the simulated changes.\n\n"
        "What this means: the app supports simulated plan changes and impact analysis, not direct transactional plan editing.\n\n"
        "Recommendation: use the What-if planner to test a change first, then apply the chosen action in your operational planning system."
    )


def _format_scenario_summary(data: CanonicalData, plant: str | None = None) -> str:
    rows = call_tool("run_scenario", {"plant": plant} if plant else {}, data).get("rows", [])
    if not rows:
        return "Scenario summary is not available from the current dataset."

    expected = next((r for r in rows if r["scenario"] == "expected"), rows[0])
    lines = ["Scenario summary"]
    if plant:
        lines[0] += f" for plant {plant}"
    lines.append("")
    for r in rows:
        status = "CRITICAL" if r["peak_util"] >= 1.0 else "WARNING" if r["peak_util"] >= 0.85 else "OK"
        lines.append(
            f"- {r['label']}: peak {r['peak_util']:.0%}, critical weeks {int(r['weeks_critical'])}, "
            f"demand {r['total_demand_hours']:,.0f}h [{status}]"
        )
    lines.append("")
    if expected["peak_util"] >= 1.0:
        lines.append("Recommendation: review the top bottleneck and pre-empt sourcing gaps immediately.")
    elif expected["peak_util"] >= 0.85:
        lines.append("Recommendation: protect high-priority demand and prepare contingency capacity.")
    else:
        lines.append("Recommendation: capacity is healthy; use the buffer to protect delivery risk.")
    return "\n".join(lines)


def _format_bottleneck_summary(data: CanonicalData, plant: str | None = None) -> str:
    util = build_utilization(data, "expected", plant=plant)
    b = detect_bottlenecks(util)
    if b.empty:
        scope = f" at plant {plant}" if plant else ""
        return f"No work centers exceed 85% utilization under the expected scenario{scope}."

    top = b.head(5)
    worst = top.iloc[0]
    lines = ["Top bottlenecks (expected scenario)"]
    if plant:
        lines[0] += f" for plant {plant}"
    lines.append("")
    for _, r in top.iterrows():
        lines.append(
            f"- {r['work_center']} ({r['plant']}): peak {r['peak_util']:.0%}, "
            f"critical weeks {int(r['weeks_crit'])}, overload {r['total_overload_hours']:.0f}h"
        )
    lines.append("")
    lines.append(f"Recommendation: investigate {worst['work_center']} first because it has the highest peak load.")
    return "\n".join(lines)


def _format_sourcing_summary(data: CanonicalData, plant: str | None = None) -> str:
    s = sourcing_recommendations(data, "expected", top_n=5, plant=plant)
    if s is None or s.empty:
        scope = f" at plant {plant}" if plant else ""
        return f"No component shortfalls were detected under the expected scenario{scope}."

    lines = ["Top sourcing recommendations (expected scenario)"]
    if plant:
        lines[0] += f" for plant {plant}"
    lines.append("")
    for _, r in s.iterrows():
        lines.append(
            f"- {r['component_material']} {r['component_description']}: need {r['component_demand_qty']:.0f}, "
            f"ATP {r['atp_today']:.0f}, shortfall {r['shortfall']:.0f}, "
            f"order by {pd.Timestamp(r['order_by']).date()}"
        )
    lines.append("")
    lines.append("Recommendation: place the earliest-due shortage first to prevent avoidable delays.")
    return "\n".join(lines)


def _format_constraint_explanation(data: CanonicalData, plant: str | None = None) -> str:
    util = build_utilization(data, "expected", plant=plant)
    b = detect_bottlenecks(util)
    if b.empty:
        return _format_bottleneck_summary(data, plant=plant)

    wc = str(b.iloc[0]["work_center"])
    explanation = explain_constraint(data, wc, scenario="expected")
    if "error" in explanation:
        return _format_bottleneck_summary(data, plant=plant)

    lines = [
        f"Why {wc} is constrained (expected scenario)",
        "",
        f"- Plant: {explanation['plant']}",
        f"- Peak week: {explanation['year']}-W{int(explanation['week']):02d}",
        f"- Demand vs available: {explanation['demand_hours']:.0f}h vs {explanation['available_hours']:.0f}h",
        f"- Utilization: {explanation['utilization']:.0%} [{explanation['status']}]",
        "",
        "Top contributing projects:",
    ]
    projects = explanation.get("top_projects") or []
    if not projects:
        lines.append("- No project-level contributors were available.")
    else:
        for proj in projects[:5]:
            lines.append(
                f"- {proj.get('project_name', 'Unknown project')} / {proj.get('material', 'n/a')}: "
                f"{float(proj.get('hours', 0.0)):.0f}h"
            )
    lines.append("")
    lines.append("Recommendation: rebalance the highest-hour contributors before adding new demand to this work center.")
    return "\n".join(lines)


def _format_general_summary(user_msg: str, data: CanonicalData, plant: str | None = None) -> str:
    scenario_summary = _format_scenario_summary(data, plant=plant)
    bottlenecks = detect_bottlenecks(build_utilization(data, "expected", plant=plant))
    sourcing = sourcing_recommendations(data, "expected", top_n=1, plant=plant)

    lines = [
        "Clarix planner summary",
        "",
        f"Question received: {user_msg.strip()}",
        "",
        scenario_summary,
    ]
    if not bottlenecks.empty:
        worst = bottlenecks.iloc[0]
        lines.extend([
            "",
            (
                f"Top bottleneck: {worst['work_center']} at {worst['plant']} "
                f"with peak utilization {worst['peak_util']:.0%}."
            ),
        ])
    if sourcing is not None and not sourcing.empty:
        top = sourcing.iloc[0]
        lines.extend([
            "",
            (
                f"Top sourcing risk: {top['component_material']} shortfall {top['shortfall']:.0f}, "
                f"order by {pd.Timestamp(top['order_by']).date()}."
            ),
        ])
    lines.extend([
        "",
        "Recommendation: ask a follow-up about bottlenecks, sourcing, scenarios, or a specific work center for a deeper answer.",
        _provider_tip()[0].upper() + _provider_tip()[1:] + ".",
    ])
    return "\n".join(lines)


def _fallback_planner(user_msg: str, data: CanonicalData, trace: list[AgentTurn]) -> tuple[str, list[AgentTurn]]:
    msg = user_msg.lower()
    plant = _extract_plant(user_msg)
    if _looks_like_general_knowledge_question(user_msg):
        return _format_out_of_scope_answer(user_msg), trace
    if _is_plan_change_question(user_msg):
        return _format_plan_change_answer(), trace
    if _is_app_help_question(user_msg):
        return _format_app_help_answer(), trace
    if _is_definition_question(user_msg):
        return _format_definition_answer(user_msg), trace
    if any(k in msg for k in ["why", "driver", "driving", "root cause", "what is causing"]):
        return _format_constraint_explanation(data, plant=plant), trace
    if any(k in msg for k in ["bottleneck", "overload", "constraint"]):
        return _format_bottleneck_summary(data, plant=plant), trace
    if any(k in msg for k in ["sourcing", "buy", "order", "component", "inventory", "supplier", "procurement"]):
        return _format_sourcing_summary(data, plant=plant), trace
    if any(k in msg for k in ["scenario", "compare", "risk", "capacity", "utilization", "load"]):
        return _format_scenario_summary(data, plant=plant), trace
    return _format_general_summary(user_msg, data, plant=plant), trace
