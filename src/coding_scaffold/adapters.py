from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdapterResult:
    files: list[Path]
    skipped: list[Path]


def write_tool_adapter(target: Path, tool: str) -> AdapterResult:
    root = target.expanduser().resolve()
    files: list[Path] = []
    skipped: list[Path] = []
    routing = _read_routing(root)
    tools = ["opencode", "openclaude"] if tool == "both" else [tool]
    for selected in tools:
        if selected == "opencode":
            result = _write_opencode(root, routing)
        elif selected == "openclaude":
            result = _write_openclaude(root, routing)
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
    routing = _read_routing(root)
    files = [
        _write(scaffold / "ROUTELLM.md", _routellm_md(routing), overwrite=True),
        _write(scaffold / "routellm.config.yaml", _routellm_yaml(routing), overwrite=True),
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
    _collect_write(files, skipped, opencode_json, json.dumps(config, indent=2) + "\n")

    agents = root / ".opencode" / "agents"
    commands = root / ".opencode" / "commands"
    _collect_write(files, skipped, agents / "reviewer.md", _opencode_reviewer(routing))
    _collect_write(files, skipped, agents / "explorer.md", _opencode_explorer())
    _collect_write(files, skipped, agents / "implementer.md", _opencode_implementer(routing))
    _collect_write(files, skipped, commands / "first-session.md", _opencode_first_session())
    _collect_write(files, skipped, commands / "review.md", _opencode_review_command())
    _collect_write(files, skipped, commands / "route-42.md", _opencode_route_42())
    return AdapterResult(files, skipped)


def _write_openclaude(root: Path, routing: dict[str, object]) -> AdapterResult:
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "OPENCLAUDE.md"
    return AdapterResult([_write(path, _openclaude_md(routing), overwrite=True)], [])


def _collect_write(files: list[Path], skipped: list[Path], path: Path, content: str) -> None:
    if path.exists():
        skipped.append(path)
        return
    files.append(_write(path, content, overwrite=False))


def _write(path: Path, content: str, overwrite: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if overwrite or not path.exists():
        path.write_text(content, encoding="utf-8")
    return path


def _read_routing(root: Path) -> dict[str, object]:
    path = root / ".coding-scaffold" / "routing.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _model(routing: dict[str, object], key: str, fallback: str) -> str:
    value = routing.get(key)
    return str(value) if value else fallback


def _opencode_reviewer(routing: dict[str, object]) -> str:
    model = _model(routing, "strong_model", "use-global-model")
    return f"""---
description: Reviews code for regressions, missing tests, security issues, and maintainability.
mode: subagent
model: {model}
tools:
  write: false
  edit: false
---

You are the review agent. Lead with findings ordered by severity. Reference files and lines when
possible. Do not modify files. Focus on behavior, test coverage, security, data handling, and
maintainer clarity.
"""


def _opencode_explorer() -> str:
    return """---
description: Read-only codebase exploration and context loading.
mode: subagent
tools:
  write: false
  edit: false
---

You are the explorer agent. Map relevant files, commands, dependencies, and risks. Do not edit.
Return concise findings and the smallest useful next context to inspect.
"""


def _opencode_implementer(routing: dict[str, object]) -> str:
    model = _model(routing, "weak_model", "use-global-model")
    return f"""---
description: Implements small, bounded changes and runs narrow verification.
mode: subagent
model: {model}
---

You are the implementer agent. Own only the assigned files or module. Keep edits small, run the
narrowest meaningful check, and summarize changed files plus residual risk.
"""


def _opencode_first_session() -> str:
    return """Inspect this repository before editing. Identify the language, package manager, run command,
test command, main source directories, and the first safe improvement. Do not modify files yet.
"""


def _opencode_review_command() -> str:
    return """Review the current change for regressions, missing tests, security issues, and unclear behavior.
Findings first. Do not edit files unless explicitly asked after the review.
"""


def _opencode_route_42() -> str:
    return """ROUTE-42: the current answer or plan feels off. Re-inspect the relevant files, state assumptions,
choose whether this should use the routine or heavy-lift model, and propose the smallest next step.
"""


def _openclaude_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return f"""# OpenClaude Adapter

OpenClaude support is intentionally lightweight because the project moves quickly. Use this as a
profile checklist rather than a locked config format.

## Install

```bash
npm install -g @gitlawb/openclaude
openclaude
```

## Suggested Profiles

- Routine/editing model: `{weak}`
- Heavy-lift/review model: `{strong}`
- Local endpoint: use Ollama or another OpenAI-compatible endpoint when available.

Inside OpenClaude, run `/provider` and configure the provider profile to match these values. Keep
real API keys in `.coding-scaffold/.env.local` or the tool's secure login flow, not in committed
files.
"""


def _routellm_yaml(routing: dict[str, object]) -> str:
    strong = _model(routing, "strong_model", "replace-me-strong-model")
    weak = _model(routing, "weak_model", "replace-me-weak-model")
    return "\n".join(
        [
            "routers:",
            "  - mf",
            f"strong_model: {strong}",
            f"weak_model: {weak}",
            "threshold: 0.11593",
            "",
        ]
    )


def _routellm_md(routing: dict[str, object]) -> str:
    strong = _model(routing, "strong_model", "replace-me-strong-model")
    weak = _model(routing, "weak_model", "replace-me-weak-model")
    return f"""# RouteLLM

RouteLLM is optional. Use it when you want an OpenAI-compatible local routing server that decides
between a weak/routine model and a strong/heavy-lift model.

## When It Helps

- You have a cheap or local routine model and a stronger model.
- You want tools to call one endpoint while routing happens behind the scenes.
- You want to experiment with cost/quality thresholds.

## Install

```bash
python -m pip install "routellm[serve,eval]"
```

## Important Caveat

The commonly recommended `mf` router currently requires `OPENAI_API_KEY` for embeddings, even when
one of the routed models is local. Keep that key local in `.coding-scaffold/.env.local`.

## Start A Router Server

```bash
python -m routellm.openai_server \\
  --routers mf \\
  --strong-model {strong} \\
  --weak-model {weak}
```

RouteLLM's OpenAI-compatible server defaults to port `6060`. Point OpenCode, OpenClaude, or another
OpenAI-compatible client at that endpoint, then use a model value such as `router-mf-0.11593`.
"""
