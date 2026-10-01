import asyncio

import pytest
from pydantic import ValidationError

from src.models import IncidentContext
from src.services import (
    gather_incident_context,
    get_incident_context_sequential,
)


@pytest.mark.asyncio
async def test_gather_incident_context_returns_valid_pydantic_model():
    context = await gather_incident_context("INC-001")

    assert isinstance(context, IncidentContext)
    assert context.incident_id == "INC-001"
    assert context.application_logs
    assert context.monitoring_metrics["error_rate"] == 0.25
    assert context.service_status == "degraded"


@pytest.mark.asyncio
async def test_gather_is_faster_than_sequential_collection():
    sequential_start = asyncio.get_running_loop().time()
    await get_incident_context_sequential("INC-002")
    sequential_duration = asyncio.get_running_loop().time() - sequential_start

    concurrent_start = asyncio.get_running_loop().time()
    await gather_incident_context("INC-002")
    concurrent_duration = asyncio.get_running_loop().time() - concurrent_start

    assert concurrent_duration < sequential_duration


def test_incident_context_rejects_empty_application_logs():
    with pytest.raises(ValidationError):
        IncidentContext(
            incident_id="INC-003",
            application_logs=[],
            monitoring_metrics={"error_rate": 0.0},
            service_status="healthy",
        )
