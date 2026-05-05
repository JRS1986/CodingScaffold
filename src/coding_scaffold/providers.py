from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Provider:
    name: str
    kind: str
    available: bool
    status: str
    endpoint: str | None = None
    model_family: str | None = None
    deployment: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_providers(env: dict[str, str] | None = None) -> list[Provider]:
    env_values = env or os.environ
    providers = [
        _local_provider("ollama", "http://127.0.0.1:11434/v1"),
        _local_provider("lmstudio", "http://127.0.0.1:1234/v1"),
        _local_provider("llama-server", "http://127.0.0.1:8080/v1"),
        _env_provider("openai", "OPENAI_API_KEY", env_values=env_values, model_family="openai"),
        _env_provider("anthropic", "ANTHROPIC_API_KEY", env_values=env_values, model_family="anthropic"),
        _azure_openai_provider(env_values),
        _azure_ai_provider(env_values),
        _env_provider("openrouter", "OPENROUTER_API_KEY", env_values=env_values, model_family="mixed"),
        _env_provider("groq", "GROQ_API_KEY", env_values=env_values, model_family="mixed"),
        _env_provider(
            "gemini",
            "GEMINI_API_KEY",
            fallback_env="GOOGLE_API_KEY",
            env_values=env_values,
            model_family="google",
        ),
        _env_provider(
            "github-models",
            "GITHUB_TOKEN",
            fallback_env="GH_TOKEN",
            env_values=env_values,
            model_family="mixed",
        ),
    ]
    providers.append(_github_copilot_provider())
    return providers


def _local_provider(name: str, endpoint: str) -> Provider:
    available = shutil.which(name) is not None
    return Provider(
        name=name,
        kind="local",
        available=available,
        status="CLI found" if available else "CLI not found",
        endpoint=endpoint,
        model_family="local",
    )


def _env_provider(
    name: str,
    env_name: str,
    fallback_env: str | None = None,
    env_values: Mapping[str, str] = os.environ,
    model_family: str | None = None,
) -> Provider:
    has_primary = bool(env_values.get(env_name))
    has_fallback = bool(fallback_env and env_values.get(fallback_env))
    found = has_primary or has_fallback
    source = env_name if has_primary else fallback_env
    return Provider(
        name=name,
        kind="cloud",
        available=found,
        status=f"{source} set" if found else f"{env_name} not set",
        model_family=model_family,
    )


def _azure_openai_provider(env_values: Mapping[str, str]) -> Provider:
    api_key = bool(env_values.get("AZURE_OPENAI_API_KEY"))
    endpoint = env_values.get("AZURE_OPENAI_ENDPOINT")
    deployment = env_values.get("AZURE_OPENAI_DEPLOYMENT") or env_values.get(
        "AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    available = bool(api_key and endpoint)
    status = "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT set" if available else "Azure OpenAI env not set"
    return Provider(
        "azure-openai",
        "cloud",
        available,
        status,
        endpoint=endpoint,
        model_family="openai",
        deployment=deployment,
    )


def _azure_ai_provider(env_values: Mapping[str, str]) -> Provider:
    api_key = bool(
        env_values.get("AZURE_AI_API_KEY")
        or env_values.get("AZURE_AI_FOUNDRY_API_KEY")
        or env_values.get("AZURE_AI_SERVICES_KEY")
        or env_values.get("AZURE_COGNITIVE_SERVICES_KEY")
    )
    endpoint = (
        env_values.get("AZURE_AI_ENDPOINT")
        or env_values.get("AZURE_AI_FOUNDRY_ENDPOINT")
        or env_values.get("AZURE_AI_SERVICES_ENDPOINT")
        or env_values.get("AZURE_COGNITIVE_SERVICES_ENDPOINT")
    )
    deployment = env_values.get("AZURE_AI_MODEL") or env_values.get("AZURE_AI_DEPLOYMENT")
    family = (
        env_values.get("AZURE_AI_MODEL_FAMILY")
        or env_values.get("AZURE_AI_FOUNDRY_MODEL_FAMILY")
        or env_values.get("AZURE_AI_SERVICES_MODEL_FAMILY")
    )
    available = bool(api_key and endpoint)
    status = "Azure AI endpoint and key set" if available else "Azure AI env not set"
    return Provider(
        "azure-ai",
        "cloud",
        available,
        status,
        endpoint=endpoint,
        model_family=family,
        deployment=deployment,
    )


def _github_copilot_provider() -> Provider:
    if shutil.which("gh") is None:
        return Provider("github-copilot-cli", "cloud", False, "gh CLI not found")
    try:
        result = subprocess.run(
            ["gh", "copilot", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return Provider("github-copilot-cli", "cloud", False, "gh CLI present; Copilot check failed")
    if result.returncode == 0:
        return Provider(
            "github-copilot-cli",
            "cloud",
            True,
            "gh Copilot extension found",
            model_family="copilot",
        )
    return Provider(
        "github-copilot-cli",
        "cloud",
        False,
        "gh CLI found; install/authenticate Copilot extension if desired",
        model_family="copilot",
    )
