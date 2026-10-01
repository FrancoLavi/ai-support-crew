"""Asynchronous service that simulates collecting incident context."""

import asyncio

from src.models import IncidentContext


async def get_application_logs(incident_id: str) -> list[str]:
    """Simulate retrieving application logs from a logging system."""

    await asyncio.sleep(0.10)
    return [f"{incident_id}: ERROR simulated application failure"]


async def get_monitoring_metrics(incident_id: str) -> dict[str, float]:
    """Simulate retrieving metrics from a monitoring system."""

    await asyncio.sleep(0.20)
    return {"error_rate": 0.25, "latency_ms": 850.0}


async def get_service_status(incident_id: str) -> str:
    """Simulate retrieving service status from a service registry."""

    await asyncio.sleep(0.15)
    return "degraded"


async def get_incident_context_sequential(incident_id: str) -> IncidentContext:
    """Collect incident data one query after another.

    This function is intentionally provided as a baseline for comparison.
    """

    logs = await get_application_logs(incident_id)
    metrics = await get_monitoring_metrics(incident_id)
    status = await get_service_status(incident_id)

    return IncidentContext(
        incident_id=incident_id,
        application_logs=logs,
        monitoring_metrics=metrics,
        service_status=status,
    )


async def gather_incident_context(incident_id: str) -> IncidentContext:
    """Collect all incident data concurrently."""

    logs, metrics, status = await asyncio.gather(
        get_application_logs(incident_id),
        get_monitoring_metrics(incident_id),
        get_service_status(incident_id),
    )

    return IncidentContext(
        incident_id=incident_id,
        application_logs=logs,
        monitoring_metrics=metrics,
        service_status=status,
    )
