"""CrewAI Tasks for the incident analysis pipeline."""

from crewai import Agent, Task

from src.models import LogAnalysis, Resolution, TriageResult


def create_triage_task(agent: Agent) -> Task:
    """Create the task that classifies the incident."""

    return Task(
        description=(
            "Analyze the incident provided as JSON below. Determine its severity, "
            "identify the affected service or technical area, and write a concise "
            "technical summary. Use the incident facts only; do not invent logs or "
            "metrics.\n\nIncident JSON:\n{incident}"
        ),
        expected_output=(
            "A valid TriageResult with incident_id, severity (LOW, MEDIUM, HIGH, "
            "or CRITICAL), affected_area, summary, and "
            "requires_immediate_action."
        ),
        agent=agent,
        output_pydantic=TriageResult,
    )


def create_log_analysis_task(agent: Agent, triage_task: Task) -> Task:
    """Create the task that collects and analyzes technical evidence."""

    return Task(
        description=(
            "Investigate the incident using the available logs, monitoring metrics, "
            "service status, and local knowledge base Tools. Compare the evidence "
            "with the preceding triage result, identify relevant errors and patterns, "
            "and list probable causes with a confidence from 0.0 to 1.0.\n\n"
            "Incident JSON:\n{incident}\n\n"
            "Potentially relevant historical memory:\n{historical_context}\n\n"
            "Treat historical memory as a hypothesis, not as proof. Verify it against "
            "the current logs, metrics, and service status."
        ),
        expected_output=(
            "A valid LogAnalysis with incident_id, relevant_errors, probable_causes, "
            "and confidence between 0.0 and 1.0."
        ),
        agent=agent,
        context=[triage_task],
        output_pydantic=LogAnalysis,
    )


def create_solution_task(
    agent: Agent,
    triage_task: Task,
    log_analysis_task: Task,
) -> Task:
    """Create the task that proposes and evaluates a resolution."""

    return Task(
        description=(
            "Act as the senior Application Support reviewer. Use the incident, the "
            "structured triage result, and the structured log analysis to propose the "
            "most probable root cause. Provide concrete, ordered resolution steps. "
            "Decide whether Development or Engineering must be involved; if so, give "
            "a specific escalation reason.\n\nIncident JSON:\n{incident}"
        ),
        expected_output=(
            "A valid Resolution with incident_id, probable_root_cause, a non-empty "
            "list of recommended_steps, should_escalate, and an escalation_reason "
            "when escalation is true."
        ),
        agent=agent,
        context=[triage_task, log_analysis_task],
        output_pydantic=Resolution,
    )


def create_incident_tasks(
    triage_agent: Agent,
    log_analyst_agent: Agent,
    solution_agent: Agent,
) -> list[Task]:
    """Build the ordered task list and connect stage contexts."""

    triage_task = create_triage_task(triage_agent)
    log_analysis_task = create_log_analysis_task(log_analyst_agent, triage_task)
    solution_task = create_solution_task(
        solution_agent,
        triage_task,
        log_analysis_task,
    )
    return [triage_task, log_analysis_task, solution_task]


__all__ = [
    "create_triage_task",
    "create_log_analysis_task",
    "create_solution_task",
    "create_incident_tasks",
]
