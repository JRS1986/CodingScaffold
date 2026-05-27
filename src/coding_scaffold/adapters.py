from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .file_ops import collect_json, collect_text, write_json, write_text
from .model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from .template_resources import read_template, render_template
from .routing_io import load_routing_payload


@dataclass(frozen=True)
class AdapterResult:
    files: list[Path]
    skipped: list[Path]


def write_tool_adapter(target: Path, tool: str | list[str]) -> AdapterResult:
    from .intake import normalize_tools

    root = target.expanduser().resolve()
    files: list[Path] = []
    skipped: list[Path] = []
    routing = load_routing_payload(root)
    tools = normalize_tools(tool)
    for selected in tools:
        if selected == "opencode":
            result = _write_opencode(root, routing)
        elif selected == "claude-code":
            result = _write_claude_code(root, routing)
        elif selected == "codex":
            result = _write_codex(root, routing)
        elif selected == "openclaude":
            result = _write_openclaude(root, routing)
        elif selected == "hermes":
            result = _write_hermes(root, routing)
        elif selected == "pi":
            result = _write_pi(root, routing)
        else:
            result = AdapterResult([], [])
        files.extend(result.files)
        skipped.extend(result.skipped)
    return AdapterResult(files, skipped)


def write_route_backend(target: Path, backend: str) -> AdapterResult:
    if backend != "routellm":
        return AdapterResult([], [])
    root = target.expanduser().resolve()
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    routing = load_routing_payload(root)
    files = [
        write_text(scaffold / "ROUTELLM.md", _routellm_md(routing), overwrite=True),
        write_text(scaffold / "routellm.config.yaml", _routellm_yaml(routing), overwrite=True),
    ]
    return AdapterResult(files, [])


def write_workflow_backend(target: Path, backend: str) -> AdapterResult:
    if backend != "open-multi-agent":
        return AdapterResult([], [])
    root = target.expanduser().resolve()
    scaffold = root / ".coding-scaffold"
    examples = root / "examples" / "open-multi-agent"
    scaffold.mkdir(parents=True, exist_ok=True)
    examples.mkdir(parents=True, exist_ok=True)
    routing = load_routing_payload(root)
    files = [
        write_text(scaffold / "OPEN_MULTI_AGENT.md", _open_multi_agent_md(routing), overwrite=True),
        write_json(scaffold / "open-multi-agent.team.json", _open_multi_agent_team(routing)),
        write_text(examples / "team-coding-workflow.ts", _open_multi_agent_example(), overwrite=True),
    ]
    return AdapterResult(files, [])


def _write_opencode(root: Path, routing: dict[str, object]) -> AdapterResult:
    files: list[Path] = []
    skipped: list[Path] = []
    opencode_json = root / "opencode.json"
    config = {
        "$schema": "https://opencode.ai/config.json",
        "default_agent": "plan",
        "share": "disabled",
    }
    collect_text(files, skipped, opencode_json, json.dumps(config, indent=2) + "\n")

    agents = root / ".opencode" / "agents"
    commands = root / ".opencode" / "commands"
    collect_text(files, skipped, agents / "reviewer.md", _opencode_reviewer(routing))
    collect_text(files, skipped, agents / "explorer.md", _opencode_explorer())
    collect_text(files, skipped, agents / "implementer.md", _opencode_implementer(routing))
    collect_text(files, skipped, commands / "first-session.md", _opencode_first_session())
    collect_text(files, skipped, commands / "agentic-change.md", _opencode_agentic_change())
    collect_text(files, skipped, commands / "knowledge-propose.md", _knowledge_propose_command())
    collect_text(files, skipped, commands / "review.md", _opencode_review_command())
    collect_text(files, skipped, commands / "recheck-route.md", _opencode_recheck_route())
    return AdapterResult(files, skipped)


