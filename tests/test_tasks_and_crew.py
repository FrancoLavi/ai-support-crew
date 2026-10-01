from crewai import LLM, Process

from src.agents import (
    create_log_analyst_agent,
    create_solution_agent,
    create_triage_agent,
)
from src.services.incident_crew_service import create_incident_crew
from src.tasks import create_incident_tasks


TEST_LLM = LLM(model="openai/gpt-4o-mini", api_key="test-key")


def test_tasks_are_structured_and_connected_by_context():
    tasks = create_incident_tasks(
        create_triage_agent(TEST_LLM),
        create_log_analyst_agent(TEST_LLM),
        create_solution_agent(TEST_LLM),
    )

    assert len(tasks) == 3
    assert tasks[0].output_pydantic.__name__ == "TriageResult"
    assert tasks[1].output_pydantic.__name__ == "LogAnalysis"
    assert tasks[2].output_pydantic.__name__ == "Resolution"
    assert tasks[1].context == [tasks[0]]
    assert tasks[2].context == [tasks[0], tasks[1]]


def test_crew_uses_sequential_process_and_does_not_execute_on_creation():
    crew = create_incident_crew(llm=TEST_LLM)

    assert crew.process is Process.sequential
    assert len(crew.tasks) == 3
    assert len(crew.agents) == 3
