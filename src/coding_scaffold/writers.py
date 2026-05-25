from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .file_ops import write_json, write_text
from .hardware import HardwareProfile
from .intake import IntakeAnswers
from .model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from .providers import Provider
from .router import RoutingPlan
from .scaffold_version import write_scaffold_version
from .template_resources import read_template, render_template


@dataclass(frozen=True)
class ScaffoldManifest:
    scaffold_dir: Path
    files: list[Path]


def write_scaffold(
    target: Path,
    intake: IntakeAnswers,
    hardware: HardwareProfile,
    providers: list[Provider],
    routing: RoutingPlan,
) -> ScaffoldManifest:
    target = target.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    scaffold_dir = target / ".coding-scaffold"
    scaffold_dir.mkdir(exist_ok=True)

    files = [
        write_json(scaffold_dir / "project.json", intake.to_dict()),
        write_json(scaffold_dir / "hardware.json", hardware.to_dict()),
        write_json(scaffold_dir / "providers.json", [provider.to_dict() for provider in providers]),
        write_json(scaffold_dir / "routing.json", routing.to_dict()),
        write_json(scaffold_dir / "model-selection.json", _model_selection_json(routing)),
        write_json(scaffold_dir / "opencode.json", _opencode_config(routing)),
        write_json(scaffold_dir / "openclaude.json", _openclaude_config(routing)),
        write_json(scaffold_dir / "hermes.json", _hermes_config(routing)),
        write_json(scaffold_dir / "pi.json", _pi_config(routing)),
        write_text(scaffold_dir / "routellm.config.yaml", _routellm_yaml(routing)),
        write_text(scaffold_dir / ".gitignore", _scaffold_gitignore()),
        write_text(scaffold_dir / ".env.example", _env_example()),
        write_json(scaffold_dir / "credentials.example.json", _credentials_example()),
        write_text(scaffold_dir / "CREDENTIALS.md", _credentials_md()),
        write_text(scaffold_dir / "MODEL_SELECTION.md", _model_selection_md()),
        write_text(scaffold_dir / "TOOLS.md", _tools_md()),
        write_text(scaffold_dir / "ORCHESTRATION.md", _orchestration_md()),
        write_json(scaffold_dir / "orchestration.json", _orchestration_json()),
        write_text(scaffold_dir / "skills" / "README.md", _skills_readme()),
        write_text(scaffold_dir / "FIRST_SESSION.md", _first_session_md()),
        write_text(scaffold_dir / "GETTING_STARTED.md", _getting_started_md(intake, routing)),
        write_text(scaffold_dir / "SKILLS.md", _skills_md()),
        write_text(scaffold_dir / "AGENTS.md", _agents_md(intake, routing)),
    ]
    if intake.mode == "beginner":
        files.append(write_text(scaffold_dir / "BEGINNER_PATH.md", _beginner_path_md(intake, routing)))
    files.append(write_scaffold_version(target, files))
    return ScaffoldManifest(scaffold_dir=scaffold_dir, files=files)


def _opencode_config(routing: RoutingPlan) -> dict[str, object]:
    return {
        "providerHints": {
            "local": {
                "endpoint": routing.local_endpoint,
                "model": routing.weak_model,
            },
            "strong": {
                "provider": routing.cloud_provider or "local",
                "model": routing.strong_model,
            },
        },
        "nativeAdapter": {
            "command": "coding-scaffold tools adapt --target . --tool opencode",
            "writes": ["opencode.json", ".opencode/agents/*.md", ".opencode/commands/*.md"],
        },
        "routing": routing.to_dict(),
    }


def _openclaude_config(routing: RoutingPlan) -> dict[str, object]:
    return {
        "profiles": [
            {
                "name": "local",
                "base_url": routing.local_endpoint,
                "model": routing.weak_model,
            },
            {
                "name": "strong",
                "provider": routing.cloud_provider or "local",
                "model": routing.strong_model,
            },
        ],
        "default_profile": "local",
    }


def _hermes_config(routing: RoutingPlan) -> dict[str, object]:
    return {
        "profiles": {
            "routine": {
                "endpoint": routing.local_endpoint,
                "model": routing.weak_model,
            },
            "heavy_lift": {
                "provider": routing.cloud_provider or "local",
                "model": routing.strong_model,
            },
        },
        "nativeAdapter": {
            "command": "coding-scaffold tools adapt --target . --tool hermes",
            "writes": [".coding-scaffold/HERMES.md"],
        },
        "setup": ["hermes setup", "hermes model", "hermes tools", "hermes env"],
    }


def _pi_config(routing: RoutingPlan) -> dict[str, object]:
    return {
        "profiles": {
            "routine": {
                "endpoint": routing.local_endpoint,
                "model": routing.weak_model,
            },
            "heavy_lift": {
                "provider": routing.cloud_provider or "local",
                "model": routing.strong_model,
            },
        },
        "nativeAdapter": {
            "command": "coding-scaffold tools adapt --target . --tool pi",
            "writes": [".coding-scaffold/PI.md"],
        },
        "project_instructions": ["AGENTS.md", ".coding-scaffold/AGENTS.md"],
    }


