"""CrewAI task definitions will live here."""

from src.tasks.incident_tasks import (
    create_incident_tasks,
    create_log_analysis_task,
    create_solution_task,
    create_triage_task,
)

__all__ = [
    "create_incident_tasks",
    "create_triage_task",
    "create_log_analysis_task",
    "create_solution_task",
]