def _write_claude_code(root: Path, routing: dict[str, object]) -> AdapterResult:
    files: list[Path] = []
    skipped: list[Path] = []
    collect_text(files, skipped, root / "CLAUDE.md", _claude_md(routing))
    collect_json(files, skipped, root / ".claude" / "settings.json", _claude_settings())
    collect_text(
        files,
        skipped,
        root / ".claude" / "commands" / "first-session.md",
        _claude_first_session(),
    )
    collect_text(
        files,
        skipped,
        root / ".claude" / "commands" / "agentic-change.md",
        _claude_agentic_change(),
    )
    collect_text(
        files,
        skipped,
        root / ".claude" / "commands" / "knowledge-propose.md",
        _knowledge_propose_command(),
    )
    collect_text(files, skipped, root / ".claude" / "agents" / "reviewer.md", _claude_reviewer(routing))
    return AdapterResult(files, skipped)


def _write_codex(root: Path, routing: dict[str, object]) -> AdapterResult:
    files: list[Path] = []
    skipped: list[Path] = []
    collect_text(files, skipped, root / "AGENTS.md", _codex_agents_md(routing))
    collect_text(files, skipped, root / ".codex" / "skills" / "README.md", _codex_skills_readme())
    collect_text(files, skipped, root / ".codex" / "skills" / "first-session.md", _codex_first_session_skill())
    collect_text(files, skipped, root / ".codex" / "skills" / "knowledge-propose.md", _knowledge_propose_command())
    collect_text(files, skipped, root / ".codex" / "config.toml", _codex_config_toml())
    return AdapterResult(files, skipped)


def _write_openclaude(root: Path, routing: dict[str, object]) -> AdapterResult:
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "OPENCLAUDE.md"
    return AdapterResult([write_text(path, _openclaude_md(routing), overwrite=True)], [])


def _write_hermes(root: Path, routing: dict[str, object]) -> AdapterResult:
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "HERMES.md"
    return AdapterResult([write_text(path, _hermes_md(routing), overwrite=True)], [])


def _write_pi(root: Path, routing: dict[str, object]) -> AdapterResult:
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "PI.md"
    return AdapterResult([write_text(path, _pi_md(routing), overwrite=True)], [])


def _model(routing: dict[str, object], key: str, fallback: str) -> str:
    value = routing.get(key)
    return str(value) if value else fallback


def _opencode_reviewer(routing: dict[str, object]) -> str:
    model = _model(routing, "strong_model", "use-global-model")
    return render_template(
        "adapters/opencode-reviewer.md",
        model=model,
    )


def _opencode_explorer() -> str:
    return read_template("adapters/opencode-explorer.md")


def _opencode_implementer(routing: dict[str, object]) -> str:
    model = _model(routing, "weak_model", "use-global-model")
    return render_template(
        "adapters/opencode-implementer.md",
        model=model,
    )


def _opencode_first_session() -> str:
    return read_template("adapters/opencode-first-session.md")


def _opencode_agentic_change() -> str:
    return read_template("adapters/opencode-agentic-change.md")


def _opencode_review_command() -> str:
    return read_template("adapters/opencode-review-command.md")


def _opencode_recheck_route() -> str:
    return read_template("adapters/opencode-recheck-route.md")


def _knowledge_propose_command() -> str:
    return read_template("adapters/knowledge-propose.md")


def _claude_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return render_template(
        "adapters/claude.md",
        weak=weak,
        strong=strong,
    )

def _claude_settings() -> dict[str, object]:
    return {
        "permissions": {
            "defaultMode": "ask",
            "deny": [
                ".coding-scaffold/.env.local",
                ".coding-scaffold/credentials.local.json",
                "**/.env",
                "**/.env.*",
            ],
        },
        "includeCoAuthoredBy": False,
    }


def _claude_first_session() -> str:
    return read_template("adapters/claude-first-session.md")

def _claude_agentic_change() -> str:
    return read_template("adapters/claude-agentic-change.md")


