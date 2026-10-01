"""CrewAI Agent definitions for the incident support workflow."""

import os
from typing import Any

from crewai import Agent, LLM

from src.config import Settings, active_llm_provider, get_settings
from src.services.llm_retry_service import RetryingLLM
from src.tools import (
    application_logs_tool,
    knowledge_base_tool,
    monitoring_metrics_tool,
    service_status_tool,
)


def create_llm(settings: Settings | None = None) -> LLM:
    """Create the configured LLM without embedding provider credentials."""

    resolved_settings = settings or get_settings()
    provider = resolved_settings.llm_provider.strip().lower()

    if provider in {"bedrock", "aws-bedrock"}:
        if not resolved_settings.aws_region:
            raise RuntimeError(
                "AWS_REGION is not configured. Set it before using Amazon Bedrock."
            )
        if not resolved_settings.bedrock_model_id:
            raise RuntimeError(
                "BEDROCK_MODEL_ID is not configured. Set it before using Amazon Bedrock."
            )

        # LiteLLM uses boto3's standard AWS credential provider chain. These
        # region variables contain no secrets and make the selected region
        # explicit without replacing profile, role, or SSO credentials.
        os.environ.setdefault("AWS_REGION", resolved_settings.aws_region)
        os.environ.setdefault("AWS_DEFAULT_REGION", resolved_settings.aws_region)
        model_id = resolved_settings.bedrock_model_id
        if model_id.startswith("bedrock/"):
            model_id = model_id.removeprefix("bedrock/")
        return RetryingLLM(
            model=f"bedrock/{model_id}",
            provider="litellm",
            additional_params={"num_retries": 0},
            active_provider="bedrock",
            max_attempts=resolved_settings.llm_max_retries,
            retry_base_delay=resolved_settings.llm_retry_base_delay,
        )

    if not resolved_settings.llm_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Set it in the environment or .env file."
        )

    return RetryingLLM(
        model=resolved_settings.llm_model,
        provider=resolved_settings.llm_provider,
        api_key=resolved_settings.llm_api_key,
        additional_params={"num_retries": 0},
        active_provider=active_llm_provider(resolved_settings),
        max_attempts=resolved_settings.llm_max_retries,
        retry_base_delay=resolved_settings.llm_retry_base_delay,
    )


def _resolve_llm(llm: Any | None) -> Any:
    """Use an injected LLM in tests or build the configured one for the app."""

    return llm if llm is not None else create_llm()


def create_triage_agent(llm: Any | None = None) -> Agent:
    """Create the agent responsible for initial incident classification."""

    return Agent(
        role="Incident Triage Specialist",
        goal=(
            "Classify the incident severity, identify the affected service or area, "
            "and produce a concise technical summary."
        ),
        backstory=(
            "You are an experienced support engineer who quickly turns raw incident "
            "reports into consistent, actionable triage information."
        ),
        tools=[],
        llm=_resolve_llm(llm),
        allow_delegation=False,
    )


def create_log_analyst_agent(llm: Any | None = None) -> Agent:
    """Create the agent responsible for troubleshooting evidence."""

    return Agent(
        role="Log Analyst and Troubleshooting Specialist",
        goal=(
            "Inspect logs, metrics, service status, and known symptoms to identify "
            "relevant patterns and probable causes."
        ),
        backstory=(
            "You are a methodical application support specialist who validates clues "
            "across multiple observability sources before suggesting a cause."
        ),
        tools=[
            application_logs_tool,
            monitoring_metrics_tool,
            service_status_tool,
            knowledge_base_tool,
        ],
        llm=_resolve_llm(llm),
        allow_delegation=False,
    )


def create_solution_agent(llm: Any | None = None) -> Agent:
    """Create the senior agent responsible for the proposed resolution."""

    return Agent(
        role="Senior Application Support Engineer",
        goal=(
            "Combine triage and log analysis results into a probable root cause, "
            "concrete resolution steps, and a clear escalation decision."
        ),
        backstory=(
            "You are a senior support engineer who communicates practical fixes and "
            "escalates to Development or Engineering when evidence or risk requires it."
        ),
        tools=[],
        llm=_resolve_llm(llm),
        allow_delegation=False,
    )


__all__ = [
    "create_llm",
    "create_triage_agent",
    "create_log_analyst_agent",
    "create_solution_agent",
]
