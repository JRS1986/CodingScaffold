from urllib.error import URLError

from coding_scaffold.providers import _local_provider, detect_providers


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


def test_detect_providers_skips_copilot_subprocess_by_default(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr("coding_scaffold.providers.subprocess.run", fail_if_called)

    providers = detect_providers({})

    assert all(provider.name != "github-copilot-cli" for provider in providers)


def test_local_provider_unreachable_when_endpoint_refuses_connection(monkeypatch) -> None:
    monkeypatch.setattr(
        "coding_scaffold.providers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )

    def refuse(*args, **kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr("coding_scaffold.providers.urllib.request.urlopen", refuse)

    provider = _local_provider("ollama", "http://127.0.0.1:11434/v1")

    assert provider.available is False
    assert "unreachable" in provider.status


def test_local_provider_available_when_endpoint_responds_ok(monkeypatch) -> None:
    monkeypatch.setattr(
        "coding_scaffold.providers.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getcode(self):
            return 200

    monkeypatch.setattr(
        "coding_scaffold.providers.urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    provider = _local_provider("ollama", "http://127.0.0.1:11434/v1")

    assert provider.available is True
    assert "reachable" in provider.status


def test_azure_openai_provider_redacts_endpoint_and_deployment():
    from coding_scaffold.providers import REDACTED_PLACEHOLDER, detect_providers

    env = {
        "AZURE_OPENAI_API_KEY": "key-xyz",
        "AZURE_OPENAI_ENDPOINT": "https://contoso-prod.openai.azure.com/",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4-internal",
    }
    providers = detect_providers(env=env)
    azure = next(p for p in providers if p.name == "azure-openai")

    # In-memory values stay intact for routing.
    assert azure.endpoint == "https://contoso-prod.openai.azure.com/"
    assert azure.deployment == "gpt-4-internal"

    # Serialized form redacts.
    serialized = azure.to_dict()
    assert serialized["endpoint"] == REDACTED_PLACEHOLDER
    assert serialized["deployment"] == REDACTED_PLACEHOLDER
    assert "redact_fields" not in serialized
    # Non-redacted providers serialize unchanged.
    openai = next(p for p in providers if p.name == "openai")
    assert "redact_fields" not in openai.to_dict()


def test_detect_providers_can_include_copilot_status(monkeypatch) -> None:
    class Result:
        returncode = 0

    monkeypatch.setattr(
        "coding_scaffold.providers.shutil.which",
        lambda name: "/usr/bin/gh" if name == "gh" else None,
    )
    monkeypatch.setattr("coding_scaffold.providers.subprocess.run", lambda *args, **kwargs: Result())

    providers = detect_providers({}, include_copilot=True)

    provider = next(item for item in providers if item.name == "github-copilot-cli")
    assert provider.available is True
