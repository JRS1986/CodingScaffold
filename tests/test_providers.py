from coding_scaffold.providers import detect_providers


def test_detects_azure_openai_without_exposing_key() -> None:
    providers = detect_providers(
        {
            "AZURE_OPENAI_API_KEY": "secret-value",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "team-gpt",
        }
    )

    provider = next(item for item in providers if item.name == "azure-openai")
    assert provider.available is True
    assert provider.model_family == "openai"
    assert provider.deployment == "team-gpt"
    assert "secret-value" not in provider.status


def test_detects_azure_ai_model_family() -> None:
    providers = detect_providers(
        {
            "AZURE_AI_API_KEY": "secret-value",
            "AZURE_AI_ENDPOINT": "https://example.services.ai.azure.com",
            "AZURE_AI_MODEL": "team-sonnet",
            "AZURE_AI_MODEL_FAMILY": "anthropic",
        }
    )

    provider = next(item for item in providers if item.name == "azure-ai")
    assert provider.available is True
    assert provider.model_family == "anthropic"
    assert provider.deployment == "team-sonnet"


def test_detects_azure_cognitive_services_aliases() -> None:
    providers = detect_providers(
        {
            "AZURE_COGNITIVE_SERVICES_KEY": "secret-value",
            "AZURE_COGNITIVE_SERVICES_ENDPOINT": "https://example.cognitiveservices.azure.com",
            "AZURE_AI_MODEL": "team-gpt",
            "AZURE_AI_SERVICES_MODEL_FAMILY": "openai",
        }
    )

    provider = next(item for item in providers if item.name == "azure-ai")
    assert provider.available is True
    assert provider.model_family == "openai"
    assert provider.endpoint == "https://example.cognitiveservices.azure.com"
