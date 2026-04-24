import pandas as pd

from clarix.agent import run_agent
from clarix.data_loader import CanonicalData


def _sample_data() -> CanonicalData:
    pipeline = pd.DataFrame(
        [
            {
                "status": "Open",
                "material": "FG1",
                "material_description": "Finished Good 1",
                "cycle_time_min": 60.0,
                "project_name": "Project Alpha",
                "work_center_full": "P01_NW01_PRESS_1",
                "plant": "NW01",
                "year": 2026,
                "month": 1,
                "period_date": pd.Timestamp("2026-01-01"),
                "qty": 500.0,
                "expected_qty": 250.0,
                "probability_frac": 0.5,
            }
        ]
    )
    capacity = pd.DataFrame(
        [
            {
                "work_center": "P01_NW01_PRESS_1",
                "plant": "NW01",
                "year": 2026,
                "week": week,
                "week_start": pd.Timestamp.fromisocalendar(2026, week, 1),
                "available_hours": 50.0,
            }
            for week in [1, 2, 3, 4, 5]
        ]
    )
    bom = pd.DataFrame(
        [
            {
                "plant": "NW01",
                "header_material": "FG1",
                "component_material": "COMP1",
                "component_description": "Component 1",
                "qty_per": 2.0,
                "lead_time_weeks": 2.0,
            }
        ]
    )
    inventory = pd.DataFrame(
        [
            {
                "plant": "NW01",
                "material": "COMP1",
                "snapshot_date": pd.Timestamp("2025-12-15"),
                "atp_qty": 10.0,
                "safety_stock_qty": 5.0,
            }
        ]
    )
    return CanonicalData(
        fact_pipeline_monthly=pipeline,
        fact_wc_capacity_weekly=capacity,
        fact_finished_to_component=bom,
        fact_inventory_snapshot=inventory,
    )


def test_freeform_question_returns_general_summary(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answer, trace = run_agent("Cosa mi consigli di fare adesso?", _sample_data())

    assert "Clarix planner summary" in answer
    assert "Top bottleneck" in answer
    assert "GEMINI_API_KEY" in answer
    assert isinstance(trace, list)


def test_why_question_returns_constraint_explanation(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answer, _ = run_agent("Why is NW01 overloaded?", _sample_data())

    assert "Why P01_NW01_PRESS_1 is constrained" in answer
    assert "Top contributing projects" in answer


def test_gemini_error_falls_back_to_deterministic_answer(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def _boom(*args, **kwargs):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr("clarix.agent._run_gemini", _boom)

    answer, trace = run_agent("Explain the current risk picture", _sample_data())

    assert "Scenario summary" in answer
    assert any("Gemini error" in turn.content for turn in trace)


def test_general_knowledge_question_does_not_return_factory_summary(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answer, _ = run_agent("What is a volcano?", _sample_data())

    assert "outside the manufacturing planning scope" in answer
    assert "Scenario summary" not in answer
    assert "Top bottleneck" not in answer


def test_out_of_scope_question_with_existing_key_does_not_ask_to_set_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def _boom(*args, **kwargs):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr("clarix.agent._run_gemini", _boom)

    answer, _ = run_agent("What is a volcano?", _sample_data())

    assert "outside the manufacturing planning scope" in answer
    assert "set `ANTHROPIC_API_KEY`" not in answer
    assert "configured" in answer


def test_domain_definition_question_returns_definition_not_kpis(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answer, _ = run_agent("What is a bottleneck?", _sample_data())

    assert "limits flow" in answer
    assert "Top bottlenecks" not in answer


def test_app_help_question_returns_usage_guidance(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answer, _ = run_agent("How do I use this app?", _sample_data())

    assert "manufacturing planning app" in answer
    assert "Ask Clarix" in answer


def test_plan_change_question_returns_ui_guide(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answer, _ = run_agent("How can I change the plan in the application?", _sample_data())

    assert "What-if planner" in answer
    assert "Add to basket" in answer
    assert "Run feasibility check" in answer
