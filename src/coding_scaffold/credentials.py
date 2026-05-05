from __future__ import annotations

import json
from pathlib import Path


SECRET_ENV_NAMES = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_AI_API_KEY",
    "AZURE_AI_ENDPOINT",
    "AZURE_AI_MODEL",
    "AZURE_AI_MODEL_FAMILY",
    "AZURE_AI_SERVICES_KEY",
    "AZURE_AI_SERVICES_ENDPOINT",
    "AZURE_COGNITIVE_SERVICES_KEY",
    "AZURE_COGNITIVE_SERVICES_ENDPOINT",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
]


def scaffold_dir(target: Path) -> Path:
    return target.expanduser().resolve() / ".coding-scaffold"


def load_local_credentials(target: Path) -> dict[str, str]:
    directory = scaffold_dir(target)
    values: dict[str, str] = {}
    values.update(_read_env_file(directory / ".env.local"))
    values.update(_read_json_file(directory / "credentials.local.json"))
    return {key: value for key, value in values.items() if value}


def write_local_credential_file(target: Path, file_format: str) -> Path:
    directory = scaffold_dir(target)
    directory.mkdir(parents=True, exist_ok=True)
    if file_format == "json":
        path = directory / "credentials.local.json"
        if not path.exists():
            path.write_text(json.dumps({name: "" for name in SECRET_ENV_NAMES}, indent=2) + "\n")
        return path
    path = directory / ".env.local"
    if not path.exists():
        lines = [
            "# Local credentials for this project. Do not commit this file.",
            "# Fill only the providers you intend to use.",
            "",
            *[f"{name}=" for name in SECRET_ENV_NAMES],
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _read_json_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if value is not None}
