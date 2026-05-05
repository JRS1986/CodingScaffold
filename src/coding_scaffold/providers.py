from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Provider:
    name: str
    kind: str
    available: bool
    status: str
    endpoint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_providers() -> list[Provider]:
    providers = [
        _local_provider("ollama", "http://127.0.0.1:11434/v1"),
        _local_provider("lmstudio", "http://127.0.0.1:1234/v1"),
        _local_provider("llama-server", "http://127.0.0.1:8080/v1"),
        _env_provider("openai", "OPENAI_API_KEY"),
        _env_provider("anthropic", "ANTHROPIC_API_KEY"),
        _env_provider("openrouter", "OPENROUTER_API_KEY"),
        _env_provider("groq", "GROQ_API_KEY"),
        _env_provider("gemini", "GEMINI_API_KEY", fallback_env="GOOGLE_API_KEY"),
        _env_provider("github-models", "GITHUB_TOKEN", fallback_env="GH_TOKEN"),
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
    )


def _env_provider(name: str, env_name: str, fallback_env: str | None = None) -> Provider:
    has_primary = bool(os.environ.get(env_name))
    has_fallback = bool(fallback_env and os.environ.get(fallback_env))
    found = has_primary or has_fallback
    source = env_name if has_primary else fallback_env
    return Provider(
        name=name,
        kind="cloud",
        available=found,
        status=f"{source} set" if found else f"{env_name} not set",
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
        return Provider("github-copilot-cli", "cloud", True, "gh Copilot extension found")
    return Provider(
        "github-copilot-cli",
        "cloud",
        False,
        "gh CLI found; install/authenticate Copilot extension if desired",
    )