def _claude_reviewer(routing: dict[str, object]) -> str:
    model = _model(routing, "strong_model", "use-current-claude-code-model")
    return render_template(
        "adapters/claude-reviewer.md",
        model=model,
    )


def _codex_agents_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return render_template(
        "adapters/codex-agents.md",
        weak=weak,
        strong=strong,
    )


def _codex_skills_readme() -> str:
    return read_template("adapters/codex-skills-readme.md")


def _codex_first_session_skill() -> str:
    return read_template("adapters/codex-first-session.md")


def _codex_config_toml() -> str:
    return read_template("adapters/codex-config.toml")


def _openclaude_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return render_template(
        "adapters/openclaude.md",
        weak=weak,
        strong=strong,
    )


def _hermes_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return render_template(
        "adapters/hermes.md",
        weak=weak,
        strong=strong,
    )


def _pi_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return render_template(
        "adapters/pi.md",
        weak=weak,
        strong=strong,
    )

def _yaml_scalar(value: str | None) -> str:
    """Quote ``value`` as a YAML scalar via JSON encoding (JSON is a YAML 1.2 subset)."""
    if value is None:
        return "null"
    return json.dumps(value)


def _routellm_yaml(routing: dict[str, object]) -> str:
    strong = _model(routing, "strong_model", "replace-me-strong-model")
    weak = _model(routing, "weak_model", "replace-me-weak-model")
    return "\n".join(
        [
            "routers:",
            "  - mf",
            f"strong_model: {_yaml_scalar(strong)}",
            f"weak_model: {_yaml_scalar(weak)}",
            f"threshold: {ROUTELLM_MF_DEFAULT_THRESHOLD}",
            "",
        ]
    )


def _routellm_md(routing: dict[str, object]) -> str:
    strong = _model(routing, "strong_model", "replace-me-strong-model")
    weak = _model(routing, "weak_model", "replace-me-weak-model")
    return render_template(
        "adapters/routellm.md",
        strong=strong,
        weak=weak,
        threshold=ROUTELLM_MF_DEFAULT_THRESHOLD,
    )


def _open_multi_agent_team(routing: dict[str, object]) -> dict[str, object]:
    routine = _model(routing, "weak_model", "choose-routine-model")
    heavy = _model(routing, "strong_model", "choose-heavy-lift-model")
    return {
        "backend": "open-multi-agent",
        "intent": "Turn validated local agentic workflows into repeatable TypeScript automation.",
        "install": "npm install @jackchen_me/open-multi-agent",
        "agents": [
            {
                "name": "explorer",
                "model": routine,
                "tools": ["file_read", "grep", "glob"],
                "responsibility": "Map relevant files, commands, dependencies, and risks.",
            },
            {
                "name": "planner",
                "model": heavy,
                "tools": ["file_read", "grep"],
                "responsibility": "Break the goal into a small task DAG with explicit verification.",
            },
            {
                "name": "implementer",
                "model": routine,
                "tools": ["bash", "file_read", "file_write", "file_edit", "grep"],
                "responsibility": "Make bounded edits and run narrow checks.",
            },
            {
                "name": "reviewer",
                "model": heavy,
                "tools": ["file_read", "grep"],
                "responsibility": "Review for regressions, missing tests, security, and maintainability.",
            },
        ],
        "recommended_flow": [
            "Validate the workflow interactively in OpenCode first.",
            "Create or update a project skill.",
            "Generate this backend when the workflow is worth repeating.",
            "Run planOnly before letting agents execute.",
            "Review traces and outputs before adopting in CI or backend automation.",
        ],
    }


def _open_multi_agent_md(routing: dict[str, object]) -> str:
    routine = _model(routing, "weak_model", "choose-routine-model")
    heavy = _model(routing, "strong_model", "choose-heavy-lift-model")
    return render_template(
        "adapters/open-multi-agent.md",
        routine=routine,
        heavy=heavy,
    )


def _open_multi_agent_example() -> str:
    return read_template("adapters/open-multi-agent-example.ts")
