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
    _collect(files, skipped, knowledge / "sharing" / "README.md", _hierarchy_readme())
    _collect(
        files,
        skipped,
        knowledge / "team" / "README.md",
        _layer_readme("team", ["project context", "local prompts", "first skill drafts", "session findings"]),
    )
    _collect(
        files,
        skipped,
        knowledge / "department" / "README.md",
        _layer_readme(
            "department",
            ["reusable runbooks", "system patterns", "validated agent roles", "department decisions"],
        ),
    )
    _collect(
        files,
        skipped,
        knowledge / "unit" / "README.md",
        _layer_readme(
            "unit",
            ["domain vocabulary", "reference architecture", "shared provider policy", "tool defaults"],
        ),
    )
    _collect(
        files,
        skipped,
        knowledge / "company" / "README.md",
        _layer_readme(
            "company",
            ["approved standards", "approved skills", "approved agents", "security and privacy rules"],
        ),
    )
    _collect(files, skipped, knowledge / "glossary.md", _glossary_template())
    _collect(files, skipped, knowledge / "links.md", _links_template())
    _collect(files, skipped, knowledge / "sync.md", _sync_template(shared_remote))
    if backend == "obsidian":
        _collect_obsidian_files(files, skipped, knowledge)
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
        "layers": {
            "team": ".coding-scaffold/knowledge/team",
            "department": ".coding-scaffold/knowledge/department",
            "unit": ".coding-scaffold/knowledge/unit",
            "company": ".coding-scaffold/knowledge/company",
        },
        "maturity_levels": ["draft", "validated", "recommended", "standard"],
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
        "obsidian": {
            "optional": True,
            "vault_path": ".coding-scaffold/knowledge",
            "open": "Open .coding-scaffold/knowledge as an Obsidian vault.",
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
    obsidian_line = (
        "This scaffold also generated Obsidian vault settings, templates, and a start page."
        if backend == "obsidian"
        else "Run `coding-scaffold knowledge --backend obsidian` later if you want an Obsidian vault."
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

## Hierarchical Sharing

Use folders for audience and ownership before adding remote complexity:

- `knowledge/team/`: project context, local prompts, first skill drafts, session findings.
- `knowledge/department/`: reusable runbooks, system patterns, validated agent roles.
- `knowledge/unit/`: domain vocabulary, reference architecture, shared provider policy.
- `knowledge/company/`: standards, approved skills, approved agents, security and privacy rules.

Use frontmatter on promoted notes:

```yaml
scope: team
maturity: draft
owner: platform-ai
tags: [testing, opencode]
source_project: example-service
reviewed_by: ""
expires: 2026-12-31
```

Promote knowledge upward by pull request: `draft` -> `validated` -> `recommended` -> `standard`.
Use separate Git remotes only when access boundaries differ. If the same audience can read every
layer, one repo with folders, tags, and CODEOWNERS is usually easier to maintain.

## Shared Repo

Use a normal GitHub or GitLab repository when the team wants shared memory:

```bash
git clone <team-knowledge-repo> .coding-scaffold/knowledge
```

or keep this folder in the project repo if the knowledge is project-specific and safe to share.

## Optional Obsidian

{obsidian_line}

Obsidian is useful when humans want backlinks, graph navigation, templates, and a pleasant reading
surface. It still uses Markdown files, so Git remains the review and sharing mechanism.

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
- [Hierarchical sharing](sharing/README.md)
- [Glossary](glossary.md)
- [Links](links.md)
- [Sync guide](sync.md)

## High-Signal Notes

Add links to the notes that every agent should read before working in this project.
"""


def _hierarchy_readme() -> str:
    return """# Hierarchical Knowledge Sharing

Use this structure to keep useful knowledge close to the right audience while still allowing mature
patterns to move upward.

## Scopes

- `team`: project facts, local prompts, drafts, and session discoveries.
- `department`: reusable runbooks, validated skills, system-specific guidance.
- `unit`: domain vocabulary, reference architecture, shared provider and tool policy.
- `company`: approved standards, approved agents, privacy rules, and defaults.

## Maturity

- `draft`: captured from real work but not reviewed.
- `validated`: used in at least one project and reviewed by peers.
- `recommended`: useful across multiple teams or systems.
- `standard`: approved default for the scope.

## Promotion

Promote upward by pull request. Keep the old note linked until the promoted version is trusted.
Never promote secrets, customer data, unreleased strategy, or private incident details into broader
layers.

Use multiple Git remotes only when access differs. Otherwise prefer one shared repo with folders,
frontmatter, tags, and CODEOWNERS.
"""


def _layer_readme(scope: str, examples: list[str]) -> str:
    return f"""# {scope.title()} Knowledge

Audience: `{scope}`

Use this layer for:

{chr(10).join(f"- {example}" for example in examples)}

Recommended frontmatter:

```yaml
scope: {scope}
maturity: draft
owner: ""
tags: []
source_project: ""
reviewed_by: ""
expires: ""
```
"""


def _collect_obsidian_files(files: list[Path], skipped: list[Path], knowledge: Path) -> None:
    _collect(files, skipped, knowledge / "00 Start Here.md", _obsidian_start_here())
    _collect(files, skipped, knowledge / "10 Decisions" / "README.md", _obsidian_decisions_readme())
    _collect(files, skipped, knowledge / "20 Skills" / "README.md", _obsidian_skills_readme())
    _collect(files, skipped, knowledge / "30 Agents" / "README.md", _obsidian_agents_readme())
    _collect(files, skipped, knowledge / "40 Sessions" / "README.md", _obsidian_sessions_readme())
    _collect(files, skipped, knowledge / "50 Glossary" / "README.md", _obsidian_glossary_readme())
    _collect(files, skipped, knowledge / "90 Inbox" / "README.md", _obsidian_inbox_readme())
    _collect(files, skipped, knowledge / "Templates" / "Decision.md", _obsidian_decision_template())
    _collect(files, skipped, knowledge / "Templates" / "Skill.md", _obsidian_skill_template())
    _collect(files, skipped, knowledge / "Templates" / "Agent.md", _obsidian_agent_template())
    _collect(files, skipped, knowledge / ".obsidian" / "app.json", _obsidian_app_json())
    _collect(files, skipped, knowledge / ".obsidian" / "graph.json", _obsidian_graph_json())
    _collect(files, skipped, knowledge / ".obsidian" / "templates.json", _obsidian_templates_json())


def _obsidian_start_here() -> str:
    return """---
type: index
tags: [coding-scaffold, team-memory]
---
# Start Here

This vault is the human-readable team memory for agentic coding.

## Maps

- [[10 Decisions/README|Decisions]]
- [[20 Skills/README|Skills]]
- [[30 Agents/README|Agents]]
- [[40 Sessions/README|Sessions]]
- [[50 Glossary/README|Glossary]]
- [[90 Inbox/README|Inbox]]

## Operating Rule

Markdown is the source of truth. Obsidian is the reading and linking layer. Review important
knowledge changes in Git before agents treat them as defaults.
"""


def _obsidian_decisions_readme() -> str:
    return """---
type: map
tags: [decisions]
---
# Decisions

Use decision notes for architecture, model routing, tool choices, data handling, and workflow
conventions. Link notes back to [[00 Start Here]] and to related skills or agents.
"""


def _obsidian_skills_readme() -> str:
    return """---
type: map
tags: [skills]
---
# Skills

Use this map for skill explanations, ownership, examples, and review history. Runnable skill files
still live in `.coding-scaffold/skills/`.
"""


def _obsidian_agents_readme() -> str:
    return """---
type: map
tags: [agents]
---
# Agents

Document trusted agent roles here. Link each role to the skills, decisions, and verification habits
it depends on.
"""


def _obsidian_sessions_readme() -> str:
    return """---
type: map
tags: [sessions]
---
# Sessions

Capture durable findings from useful agentic coding sessions. Promote repeatable patterns into
[[20 Skills/README|Skills]] or [[30 Agents/README|Agents]].
"""


def _obsidian_glossary_readme() -> str:
    return """---
type: map
tags: [glossary]
---
# Glossary

Add project terms, internal systems, acronyms, and domain language that agents should not
rediscover.
"""


def _obsidian_inbox_readme() -> str:
    return """---
type: inbox
tags: [inbox]
---
# Inbox

Drop rough notes here first. Move them into decisions, skills, agents, sessions, or glossary once
they become durable.
"""


def _obsidian_decision_template() -> str:
    return """---
type: decision
status: proposed
tags: [decision]
---
# Decision: Title

Related: [[00 Start Here]]

## Context

## Decision

## Consequences

## Agent Notes
"""


def _obsidian_skill_template() -> str:
    return """---
type: skill
status: draft
tags: [skill]
---
# Skill: Title

Related agents:

## When To Use

## Workflow

## Verification

## Maintenance Notes
"""


def _obsidian_agent_template() -> str:
    return """---
type: agent
status: draft
tags: [agent]
---
# Agent: Title

Related skills:

## Responsibility

## Allowed Context

## Write Scope

## Handoff Rules
"""


def _obsidian_app_json() -> str:
    return json.dumps(
        {
            "attachmentFolderPath": "Attachments",
            "alwaysUpdateLinks": True,
            "newFileLocation": "folder",
            "newFileFolderPath": "90 Inbox",
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def _obsidian_graph_json() -> str:
    return json.dumps(
        {
            "collapse-filter": False,
            "search": "",
            "showAttachments": False,
            "showOrphans": True,
            "showTags": True,
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def _obsidian_templates_json() -> str:
    return json.dumps({"folder": "Templates"}, indent=2, sort_keys=True) + "\n"


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
