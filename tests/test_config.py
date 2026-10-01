from src.config import get_settings


def test_settings_have_safe_defaults(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
    monkeypatch.delenv("LLM_RETRY_BASE_DELAY", raising=False)

    settings = get_settings()

    assert settings.app_name == "AI Support Crew"
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.llm_max_retries == 5
    assert settings.llm_retry_base_delay == 2.0


def test_settings_read_retry_configuration(monkeypatch):
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_RETRY_BASE_DELAY", "3")

    settings = get_settings()

    assert settings.llm_max_retries == 4
    assert settings.llm_retry_base_delay == 3.0


def test_settings_read_bedrock_configuration(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    settings = get_settings()

    assert settings.llm_provider == "bedrock"
    assert settings.aws_region == "us-east-1"
    assert settings.bedrock_model_id.endswith(":0")
