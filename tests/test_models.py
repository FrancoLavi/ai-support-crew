from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import (
    Incident,
    IncidentSeverity,
    LogAnalysis,
    Resolution,
    TriageResult,
)


def make_incident_data() -> dict:
    return {
        "id": "INC-100",
        "title": "API unavailable",
        "description": "The API is returning errors.",
        "service": "orders-api",
        "logs": ["ERROR upstream unavailable"],
        "created_at": datetime.now(timezone.utc),
    }


def test_incident_accepts_valid_data_and_parses_datetime():
    incident = Incident(**make_incident_data())

    assert incident.id == "INC-100"
    assert incident.created_at.tzinfo is not None


def test_incident_rejects_missing_required_field():
    data = make_incident_data()
    del data["service"]

    with pytest.raises(ValidationError):
        Incident(**data)


def test_incident_rejects_empty_logs():
    data = make_incident_data()
    data["logs"] = []

    with pytest.raises(ValidationError):
        Incident(**data)


def test_models_reject_unknown_fields():
    data = make_incident_data()
    data["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        Incident(**data)


def test_triage_result_uses_severity_enum():
    result = TriageResult(
        incident_id="INC-100",
        severity="HIGH",
        affected_area="API",
        summary="Requests are failing.",
        requires_immediate_action=True,
    )

    assert result.severity is IncidentSeverity.HIGH


def test_triage_result_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        TriageResult(
            incident_id="INC-100",
            severity="URGENT",
            affected_area="API",
            summary="Requests are failing.",
            requires_immediate_action=True,
        )


def test_log_analysis_requires_confidence_between_zero_and_one():
    valid = LogAnalysis(
        incident_id="INC-100",
        relevant_errors=["timeout"],
        probable_causes=["database overload"],
        confidence=0.85,
    )

    assert valid.confidence == 0.85

    with pytest.raises(ValidationError):
        LogAnalysis(
            incident_id="INC-100",
            relevant_errors=["timeout"],
            probable_causes=["database overload"],
            confidence=1.2,
        )


def test_resolution_requires_reason_when_escalating():
    with pytest.raises(ValidationError):
        Resolution(
            incident_id="INC-100",
            probable_root_cause="Database overload",
            recommended_steps=["Increase capacity"],
            should_escalate=True,
        )

    resolution = Resolution(
        incident_id="INC-100",
        probable_root_cause="Database overload",
        recommended_steps=["Increase capacity"],
        should_escalate=True,
        escalation_reason="The database is affecting multiple services.",
    )

    assert resolution.should_escalate is True
