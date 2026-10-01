import pytest
from crewai import LLM

from src.agents import (
    create_llm,
    create_log_analyst_agent,
    create_solution_agent,
    create_triage_agent,
)
from src.config import Settings


TEST_LLM = LLM(model="openai/gpt-4o-mini", api_key="test-key")


def test_triage_agent_has_no_external_tools():
    agent = create_triage_agent(llm=TEST_LLM)

    assert agent.role == "Incident Triage Specialist"
    assert agent.tools == []
    assert "severity" in agent.goal


def test_log_analyst_agent_has_all_observability_tools():
    agent = create_log_analyst_agent(llm=TEST_LLM)

    assert agent.role == "Log Analyst and Troubleshooting Specialist"
    assert {tool.name for tool in agent.tools} == {
        "get_application_logs",
        "get_monitoring_metrics",
        "get_service_status",
        "search_incident_knowledge_base",
    }


def test_solution_agent_focuses_on_previous_results():
    agent = create_solution_agent(llm=TEST_LLM)

    assert agent.role == "Senior Application Support Engineer"
    assert "root cause" in agent.goal
    assert agent.tools == []


def test_create_llm_requires_api_key_from_settings():
    settings = Settings(llm_model="gemini/gemini-3.5-flash-lite", llm_api_key=None)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        create_llm(settings)


def test_create_llm_uses_litellm_gemini_route():
    settings = Settings(
        llm_provider="litellm",
        llm_model="gemini/gemini-3.5-flash-lite",
        llm_api_key="test-key",
    )

    llm = create_llm(settings)

    assert llm.model == "gemini/gemini-3.5-flash-lite"
