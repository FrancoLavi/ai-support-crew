"""CrewAI tools for collecting and looking up incident context."""

import json
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, field_validator

from src.services.incident_data_service import (
    get_application_logs,
    get_monitoring_metrics,
    get_service_status,
)


class IncidentIdInput(BaseModel):
    """Input shared by tools that query data for an incident."""

    incident_id: str = Field(min_length=1, description="Unique incident identifier, e.g. INC-001")

    @field_validator("incident_id")
    @classmethod
    def validate_incident_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("incident_id must not be empty")
        return value.strip()


class ServiceStatusInput(BaseModel):
    """Input for the service status tool."""

    service_name: str = Field(min_length=1, description="Name of the service to inspect")

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("service_name must not be empty")
        return value.strip()


class KnowledgeBaseInput(BaseModel):
    """Input for a keyword search in the local incident knowledge base."""

    query: str = Field(min_length=2, description="Error phrase or symptom to search for")

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be empty")
        return value.strip()


def load_knowledge_base() -> list[dict[str, Any]]:
    """Load the small, local knowledge base from JSON."""

    path = Path(__file__).parents[2] / "data" / "knowledge_base.json"
    with path.open(encoding="utf-8") as knowledge_base_file:
        return json.load(knowledge_base_file)


def search_knowledge_base(query: str) -> list[dict[str, Any]]:
    """Return articles whose topic or keywords match the query."""

    normalized_query = query.strip().lower()
    matches = []
    for article in load_knowledge_base():
        searchable_text = [article["topic"], *article["keywords"]]
        if any(normalized_query in value.lower() for value in searchable_text):
            matches.append(article)
    return matches


class GetApplicationLogsTool(BaseTool):
    name: str = "get_application_logs"
    description: str = (
        "Retrieve simulated application logs for an incident. "
        "Use this when you need concrete error messages or stack traces."
    )
    args_schema: type[BaseModel] = IncidentIdInput

    async def _run(self, incident_id: str) -> dict[str, Any]:
        logs = await get_application_logs(incident_id)
        return {"incident_id": incident_id, "logs": logs}


class GetMonitoringMetricsTool(BaseTool):
    name: str = "get_monitoring_metrics"
    description: str = (
        "Retrieve simulated monitoring metrics for an incident. "
        "Use this to inspect error rate and latency before forming a diagnosis."
    )
    args_schema: type[BaseModel] = IncidentIdInput

    async def _run(self, incident_id: str) -> dict[str, Any]:
        metrics = await get_monitoring_metrics(incident_id)
        return {"incident_id": incident_id, "metrics": metrics}


class GetServiceStatusTool(BaseTool):
    name: str = "get_service_status"
    description: str = (
        "Retrieve the simulated availability status of a service. "
        "Use this when determining whether a service is healthy, degraded, or unavailable."
    )
    args_schema: type[BaseModel] = ServiceStatusInput

    async def _run(self, service_name: str) -> dict[str, str]:
        status = await get_service_status(service_name)
        return {"service_name": service_name, "status": status}


class SearchKnowledgeBaseTool(BaseTool):
    name: str = "search_incident_knowledge_base"
    description: str = (
        "Search the local incident knowledge base for known symptoms such as "
        "HTTP 500, database timeout, connection refused, authentication errors, "
        "or high latency. Use it for basic troubleshooting guidance."
    )
    args_schema: type[BaseModel] = KnowledgeBaseInput

    def _run(self, query: str) -> dict[str, Any]:
        return {"query": query, "matches": search_knowledge_base(query)}


application_logs_tool = GetApplicationLogsTool()
monitoring_metrics_tool = GetMonitoringMetricsTool()
service_status_tool = GetServiceStatusTool()
knowledge_base_tool = SearchKnowledgeBaseTool()

__all__ = [
    "GetApplicationLogsTool",
    "GetMonitoringMetricsTool",
    "GetServiceStatusTool",
    "SearchKnowledgeBaseTool",
    "IncidentIdInput",
    "ServiceStatusInput",
    "KnowledgeBaseInput",
    "application_logs_tool",
    "monitoring_metrics_tool",
    "service_status_tool",
    "knowledge_base_tool",
    "load_knowledge_base",
    "search_knowledge_base",
]
