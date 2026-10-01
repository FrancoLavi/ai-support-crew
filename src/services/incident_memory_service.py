"""Local CrewAI Memory integration for previously resolved incidents."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from crewai import Memory
from crewai.memory.types import MemoryMatch

from src.models import HistoricalIncident, Incident, Resolution


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_INCIDENTS_PATH = PROJECT_ROOT / "data" / "historical_incidents.json"
DEFAULT_MEMORY_PATH = PROJECT_ROOT / "data" / "memory"
EMBEDDING_DIMENSIONS = 128


def local_incident_embedder(texts: list[str]) -> list[list[float]]:
    """Create deterministic local bag-of-words embeddings for support text.

    CrewAI Memory accepts a callable embedder. Hashing tokens keeps this demo
    local and reproducible, while LanceDB handles similarity search.
    """

    vectors: list[list[float]] = []
    for text in texts:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        counts = Counter(tokens)
        for token, count in counts.items():
            index = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            vector[index % EMBEDDING_DIMENSIONS] += float(count)
        vectors.append(vector)
    return vectors


class IncidentMemoryService:
    """Small adapter around CrewAI's official local Memory implementation."""

    def __init__(
        self,
        *,
        storage_path: Path = DEFAULT_MEMORY_PATH,
        history_path: Path = HISTORICAL_INCIDENTS_PATH,
    ) -> None:
        self.storage_path = storage_path
        self.history_path = history_path
        self.memory = Memory(
            storage=str(storage_path),
            embedder=local_incident_embedder,
            # Explicit metadata means the demo does not need a second LLM call
            # to infer categories or importance while seeding records.
            llm="gpt-5.4-mini",
        )

    def seed_historical_incidents(self) -> int:
        """Store the bundled history once and return the number of records added."""

        marker = self.storage_path / ".historical_seeded"
        if marker.exists():
            return 0

        records = self._load_history()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        for record in records:
            self.memory.remember(
                self._to_memory_text(record),
                scope="historical_incidents",
                categories=["incident", "resolved"],
                metadata={"incident_id": record.incident_id, "service": record.service},
                importance=0.8,
                source="historical_dataset",
            )
        marker.write_text("seeded\n", encoding="utf-8")
        return len(records)

    def find_similar(self, incident: Incident, limit: int = 3) -> list[MemoryMatch]:
        """Return resolved incidents semantically similar to the current incident."""

        self.seed_historical_incidents()
        query = " ".join(
            [incident.title, incident.description, incident.service, *incident.logs]
        )
        return self.memory.recall(
            query,
            scope="historical_incidents",
            limit=limit,
            depth="shallow",
        )

    def remember_resolution(self, incident: Incident, resolution: Resolution) -> None:
        """Persist the current resolution as a future support reference."""

        self.memory.remember(
            self._to_resolution_text(incident, resolution),
            scope="historical_incidents",
            categories=["incident", "resolved"],
            metadata={"incident_id": incident.id, "service": incident.service},
            importance=0.7,
            source="incident_flow",
        )

    @staticmethod
    def format_matches(matches: list[MemoryMatch]) -> str:
        """Convert CrewAI matches into concise, predictable task context."""

        if not matches:
            return "No similar resolved incident was found in local memory."
        return "\n\n".join(
            f"Historical match {index} (relevance={match.score:.2f}):\n{match.record.content}"
            for index, match in enumerate(matches, start=1)
        )

    def _load_history(self) -> list[HistoricalIncident]:
        payload: Any = json.loads(self.history_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Historical incident data must be a JSON list.")
        return [HistoricalIncident.model_validate(item) for item in payload]

    @staticmethod
    def _to_memory_text(record: HistoricalIncident) -> str:
        return (
            f"Incident {record.incident_id}: {record.title}\n"
            f"Service: {record.service}\n"
            f"Summary: {record.summary}\n"
            f"Probable root cause: {record.probable_root_cause}\n"
            f"Recommended steps: {'; '.join(record.recommended_steps)}\n"
            f"Tags: {', '.join(record.tags)}"
        )

    @staticmethod
    def _to_resolution_text(incident: Incident, resolution: Resolution) -> str:
        return (
            f"Incident {incident.id}: {incident.title}\n"
            f"Service: {incident.service}\n"
            f"Summary: {incident.description}\n"
            f"Probable root cause: {resolution.probable_root_cause}\n"
            f"Recommended steps: {'; '.join(resolution.recommended_steps)}\n"
            f"Escalated: {resolution.should_escalate}"
        )


__all__ = ["IncidentMemoryService", "local_incident_embedder"]
