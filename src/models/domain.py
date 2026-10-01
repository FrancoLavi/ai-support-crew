"""Domain models exchanged by the incident analysis workflow."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DomainModel(BaseModel):
    """Shared Pydantic configuration for domain objects."""

    model_config = ConfigDict(extra="forbid")


class IncidentSeverity(StrEnum):
    """Possible urgency levels for an incident."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Incident(DomainModel):
    """Technical support incident received by the system."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    service: str = Field(min_length=1)
    logs: list[str] = Field(min_length=1)
    created_at: datetime

    @field_validator("id", "title", "description", "service", mode="before")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """Reject empty or whitespace-only text values."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("must be a non-empty text value")
        return value.strip()

    @field_validator("logs")
    @classmethod
    def validate_logs(cls, logs: list[str]) -> list[str]:
        """Ensure every log entry contains useful text."""

        if any(not isinstance(log, str) or not log.strip() for log in logs):
            raise ValueError("logs must contain non-empty text entries")
        return [log.strip() for log in logs]


class TriageResult(DomainModel):
    """Structured output produced by the triage stage."""

    incident_id: str = Field(min_length=1)
    severity: IncidentSeverity
    affected_area: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    requires_immediate_action: bool


class LogAnalysis(DomainModel):
    """Structured output produced by the log analysis stage."""

    incident_id: str = Field(min_length=1)
    relevant_errors: list[str] = Field(min_length=1)
    probable_causes: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class Resolution(DomainModel):
    """Proposed resolution produced after triage and log analysis."""

    incident_id: str = Field(min_length=1)
    probable_root_cause: str = Field(min_length=1)
    recommended_steps: list[str] = Field(min_length=1)
    should_escalate: bool
    escalation_reason: str | None = None

    @model_validator(mode="after")
    def validate_escalation_reason(self) -> "Resolution":
        """Require a reason when the proposed solution must be escalated."""

        if self.should_escalate and (
            self.escalation_reason is None or not self.escalation_reason.strip()
        ):
            raise ValueError(
                "escalation_reason is required when should_escalate is true"
            )
        return self


class HistoricalIncident(DomainModel):
    """Resolved incident stored as reusable support knowledge."""

    incident_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    service: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    probable_root_cause: str = Field(min_length=1)
    recommended_steps: list[str] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class IncidentContext(DomainModel):
    """External information collected before analyzing an incident."""

    incident_id: str = Field(min_length=1)
    application_logs: list[str] = Field(min_length=1)
    monitoring_metrics: dict[str, float]
    service_status: str = Field(min_length=1)

    @field_validator("application_logs")
    @classmethod
    def validate_application_logs(cls, logs: list[str]) -> list[str]:
        if any(not isinstance(log, str) or not log.strip() for log in logs):
            raise ValueError("application_logs must contain non-empty text entries")
        return [log.strip() for log in logs]

    @field_validator("service_status")
    @classmethod
    def validate_service_status(cls, status: str) -> str:
        if not status.strip():
            raise ValueError("service_status must be non-empty")
        return status.strip()
