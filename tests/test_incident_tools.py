import pytest
from pydantic import ValidationError

from src.tools.incident_tools import (
    IncidentIdInput,
    KnowledgeBaseInput,
    SearchKnowledgeBaseTool,
    application_logs_tool,
    monitoring_metrics_tool,
    service_status_tool,
    search_knowledge_base,
)


@pytest.mark.asyncio
async def test_application_logs_tool_returns_predictable_output():
    result = await application_logs_tool._run("INC-001")

    assert result["incident_id"] == "INC-001"
    assert isinstance(result["logs"], list)


@pytest.mark.asyncio
async def test_monitoring_and_status_tools_return_predictable_output():
    metrics = await monitoring_metrics_tool._run("INC-001")
    status = await service_status_tool._run("payments-api")

    assert set(metrics) == {"incident_id", "metrics"}
    assert set(status) == {"service_name", "status"}
    assert isinstance(metrics["metrics"], dict)
    assert status["status"] == "degraded"


def test_knowledge_base_search_finds_known_topic():
    matches = search_knowledge_base("database timeout")

    assert len(matches) == 1
    assert matches[0]["topic"] == "database timeout"
    assert matches[0]["recommended_actions"]


def test_knowledge_base_tool_returns_empty_matches_for_unknown_query():
    result = SearchKnowledgeBaseTool().run(query="unknown symptom")

    assert result == {"query": "unknown symptom", "matches": []}


def test_inputs_reject_empty_values():
    with pytest.raises(ValidationError):
        IncidentIdInput(incident_id=" ")

    with pytest.raises(ValidationError):
        KnowledgeBaseInput(query=" ")


def test_crewai_tool_run_validates_its_input_schema():
    with pytest.raises(ValueError):
        application_logs_tool.run(incident_id=" ")