def _yaml_scalar(value: str | None) -> str:
    """Quote ``value`` as a YAML scalar via JSON encoding (JSON is a YAML 1.2 subset)."""
    if value is None:
        return "null"
    return json.dumps(value)


def _routellm_yaml(routing: RoutingPlan) -> str:
    strong = routing.strong_model or routing.weak_model or "replace-me-strong-model"
    weak = routing.weak_model or strong
    endpoint = routing.local_endpoint or "http://127.0.0.1:11434/v1"
    return "\n".join(
        [
            "routers:",
            "  - mf",
            f"strong_model: {_yaml_scalar(strong)}",
            f"weak_model: {_yaml_scalar(weak)}",
            f"threshold: {ROUTELLM_MF_DEFAULT_THRESHOLD}",
            "providers:",
            "  local:",
            f"    base_url: {_yaml_scalar(endpoint)}",
            "",
        ]
    )


def _model_selection_json(routing: RoutingPlan) -> dict[str, object]:
    return {
        "default_mode": "recommend",
        "auto_mode": {
            "command": "coding-scaffold tools select-model --target . --mode auto --prompt '...'",
            "meaning": "select a route without asking each time; still prints the decision",
        },
        "routes": {
            "routine": {
                "model": routing.weak_model,
                "provider": "local-first",
                "use_for": ["small edits", "tests", "docs", "explanations", "formatting"],
            },
            "heavy-lift": {
                "model": routing.strong_model,
                "provider": routing.cloud_provider or "local",
                "model_family": routing.cloud_model_family or "local",
                "use_for": ["architecture", "security", "migrations", "reviews", "multi-file work"],
            },
        },
        "provider_abstraction": {
            "provider": "where the request is sent, for example Azure AI or OpenAI",
            "model_family": "what kind of model is behind it, for example OpenAI or Anthropic",
            "deployment": "provider-specific deployment name, kept outside prompts and skills",
        },
    }


def _scaffold_gitignore() -> str:
    return read_template("writers/scaffold.gitignore")


def _env_example() -> str:
    return read_template("writers/env.example")


def _credentials_example() -> dict[str, str]:
    return {
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "AZURE_OPENAI_API_KEY": "",
        "AZURE_OPENAI_ENDPOINT": "",
        "AZURE_OPENAI_DEPLOYMENT": "",
        "AZURE_AI_API_KEY": "",
        "AZURE_AI_ENDPOINT": "",
        "AZURE_AI_MODEL": "",
        "AZURE_AI_MODEL_FAMILY": "",
        "AZURE_AI_SERVICES_KEY": "",
        "AZURE_AI_SERVICES_ENDPOINT": "",
        "AZURE_COGNITIVE_SERVICES_KEY": "",
        "AZURE_COGNITIVE_SERVICES_ENDPOINT": "",
        "OPENROUTER_API_KEY": "",
        "GROQ_API_KEY": "",
        "GEMINI_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "GITHUB_TOKEN": "",
        "GH_TOKEN": "",
    }


def _credentials_md() -> str:
    return read_template("writers/credentials.md")


def _model_selection_md() -> str:
    return read_template("writers/model-selection.md")


def _tools_md() -> str:
    return read_template("writers/tools.md")


def _orchestration_json() -> dict[str, object]:
    return {
        "default_profile": "pair",
        "profiles": {
            "solo": "One agent, explicit checkpoints.",
            "pair": "Builder plus reviewer.",
            "team": "Explorer, planner, implementer, verifier with disjoint scopes.",
        },
        "routing": {
            "routine": "Use the selected local/routine model.",
            "heavy-lift": "Use the stronger routed model for architecture, security, and review.",
        },
    }


def _orchestration_md() -> str:
    return read_template("writers/orchestration.md")


def _skills_readme() -> str:
    return read_template("writers/skills-readme.md")


def _agents_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    return render_template(
        "writers/agents.md",
        language=intake.language,
        project_target=intake.project_target,
        existing_codebase=intake.existing_codebase,
        privacy=intake.privacy,
        mode=intake.mode,
        weak_model=routing.weak_model,
        strong_model=routing.strong_model,
        route_threshold=routing.route_threshold,
        cloud_provider=routing.cloud_provider or "none",
        cloud_model_family=routing.cloud_model_family or "none",
    )


def _getting_started_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    selected_tool = intake.tool or "opencode"
    setup_hint = (
        "Validate or install the selected coding environment with "
        f"`coding-scaffold setup tool --tool {selected_tool}`."
        if selected_tool != "manual"
        else "Use your manually selected coding environment and keep its config next to this scaffold."
    )
    return render_template(
        "writers/getting-started.md",
        setup_hint=setup_hint,
        language=intake.language,
        project_target=intake.project_target,
        privacy=intake.privacy,
        tool=intake.tool,
        mode=intake.mode,
        weak_model=routing.weak_model,
        strong_model=routing.strong_model,
    )


def _first_session_md() -> str:
    return read_template("writers/first-session.md")


def _skills_md() -> str:
    return read_template("writers/skills.md")


def _beginner_path_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    return render_template(
        "writers/beginner-path.md",
        weak_model=routing.weak_model,
        strong_model=routing.strong_model,
        privacy=intake.privacy,
    )
