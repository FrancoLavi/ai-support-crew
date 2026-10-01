"""Construction and execution helpers for the incident Crew."""

from typing import Any

from crewai import Crew, Process

from src.agents import (
    create_log_analyst_agent,
    create_solution_agent,
    create_triage_agent,
)
from src.models import Incident
from src.tasks.incident_tasks import create_incident_tasks


def create_incident_crew(llm: Any | None = None) -> Crew:
    """Build the sequential incident analysis Crew without executing it."""

    triage_agent = create_triage_agent(llm=llm)
    log_analyst_agent = create_log_analyst_agent(llm=llm)
    solution_agent = create_solution_agent(llm=llm)
    tasks = create_incident_tasks(
        triage_agent,
        log_analyst_agent,
        solution_agent,
    )

    return Crew(
        agents=[triage_agent, log_analyst_agent, solution_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )


def run_incident_crew(incident: Incident, llm: Any | None = None) -> Any:
    """Execute the Crew for one incident and return its structured output."""

    crew = create_incident_crew(llm=llm)
    return crew.kickoff(inputs={"incident": incident.model_dump_json(indent=2)})


__all__ = ["create_incident_crew", "run_incident_crew"]
