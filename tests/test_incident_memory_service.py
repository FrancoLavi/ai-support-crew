from src.models import Incident
from src.services.incident_memory_service import (
    HISTORICAL_INCIDENTS_PATH,
    IncidentMemoryService,
)


def make_payment_incident() -> Incident:
    return Incident(
        id="INC-MEMORY-001",
        title="Payment API returns HTTP 500 after deployment",
        description="The payment endpoint returns HTTP 500 immediately after release.",
        service="payments-api",
        logs=["ERROR payment database initialization failed"],
        created_at="2026-10-01T12:00:00Z",
    )


def test_memory_seeds_and_recovers_similar_historical_incident(tmp_path):
    service = IncidentMemoryService(
        storage_path=tmp_path / "memory",
        history_path=HISTORICAL_INCIDENTS_PATH,
    )

    matches = service.find_similar(make_payment_incident(), limit=1)

    assert matches
    assert "DATABASE_URL was missing" in matches[0].record.content
    assert matches[0].record.metadata["incident_id"] == "HIST-001"


def test_memory_format_has_predictable_agent_context(tmp_path):
    service = IncidentMemoryService(
        storage_path=tmp_path / "memory",
        history_path=HISTORICAL_INCIDENTS_PATH,
    )

    context = service.format_matches(service.find_similar(make_payment_incident(), 1))

    assert context.startswith("Historical match 1")
    assert "Probable root cause:" in context
    assert "Recommended steps:" in context
