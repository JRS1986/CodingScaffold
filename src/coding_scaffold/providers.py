from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from collections.abc import Mapping
from dataclasses import asdict, dataclass


REDACTED_PLACEHOLDER = "<configured locally; see .env.local>"


@dataclass(frozen=True)
class Provider:
    name: str
    kind: str
    available: bool
    status: str
    endpoint: str | None = None
    model_family: str | None = None
    deployment: str | None = None
    redact_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for field in self.redact_fields:
            if data.get(field):
                data[field] = REDACTED_PLACEHOLDER
        data.pop("redact_fields", None)
        return data


def detect_providers(env: dict[str, str] | None = None, *, include_copilot: bool = False) -> list[Provider]:
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
    if include_copilot:
        providers.append(_github_copilot_provider())
    return providers


def _probe_endpoint(url: str, timeout: float = 1.0) -> bool:
    """Return True if ``url`` responds with a 2xx or 3xx status within ``timeout``.

    Any exception (URLError, socket.timeout, HTTPError, OSError, etc.) is
    swallowed and returns False so callers can use this as a simple
    reachability check.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            return 200 <= int(status) < 400
    except Exception:
        return False


def _local_probe_url(name: str, endpoint: str) -> str:
    base = endpoint.rstrip("/")
    if name == "ollama":
        # Ollama's tag listing lives at the server root, not under /v1.
        if base.endswith("/v1"):
            base = base[:-3].rstrip("/")
        return base + "/api/tags"
    # LM Studio and llama-server expose the OpenAI-compatible /v1/models path.
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base + "/models"


def _local_provider(name: str, endpoint: str) -> Provider:
    cli_present = shutil.which(name) is not None
    if not cli_present:
        return Provider(
            name=name,
            kind="local",
            available=False,
            status="CLI not found",
            endpoint=endpoint,
            model_family="local",
        )
    probe_url = _local_probe_url(name, endpoint)
    endpoint_reachable = _probe_endpoint(probe_url)
    available = cli_present and endpoint_reachable
    if available:
        status = "CLI found; endpoint reachable"
    else:
        status = f"CLI found; endpoint unreachable at {probe_url}"
    return Provider(
        name=name,
        kind="local",
        available=available,
        status=status,
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
        redact_fields=("endpoint", "deployment"),
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
        redact_fields=("endpoint", "deployment", "model_family"),
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
