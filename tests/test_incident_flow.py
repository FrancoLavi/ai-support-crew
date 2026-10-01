from crewai import LLM

from src.flows import IncidentAnalysisFlow, IncidentFlowState
from src.models import IncidentSeverity, LogAnalysis, TriageResult


TEST_LLM = LLM(model="openai/gpt-4o-mini", api_key="test-key")


def make_flow() -> IncidentAnalysisFlow:
    return IncidentAnalysisFlow(
        llm=TEST_LLM,
        initial_state=IncidentFlowState(incident_id="INC-001"),
    )


def make_triage(severity: IncidentSeverity) -> TriageResult:
    return TriageResult(
        incident_id="INC-001",
        severity=severity,
        affected_area="payments-api",
        summary="Simulated incident.",
        requires_immediate_action=severity in {
            IncidentSeverity.HIGH,
            IncidentSeverity.CRITICAL,
        },
    )


def make_log_analysis() -> LogAnalysis:
    return LogAnalysis(
        incident_id="INC-001",
        relevant_errors=["simulated error"],
        probable_causes=["simulated cause"],
        confidence=0.8,
    )


def test_flow_uses_typed_state_and_loads_incident():
    flow = make_flow()

    incident = flow.load_incident()

    assert flow.state.incident_id == "INC-001"
    assert flow.state.incident == incident
    assert flow.state.id


def test_low_and_medium_severity_use_standard_route():
    flow = make_flow()

    for severity in (IncidentSeverity.LOW, IncidentSeverity.MEDIUM):
        flow.state.triage_result = make_triage(severity)

        route = flow.decide_severity(make_log_analysis())

        assert route == "standard_resolution"


def test_high_and_critical_severity_use_escalated_route():
    flow = make_flow()

    for severity in (IncidentSeverity.HIGH, IncidentSeverity.CRITICAL):
        flow.state.triage_result = make_triage(severity)

        route = flow.decide_severity(make_log_analysis())

        assert route == "escalated_resolution"
