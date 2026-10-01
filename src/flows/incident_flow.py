"""CrewAI Flow that orchestrates the incident analysis lifecycle."""

import logging
from typing import Any

from crewai import Crew, Process
from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel, Field

from src.agents import (
    create_log_analyst_agent,
    create_solution_agent,
    create_triage_agent,
)
from src.models import (
    Incident,
    IncidentContext,
    IncidentSeverity,
    LogAnalysis,
    Resolution,
    TriageResult,
)
from src.services.incident_data_service import gather_incident_context
from src.services.incident_memory_service import IncidentMemoryService
from src.services.sample_incident_service import load_sample_incidents
from src.tasks.incident_tasks import (
    create_log_analysis_task,
    create_solution_task,
    create_triage_task,
)


logger = logging.getLogger(__name__)


class IncidentFlowState(BaseModel):
    """Typed state shared by every stage of the incident Flow."""

    incident_id: str = Field(min_length=1)
    incident: Incident | None = None
    context: IncidentContext | None = None
    triage_result: TriageResult | None = None
    log_analysis: LogAnalysis | None = None
    final_resolution: Resolution | None = None
    severity_route: str | None = None
    historical_context: list[str] = []


class IncidentAnalysisFlow(Flow[IncidentFlowState]):
    """Simple event-driven Flow for one incident."""

    def __init__(
        self,
        *,
        llm: Any | None = None,
        initial_state: IncidentFlowState,
        memory_service: IncidentMemoryService | None = None,
    ) -> None:
        super().__init__(initial_state=initial_state)
        self._llm = llm
        self._triage_task = None
        self._log_analysis_task = None
        self._memory_service = memory_service or IncidentMemoryService()

    @start()
    def load_incident(self) -> Incident:
        """Load the selected incident from the local sample data."""

        logger.info("[Flow] Load Incident: %s", self.state.incident_id)
        incidents = load_sample_incidents()
        for incident in incidents:
            if incident.id == self.state.incident_id:
                self.state.incident = incident
                matches = self._memory_service.find_similar(incident)
                self.state.historical_context = [
                    self._memory_service.format_matches(matches)
                ]
                logger.info(
                    "[Flow] Memory: recovered %d similar historical incident(s)",
                    len(matches),
                )
                return incident
        raise ValueError(f"Incident not found: {self.state.incident_id}")

    @listen(load_incident)
    async def gather_context(self, incident: Incident) -> IncidentContext:
        """Collect external context concurrently before agent analysis."""

        logger.info("[Flow] Gather Context: %s", incident.id)
        context = await gather_incident_context(incident.id)
        self.state.context = context
        return context

    @listen(gather_context)
    async def run_triage(self, context: IncidentContext) -> TriageResult:
        """Run the triage Task inside a focused Crew."""

        incident = self._require_incident()
        logger.info("[Flow] Run Triage: %s", incident.id)
        agent = create_triage_agent(llm=self._llm)
        task = create_triage_task(agent)
        self._triage_task = task
        result = await Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        ).kickoff_async(
            inputs={
                "incident": incident.model_dump_json(indent=2),
            }
        )
        triage_result = self._get_pydantic_output(result, TriageResult)
        self.state.triage_result = triage_result
        return triage_result

    @listen(run_triage)
    async def run_log_analysis(self, triage_result: TriageResult) -> LogAnalysis:
        """Run log analysis with the completed triage Task as context."""

        incident = self._require_incident()
        logger.info("[Flow] Run Log Analysis: %s", incident.id)
        if self._triage_task is None:
            raise RuntimeError("Triage task is not available for log analysis.")
        agent = create_log_analyst_agent(llm=self._llm)
        task = create_log_analysis_task(agent, self._triage_task)
        self._log_analysis_task = task
        historical_context = "\n\n".join(self.state.historical_context)
        result = await Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        ).kickoff_async(
            inputs={
                "incident": incident.model_dump_json(indent=2),
                "historical_context": historical_context,
            }
        )
        log_analysis = self._get_pydantic_output(result, LogAnalysis)
        self.state.log_analysis = log_analysis
        return log_analysis

    @router(run_log_analysis)
    def decide_severity(self, log_analysis: LogAnalysis) -> str:
        """Route low/medium incidents separately from high/critical ones."""

        triage_result = self.state.triage_result
        if triage_result is None:
            raise RuntimeError("Triage result is missing for severity decision.")

        if triage_result.severity in {
            IncidentSeverity.LOW,
            IncidentSeverity.MEDIUM,
        }:
            route = "standard_resolution"
        else:
            route = "escalated_resolution"
        self.state.severity_route = route
        logger.info(
            "[Flow] Decision: severity=%s route=%s",
            triage_result.severity,
            route,
        )
        return route

    @listen("standard_resolution")
    async def generate_resolution(self) -> Resolution:
        """Generate a resolution without mandatory escalation."""

        logger.info("[Flow] Generate Resolution: standard path")
        return await self._generate_resolution(force_escalation=False)

    @listen("escalated_resolution")
    async def generate_escalated_resolution(self) -> Resolution:
        """Generate a resolution and mark it for escalation."""

        logger.info("[Flow] Generate Resolution: escalation path")
        return await self._generate_resolution(force_escalation=True)

    async def _generate_resolution(self, force_escalation: bool) -> Resolution:
        incident = self._require_incident()
        if self._triage_task is None or self._log_analysis_task is None:
            raise RuntimeError("Previous analysis tasks are missing for resolution.")
        agent = create_solution_agent(llm=self._llm)
        task = create_solution_task(
            agent,
            self._triage_task,
            self._log_analysis_task,
        )
        result = await Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        ).kickoff_async(inputs={"incident": incident.model_dump_json(indent=2)})
        resolution = self._get_pydantic_output(result, Resolution)

        if force_escalation:
            resolution = resolution.model_copy(
                update={
                    "should_escalate": True,
                    "escalation_reason": resolution.escalation_reason
                    or "High or critical severity requires Development/Engineering review.",
                }
            )
        else:
            resolution = resolution.model_copy(
                update={"should_escalate": False, "escalation_reason": None}
            )
        self.state.final_resolution = resolution
        try:
            self._memory_service.remember_resolution(incident, resolution)
        except Exception as exc:  # Memory must not hide an otherwise valid result.
            logger.warning("[Flow] Memory: could not save resolution: %s", exc)
        return resolution

    def _require_incident(self) -> Incident:
        if self.state.incident is None:
            raise RuntimeError("Incident is not loaded in Flow state.")
        return self.state.incident

    @staticmethod
    def _get_pydantic_output(output: Any, model: type[BaseModel]) -> Any:
        structured_output = getattr(output, "pydantic", None)
        if not isinstance(structured_output, model):
            raise RuntimeError(
                f"CrewAI returned an invalid structured output for {model.__name__}."
            )
        return structured_output


async def run_incident_flow(
    incident: Incident,
    *,
    llm: Any | None = None,
) -> IncidentAnalysisFlow:
    """Run the Flow for one validated incident and return its final state."""

    flow = IncidentAnalysisFlow(
        llm=llm,
        initial_state=IncidentFlowState(incident_id=incident.id),
    )
    await flow.kickoff_async()
    return flow


__all__ = ["IncidentFlowState", "IncidentAnalysisFlow", "run_incident_flow"]
