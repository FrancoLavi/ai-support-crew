from src.services.llm_error_service import describe_llm_error


def test_describes_missing_aws_credentials():
    message = describe_llm_error(RuntimeError("Unable to locate credentials"), "bedrock")
    assert "AWS credentials were not found" in message


def test_describes_denied_bedrock_access():
    message = describe_llm_error(RuntimeError("AccessDeniedException"), "bedrock")
    assert "bedrock:InvokeModel" in message


def test_describes_region_or_endpoint_errors():
    message = describe_llm_error(RuntimeError("Could not connect to endpoint"), "bedrock")
    assert "region or Bedrock endpoint" in message


def test_gemini_503_never_uses_bedrock_message():
    message = describe_llm_error(
        RuntimeError("503 UNAVAILABLE: This model is currently experiencing high demand"),
        "gemini",
    )
    assert "Gemini" in message
    assert "Bedrock" not in message
