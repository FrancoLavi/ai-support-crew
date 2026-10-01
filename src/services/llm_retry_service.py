"""Granular retrying LLM used by CrewAI Agent executions."""

from __future__ import annotations

import logging
import random
import re
import time
from typing import Any, Literal

from crewai import LLM
from pydantic import BaseModel, Field

from src.services.llm_error_service import LLMExecutionError


logger = logging.getLogger(__name__)
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


def _status_code(error: Exception) -> int | None:
    """Read status codes from LiteLLM, provider, or wrapped exceptions."""

    for candidate in (
        getattr(error, "status_code", None),
        getattr(error, "status", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        try:
            if candidate is not None and int(candidate) in TRANSIENT_STATUS_CODES:
                return int(candidate)
        except (TypeError, ValueError):
            continue

    match = re.search(
        r"\b(?:http(?: error)?|status(?:_code)?|code|grpc(?: status)?)"
        r"\s*[:=]?\s*(429|500|502|503|504)\b",
        str(error),
        flags=re.IGNORECASE,
    )
    if match is None:
        match = re.search(
            r"\b(429|500|502|503|504)\s+"
            r"(?:unavailable|serviceunavailable|too many requests|bad gateway|gateway timeout)\b",
            str(error),
            flags=re.IGNORECASE,
        )
    return int(match.group(1)) if match else None


def is_transient_llm_error(error: Exception) -> bool:
    """Return true only for failures that are usually safe to retry."""

    if _status_code(error) in TRANSIENT_STATUS_CODES:
        return True
    lowered = str(error).lower()
    return any(
        term in lowered
        for term in (
            "rate limit",
            "resource exhausted",
            "serviceunavailable",
            "temporarily unavailable",
            "high demand",
            "throttl",
            "timeout",
            "timed out",
        )
    )


def _operation_name(
    tools: list[dict[str, Any]] | None,
    response_model: type[BaseModel] | None,
) -> Literal["native_tool_call", "structured_output", "completion"]:
    if tools:
        return "native_tool_call"
    if response_model:
        return "structured_output"
    return "completion"


class RetryingLLM(LLM):
    """CrewAI-compatible LLM that retries one call, never the whole Flow."""

    active_provider: str = Field(default="unknown")
    max_attempts: int = Field(default=5, ge=1, le=10)
    retry_base_delay: float = Field(default=2.0, gt=0.0, le=60.0)
    jitter_seconds: float = Field(default=0.25, ge=0.0, le=10.0)

    def call(
        self,
        messages: str | list[Any],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
        operation = _operation_name(tools, response_model)
        for attempt in range(1, self.max_attempts + 1):
            try:
                return super().call(
                    messages=messages,
                    tools=tools,
                    callbacks=callbacks,
                    available_functions=available_functions,
                    from_task=from_task,
                    from_agent=from_agent,
                    response_model=response_model,
                )
            except Exception as error:
                if not is_transient_llm_error(error):
                    raise
                if attempt == self.max_attempts:
                    raise LLMExecutionError(
                        self.active_provider,
                        error,
                        attempts=attempt,
                    ) from error

                delay = self.retry_base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0.0, self.jitter_seconds)
                status = _status_code(error)
                logger.warning(
                    "[LLM Retry] provider=%s operation=%s attempt=%s/%s "
                    "reason=%s next_retry=%.2fs",
                    self.active_provider,
                    operation,
                    attempt + 1,
                    self.max_attempts,
                    f"HTTP {status}" if status else "temporary service error",
                    delay,
                )
                time.sleep(delay + jitter)


__all__ = ["RetryingLLM", "is_transient_llm_error"]
