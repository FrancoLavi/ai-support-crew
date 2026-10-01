import pytest

from src.services import llm_retry_service
from src.services.llm_error_service import LLMExecutionError
from src.services.llm_retry_service import RetryingLLM, is_transient_llm_error
from src.models import LogAnalysis, TriageResult


def make_llm(provider="gemini", attempts=5):
    return RetryingLLM(
        model="gemini/gemini-3.5-flash-lite",
        provider="litellm",
        api_key="test-key",
        additional_params={"num_retries": 0},
        active_provider=provider,
        max_attempts=attempts,
        retry_base_delay=2,
        jitter_seconds=0,
    )


def test_transient_statuses_are_retryable_and_auth_is_not():
    for status in (429, 500, 502, 503, 504):
        assert is_transient_llm_error(RuntimeError(f"HTTP {status}"))
    assert is_transient_llm_error(RuntimeError("rate limit exceeded"))
    assert not is_transient_llm_error(RuntimeError("invalid API key"))
    assert not is_transient_llm_error(RuntimeError("validation error"))


def test_gemini_503_retries_only_the_llm_call(monkeypatch):
    llm = make_llm()
    calls = 0
    sleeps = []

    def fake_super_call(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("HTTP 503 ServiceUnavailable")
        return "structured result"

    monkeypatch.setattr("crewai.LLM.call", fake_super_call)
    monkeypatch.setattr(llm_retry_service.time, "sleep", sleeps.append)

    result = llm.call("analyze", response_model=LogAnalysis)

    assert result == "structured result"
    assert calls == 3
    assert sleeps == [2, 4]


def test_triage_is_not_repeated_when_log_analysis_retries(monkeypatch):
    llm = make_llm()
    triage_calls = 0
    log_calls = 0

    def fake_super_call(self, messages, *args, **kwargs):
        nonlocal triage_calls, log_calls
        if messages == "triage":
            triage_calls += 1
            return "triage result"
        log_calls += 1
        if log_calls < 3:
            raise RuntimeError("HTTP 503 GeminiException")
        return "log analysis result"

    monkeypatch.setattr("crewai.LLM.call", fake_super_call)
    monkeypatch.setattr(llm_retry_service.time, "sleep", lambda _: None)

    triage_result = llm.call("triage", response_model=TriageResult)
    log_result = llm.call("log analysis", response_model=LogAnalysis)

    assert triage_result == "triage result"
    assert log_result == "log analysis result"
    assert triage_calls == 1
    assert log_calls == 3


def test_persistent_gemini_503_stops_after_max_attempts(monkeypatch):
    llm = make_llm(attempts=5)
    calls = 0

    def fake_super_call(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr("crewai.LLM.call", fake_super_call)
    monkeypatch.setattr(llm_retry_service.time, "sleep", lambda _: None)

    with pytest.raises(LLMExecutionError, match="Gemini remained unavailable after 5 attempts"):
        llm.call("analyze", tools=[{"name": "read_logs"}])

    assert calls == 5


def test_authentication_error_is_not_retried(monkeypatch):
    llm = make_llm()
    calls = 0

    def fake_super_call(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("401 AuthenticationError: invalid API key")

    monkeypatch.setattr("crewai.LLM.call", fake_super_call)
    monkeypatch.setattr(llm_retry_service.time, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="AuthenticationError"):
        llm.call("analyze")

    assert calls == 1


def test_native_tool_call_retry_is_provider_aware(monkeypatch, caplog):
    llm = make_llm(provider="gemini", attempts=3)
    calls = 0

    def fake_super_call(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("HTTP 503 GeminiException")
        return "tool result"

    monkeypatch.setattr("crewai.LLM.call", fake_super_call)
    monkeypatch.setattr(llm_retry_service.time, "sleep", lambda _: None)

    with caplog.at_level("WARNING"):
        result = llm.call("inspect", tools=[{"name": "read_logs"}])

    assert result == "tool result"
    assert calls == 2
    assert "provider=gemini" in caplog.text
    assert "operation=native_tool_call" in caplog.text
    assert "Bedrock" not in caplog.text
