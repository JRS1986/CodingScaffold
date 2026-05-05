from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeResult:
    files: list[Path]
    skipped: list[Path]


def write_knowledge_base(
    target: Path,
    backend: str = "markdown",
    shared_remote: str | None = None,
    adapter: str | None = None,
) -> KnowledgeResult:
    root = target.expanduser().resolve()
    scaffold = root / ".coding-scaffold"
    knowledge = scaffold / "knowledge"
    scaffold.mkdir(parents=True, exist_ok=True)
    knowledge.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    skipped: list[Path] = []
    _write(files, scaffold / "knowledge.json", _knowledge_json(backend, shared_remote), overwrite=True)
    _write(files, scaffold / "KNOWLEDGE.md", _knowledge_guide(backend, shared_remote), overwrite=True)
    _collect(files, skipped, knowledge / "README.md", _knowledge_readme(backend, shared_remote))
    _collect(files, skipped, knowledge / "INDEX.md", _knowledge_index())
    _collect(files, skipped, knowledge / "decisions" / "README.md", _decisions_readme())
    _collect(files, skipped, knowledge / "decisions" / "0001-decision-template.md", _decision_template())
    _collect(files, skipped, knowledge / "sessions" / "session-template.md", _session_template())
    _collect(files, skipped, knowledge / "skills" / "README.md", _shared_skills_readme())
    _collect(files, skipped, knowledge / "agents" / "README.md", _shared_agents_readme())
    _collect(files, skipped, knowledge / "glossary.md", _glossary_template())
    _collect(files, skipped, knowledge / "links.md", _links_template())
    _collect(files, skipped, knowledge / "sync.md", _sync_template(shared_remote))
    if backend == "mempalace":
        _collect(files, skipped, knowledge / "mempalace.md", _mempalace_template())
    if adapter == "opencode":
        _collect(
            files,
            skipped,
            root / ".opencode" / "commands" / "capture-knowledge.md",
            _opencode_capture_knowledge(),
        )
        _collect(
            files,
            skipped,
            root / ".opencode" / "commands" / "share-agent-pattern.md",
            _opencode_share_agent_pattern(),
        )
    return KnowledgeResult(files, skipped)


