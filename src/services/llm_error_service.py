"""Provider-aware LLM errors for the command-line entry point."""


class LLMExecutionError(RuntimeError):
    """Final provider error after retry handling has been exhausted."""

    def __init__(
        self,
        provider: str,
        original_error: Exception,
        attempts: int = 1,
    ) -> None:
        self.provider = provider
        self.original_error = original_error
        self.attempts = attempts
        if attempts > 1 and _is_transient_message(str(original_error)):
            message = f"{provider.title()} remained unavailable after {attempts} attempts."
        else:
            message = describe_llm_error(original_error, provider)
        super().__init__(message)


def describe_llm_error(error: Exception, provider: str = "unknown") -> str:
    """Translate an error using the provider that actually handled the request."""

    message = str(error)
    lowered = message.lower()

    if provider == "bedrock":
        if any(term in lowered for term in ("no credentials", "unable to locate credentials", "credential")):
            return (
                "AWS credentials were not found. Configure an AWS profile/SSO session, "
                "environment credentials, or an attached IAM role."
            )
        if any(term in lowered for term in ("accessdenied", "access denied", "not authorized", "unauthorized")):
            return (
                "AWS denied access to the Bedrock model. Check bedrock:InvokeModel "
                "permissions and model access in the selected region."
            )
        if any(term in lowered for term in ("region", "endpoint", "could not connect", "connection error")):
            return (
                "The AWS region or Bedrock endpoint is invalid or unreachable. Check "
                "AWS_REGION and network connectivity."
            )
        if any(term in lowered for term in ("throttl", "serviceunavailable", "internalservererror", "service error")):
            return (
                "Amazon Bedrock returned a service or throttling error. Retry later and "
                "check Bedrock quotas and service health."
            )

    if provider == "gemini":
        if any(term in lowered for term in ("503", "serviceunavailable", "high demand", "temporarily unavailable")):
            return "Gemini is temporarily saturated or unavailable. Retry later."
        if any(term in lowered for term in ("429", "rate limit", "resource exhausted", "too many requests")):
            return "Gemini rate limit reached. Retry later or review the provider quota."

    if any(term in lowered for term in ("timeout", "timed out")):
        return f"{provider.title()} did not respond in time. Retry later."

    return f"{provider.title()} returned an error: {message}"


def _is_transient_message(message: str) -> bool:
    lowered = message.lower()
    return any(
        term in lowered
        for term in (
            "rate limit",
            "serviceunavailable",
            "temporarily unavailable",
            "high demand",
            "throttl",
        )
    ) or any(
        f"http {status}" in lowered
        or f"status {status}" in lowered
        or f"code {status}" in lowered
        for status in (429, 500, 502, 503, 504)
    )


__all__ = ["LLMExecutionError", "describe_llm_error"]
