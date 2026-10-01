import pytest
from crewai import LLM

from src.agents.incident_agents import create_llm
from src.config import Settings


def bedrock_settings(**overrides):
    values = {
        "llm_provider": "bedrock",
        "aws_region": "us-east-1",
        "bedrock_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
        "llm_api_key": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_bedrock_uses_litellm_route_without_api_key(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    llm = create_llm(bedrock_settings())

    assert isinstance(llm, LLM)
    assert llm.model == "bedrock/anthropic.claude-3-haiku-20240307-v1:0"
    assert llm.provider == "litellm"


def test_gemini_does_not_require_aws_credentials(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    llm = create_llm(
        Settings(
            llm_provider="litellm",
            llm_model="gemini/gemini-3.5-flash-lite",
            llm_api_key="test-key",
        )
    )

    assert llm.active_provider == "gemini"
    assert llm.additional_params["num_retries"] == 0


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("aws_region", "AWS_REGION"),
        ("bedrock_model_id", "BEDROCK_MODEL_ID"),
    ],
)
def test_bedrock_requires_region_and_model_id(field, message):
    with pytest.raises(RuntimeError, match=message):
        create_llm(bedrock_settings(**{field: None}))