def _write(files: list[Path], path: Path, payload: str, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if overwrite or not path.exists():
        path.write_text(payload, encoding="utf-8")
    files.append(path)


def _collect(files: list[Path], skipped: list[Path], path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        skipped.append(path)
        return
    path.write_text(payload, encoding="utf-8")
    files.append(path)


def _knowledge_json(backend: str, shared_remote: str | None) -> str:
    payload = {
        "backend": backend,
        "path": ".coding-scaffold/knowledge",
        "shared_remote": shared_remote,
        "shareable_paths": [
            ".coding-scaffold/knowledge",
            ".coding-scaffold/skills",
            ".opencode/agents",
            ".opencode/commands",
        ],
        "entrypoints": {
            "index": ".coding-scaffold/knowledge/INDEX.md",
            "decisions": ".coding-scaffold/knowledge/decisions/",
            "skills": ".coding-scaffold/knowledge/skills/",
            "agents": ".coding-scaffold/knowledge/agents/",
        },
        "mempalace": {
            "optional": True,
            "install": "python -m pip install mempalace",
            "mine": "mempalace mine .coding-scaffold/knowledge",
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _knowledge_guide(backend: str, shared_remote: str | None) -> str:
    remote = shared_remote or "add a GitHub/GitLab repository URL when the team is ready"
    mempalace_line = (
        "This scaffold also generated `knowledge/mempalace.md` for optional MemPalace indexing."
        if backend == "mempalace"
        else "Run `coding-scaffold knowledge --backend mempalace` later if you want MemPalace notes."
    )
    return f"""# Team Knowledge Base

The knowledge base is the shared memory for AI-enabled coding: decisions, project facts, useful
agent patterns, validated skills, session notes, and links to source-of-truth docs.

Default backend: `{backend}`
Shared remote: `{remote}`

## Recommended Use

1. Capture decisions as Markdown in `knowledge/decisions/`.
2. Link the most important notes from `knowledge/INDEX.md`.
3. Promote working prompts into `.coding-scaffold/skills/`.
4. Promote reliable agent patterns into `.opencode/agents/` or the tool-specific adapter.
5. Review knowledge changes like code.

## Shared Repo

Use a normal GitHub or GitLab repository when the team wants shared memory:

```bash
git clone <team-knowledge-repo> .coding-scaffold/knowledge
```

or keep this folder in the project repo if the knowledge is project-specific and safe to share.

## Optional MemPalace

{mempalace_line}

MemPalace is useful when the Markdown corpus gets large enough that semantic retrieval matters.
Keep Markdown as the source of truth; use memory tooling as an index, not as the only copy.
"""


def _knowledge_readme(backend: str, shared_remote: str | None) -> str:
    remote = shared_remote or "not configured yet"
    return f"""# Knowledge Base

This folder is the project or team memory for agentic coding.

- Backend: `{backend}`
- Shared remote: `{remote}`
- Start here: `INDEX.md`

Keep notes short, linked, and reviewable. The best entries explain what changed, why it matters,
where the source lives, and which skill or agent should use the knowledge.
"""


def _knowledge_index() -> str:
    return """# Knowledge Index

## Start Here

- [Decision records](decisions/README.md)
- [Session notes](sessions/session-template.md)
- [Shared skills](skills/README.md)
- [Shared agents](agents/README.md)
- [Glossary](glossary.md)
- [Links](links.md)
- [Sync guide](sync.md)

## High-Signal Notes

Add links to the notes that every agent should read before working in this project.
"""


def _decisions_readme() -> str:
    return """# Decision Records

Use one Markdown file per decision. Keep the file linked from `../INDEX.md` when it is still
important for everyday engineering work.
"""


def _decision_template() -> str:
    return """# Decision: Short Title

Date: YYYY-MM-DD
Status: proposed | accepted | superseded

## Context

What forced this decision?

## Decision

What did the team decide?

## Consequences

What becomes easier, harder, or riskier?

## Agent Notes

What should coding agents remember before changing this area?
"""


def _session_template() -> str:
    return """# Session: Short Title

Date: YYYY-MM-DD
Participants: human, agent/tool names

## Goal

What were we trying to do?

## Useful Findings

- Finding:
- Source:

## Decisions Or Follow-Ups

- Decision:
- Follow-up:

## Skills Or Agents To Update

- Skill:
- Agent:
"""


def _shared_skills_readme() -> str:
    return """# Shared Skills

Use this folder to discuss and link skills that should become team standards. The runnable skill
files live in `.coding-scaffold/skills/`; this folder explains why they exist, when to use them,
and who maintains them.
"""


def _shared_agents_readme() -> str:
    return """# Shared Agents

Use this folder to document agent roles the team trusts: explorer, reviewer, migration planner,
frontend verifier, release checker, and project-specific specialists.

Runnable OpenCode agents live in `.opencode/agents/`; this folder is the team-readable catalog and
review history.
"""


def _glossary_template() -> str:
    return """# Glossary

Add project terms, service names, acronyms, internal tools, and domain language that agents should
not have to rediscover.
"""


def _links_template() -> str:
    return """# Links

- Architecture:
- Runbooks:
- API docs:
- Dashboards:
- Repositories:
- Team conventions:
"""


def _sync_template(shared_remote: str | None) -> str:
    remote = shared_remote or "<team-knowledge-repo>"
    return f"""# Sync Guide

Use Git for shared team memory.

```bash
git clone {remote} .coding-scaffold/knowledge
```

If the knowledge base lives inside the project repository, review changes in normal pull requests.
If it lives in a separate repository, keep it small and sync it before agentic coding sessions.

Suggested review rule: decisions, skills, and agent role changes need human review before they
become defaults.
"""


def _mempalace_template() -> str:
    return """# Optional MemPalace Index

MemPalace can index this Markdown knowledge base for local semantic retrieval and MCP-compatible
memory workflows.

Install:

```bash
python -m pip install mempalace
```

Initialize and mine the knowledge base:

```bash
mempalace init .
mempalace mine .coding-scaffold/knowledge
mempalace search "why did we choose this deployment model"
```

Keep Markdown as the source of truth and use MemPalace as an index. Before installing, verify you
are using the official MemPalace package, GitHub repository, or documentation site.
"""


def _opencode_capture_knowledge() -> str:
    return """Capture useful project knowledge from the current session.

Read `.coding-scaffold/KNOWLEDGE.md` and `.coding-scaffold/knowledge/INDEX.md`. Propose one small
Markdown note or decision record that preserves durable knowledge from this session. Do not write
secrets. Prefer links to source files and commands over vague summaries.
"""


def _opencode_share_agent_pattern() -> str:
    return """Turn a useful agent behavior into shared team knowledge.

Inspect `.coding-scaffold/knowledge/agents/README.md`, `.opencode/agents/`, and the recent session
context. Propose a small documented agent role or update an existing one. Include when to use it,
what it may read or edit, verification expectations, and handoff rules.
"""
