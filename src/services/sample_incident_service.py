"""Local repository for sample incidents."""

import json
from pathlib import Path

from src.models import Incident


SAMPLE_INCIDENTS_PATH = Path(__file__).parents[2] / "data" / "sample_incidents.json"


def load_sample_incidents() -> list[Incident]:
    """Load and validate all sample incidents from the local JSON file."""

    with SAMPLE_INCIDENTS_PATH.open(encoding="utf-8") as incidents_file:
        raw_incidents = json.load(incidents_file)
    return [Incident.model_validate(raw_incident) for raw_incident in raw_incidents]
