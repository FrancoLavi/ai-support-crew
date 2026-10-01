"""Command-line entry point for the incident analysis Crew."""

import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from src.models import Incident
from src.config import active_llm_provider, get_settings
from src.flows.incident_flow import run_incident_flow
from src.services.llm_error_service import LLMExecutionError, describe_llm_error
from src.services.sample_incident_service import load_sample_incidents


def select_incident(incidents: list[Incident]) -> Incident:
    """Ask the user to select one incident from the sample data."""

    print("Available incidents:")
    for index, incident in enumerate(incidents, start=1):
        print(f"{index}. {incident.id} - {incident.title}")

    selection = input(f"Select an incident [1-{len(incidents)}]: ").strip()
    try:
        selected_index = int(selection) - 1
        return incidents[selected_index]
    except (ValueError, IndexError) as error:
        raise ValueError("Please select a valid incident number.") from error


def print_pipeline_result(incident: Incident, flow: Any) -> None:
    """Print the four requested stages in a readable format."""

    state = flow.state
    if not state.triage_result or not state.log_analysis or not state.final_resolution:
        raise RuntimeError("Flow did not produce all expected structured results.")

    print("\nINCIDENT")
    print(incident.model_dump_json(indent=2))
    print("\nTRIAGE RESULT")
    print(state.triage_result.model_dump_json(indent=2))
    print("\nLOG ANALYSIS")
    print(state.log_analysis.model_dump_json(indent=2))
    print("\nFINAL RESOLUTION")
    print(state.final_resolution.model_dump_json(indent=2))


def main() -> None:
    """Load, select, analyze, and display one sample incident."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        incidents = load_sample_incidents()
        incident = select_incident(incidents)
        flow = asyncio.run(run_incident_flow(incident))
        print_pipeline_result(incident, flow)
    except LLMExecutionError as error:
        print(f"Error: {error}")
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValidationError,
        ValueError,
    ) as error:
        print(f"Error: {error}")
    except Exception as error:
        provider = active_llm_provider(get_settings())
        print(f"Unable to run incident analysis: {describe_llm_error(error, provider)}")


if __name__ == "__main__":
    main()
