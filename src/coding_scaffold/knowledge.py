from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .file_ops import collect_text, write_text

STALE_REVIEW_DAYS = 180


@dataclass(frozen=True)
class KnowledgeResult:
    files: list[Path]
    skipped: list[Path]


@dataclass(frozen=True)
class KnowledgeStatus:
    counts: dict[str, dict[str, int]]
    warnings: list[str]
    raw_files: int = 0
    curated_files: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "counts": self.counts,
            "warnings": self.warnings,
            "raw_files": self.raw_files,
            "curated_files": self.curated_files,
        }


@dataclass(frozen=True)
class KnowledgeDistillResult:
    created: list[Path]
    updated: list[Path]
    skipped: list[Path]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "created": [str(path) for path in self.created],
            "updated": [str(path) for path in self.updated],
            "skipped": [str(path) for path in self.skipped],
            "warnings": self.warnings,
        }


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
    files.append(write_text(scaffold / "knowledge.json", _knowledge_json(backend, shared_remote), overwrite=True))
    files.append(write_text(scaffold / "KNOWLEDGE.md", _knowledge_guide(backend, shared_remote), overwrite=True))
    collect_text(files, skipped, knowledge / "README.md", _knowledge_readme(backend, shared_remote))
    collect_text(files, skipped, knowledge / "INDEX.md", _knowledge_index())
    collect_text(files, skipped, knowledge / "raw" / "README.md", _raw_readme())
    collect_text(files, skipped, knowledge / "raw" / "meetings" / "README.md", _raw_folder_readme("meetings"))
    collect_text(files, skipped, knowledge / "raw" / "decisions" / "README.md", _raw_folder_readme("decisions"))
    collect_text(files, skipped, knowledge / "raw" / "code-notes" / "README.md", _raw_folder_readme("code notes"))
    collect_text(files, skipped, knowledge / "raw" / "incidents" / "README.md", _raw_folder_readme("incidents"))
    collect_text(files, skipped, knowledge / "wiki" / "architecture.md", _curated_wiki_page("architecture"))
    collect_text(files, skipped, knowledge / "wiki" / "setup.md", _curated_wiki_page("setup"))
    collect_text(files, skipped, knowledge / "wiki" / "testing.md", _curated_wiki_page("testing"))
    collect_text(files, skipped, knowledge / "wiki" / "deployment.md", _curated_wiki_page("deployment"))
    collect_text(files, skipped, knowledge / "wiki" / "domain-language.md", _curated_wiki_page("domain language"))
    collect_text(files, skipped, knowledge / "wiki" / "decisions.md", _curated_wiki_page("decisions"))
    collect_text(files, skipped, knowledge / "decisions" / "README.md", _decisions_readme())
    collect_text(files, skipped, knowledge / "decisions" / "0001-decision-template.md", _decision_template())
    collect_text(files, skipped, knowledge / "sessions" / "session-template.md", _session_template())
    collect_text(files, skipped, knowledge / "skills" / "README.md", _shared_skills_readme())
    collect_text(files, skipped, knowledge / "agents" / "README.md", _shared_agents_readme())
    collect_text(files, skipped, knowledge / "sharing" / "README.md", _hierarchy_readme())
    collect_text(
        files,
        skipped,
        knowledge / "team" / "README.md",
        _layer_readme("team", ["project context", "local prompts", "first skill drafts", "session findings"]),
    )
    collect_text(
        files,
        skipped,
        knowledge / "department" / "README.md",
        _layer_readme(
            "department",
            ["reusable runbooks", "system patterns", "validated agent roles", "department decisions"],
        ),
    )
    collect_text(
        files,
        skipped,
        knowledge / "unit" / "README.md",
        _layer_readme(
            "unit",
            ["domain vocabulary", "reference architecture", "shared provider policy", "tool defaults"],
        ),
    )
    collect_text(
        files,
        skipped,
        knowledge / "company" / "README.md",
        _layer_readme(
            "company",
            ["approved standards", "approved skills", "approved agents", "security and privacy rules"],
        ),
    )
    collect_text(files, skipped, knowledge / "glossary.md", _glossary_template())
    collect_text(files, skipped, knowledge / "links.md", _links_template())
    collect_text(files, skipped, knowledge / "sync.md", _sync_template(shared_remote))
    if backend == "obsidian":
        _collect_obsidian_files(files, skipped, knowledge)
    if backend == "foam":
        _collect_foam_files(files, skipped, knowledge)
    if backend == "mempalace":
        collect_text(files, skipped, knowledge / "mempalace.md", _mempalace_template())
    if adapter == "opencode":
        collect_text(
            files,
            skipped,
            root / ".opencode" / "commands" / "capture-knowledge.md",
            _opencode_capture_knowledge(),
        )
        collect_text(
            files,
            skipped,
            root / ".opencode" / "commands" / "share-agent-pattern.md",
            _opencode_share_agent_pattern(),
        )
    return KnowledgeResult(files, skipped)


def inspect_knowledge_status(target: Path) -> KnowledgeStatus:
    root = target.expanduser().resolve()
    knowledge = root / ".coding-scaffold" / "knowledge"
    counts: dict[str, dict[str, int]] = {}
    warnings: list[str] = []
    raw_files = 0
    curated_files = 0
    if not knowledge.exists():
        return KnowledgeStatus({}, ["No knowledge base found. Run `coding-scaffold setup-knowledge`."])
    for path in knowledge.rglob("*.md"):
        if path.name.endswith(".new"):
            continue
        frontmatter, warning = _frontmatter(path)
        if warning:
            warnings.append(warning)
        scope = frontmatter.get("scope") or _scope_from_path(path, knowledge)
        maturity = frontmatter.get("maturity") or "unspecified"
        counts.setdefault(scope, {})
        counts[scope][maturity] = counts[scope].get(maturity, 0) + 1
        if _is_raw_note(path, knowledge):
            raw_files += 1
            continue
        if _is_curated_wiki_page(path, knowledge):
            curated_files += 1
            warnings.extend(_curated_metadata_warnings(path, knowledge, frontmatter))
        if "scope" not in frontmatter and _is_layered_note(path, knowledge):
            warnings.append(f"{path.relative_to(knowledge)} is missing frontmatter field: scope")
        if "maturity" not in frontmatter and _is_layered_note(path, knowledge):
            warnings.append(f"{path.relative_to(knowledge)} is missing frontmatter field: maturity")
    return KnowledgeStatus(counts, warnings, raw_files=raw_files, curated_files=curated_files)


def distill_knowledge(target: Path, source: str = "raw", review: bool = True) -> KnowledgeDistillResult:
    root = target.expanduser().resolve()
    knowledge = root / ".coding-scaffold" / "knowledge"
    source_path = _resolve_knowledge_source(root, knowledge, source)
    wiki = knowledge / "wiki"
    created: list[Path] = []
    updated: list[Path] = []
    skipped: list[Path] = []
    warnings: list[str] = []
    if not source_path.exists():
        return KnowledgeDistillResult([], [], [], [f"Source not found: {source_path}"])
    raw_notes = [
        path
        for path in sorted(source_path.rglob("*.md"))
        if path.name != "README.md" and not path.name.endswith(".new")
    ]
    if not raw_notes:
        return KnowledgeDistillResult([], [], [], [f"No raw Markdown notes found in {source_path}"])
    for raw in raw_notes:
        relative = raw.relative_to(source_path)
        slug = _slugify(raw.stem)
        destination = wiki / f"{slug}.md"
        proposal = destination.with_name(destination.name + ".new") if review else destination
        content = _distilled_wiki_proposal(raw, relative)
        existed = proposal.exists()
        write_text(proposal, content, overwrite=True)
        if existed:
            updated.append(proposal)
        else:
            created.append(proposal)
    return KnowledgeDistillResult(created, updated, skipped, warnings)


def _frontmatter(path: Path) -> tuple[dict[str, str], str | None]:
    # Supported subset: `---` fenced YAML-style block, one `key: value` per line.
    # Splits on the first unquoted `:`; preserves the raw value (including quotes,
    # brackets, and nested colons) after stripping surrounding matched quotes.
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return {}, f"{path.name} could not be decoded as UTF-8; frontmatter skipped"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, None
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        field, value = _split_first_unquoted_colon(line)
        if field is None:
            continue
        cleaned = _strip_matched_quotes(value.strip())
        if field == "source_refs" and not cleaned:
            cleaned = "[]"
        values[field] = cleaned
    return values, None


def _split_first_unquoted_colon(line: str) -> tuple[str | None, str]:
    quote: str | None = None
    for index, char in enumerate(line):
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
            continue
        if char == ":":
            return line[:index].strip(), line[index + 1 :]
    return None, ""


def _strip_matched_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _scope_from_path(path: Path, knowledge: Path) -> str:
    try:
        first = path.relative_to(knowledge).parts[0]
    except (IndexError, ValueError):
        return "unspecified"
    if first in {"team", "department", "unit", "company"}:
        return first
    if first == "wiki":
        return "team"
    return "unspecified"


def _is_layered_note(path: Path, knowledge: Path) -> bool:
    return _scope_from_path(path, knowledge) != "unspecified" and path.name != "README.md"


def _is_raw_note(path: Path, knowledge: Path) -> bool:
    try:
        return path.relative_to(knowledge).parts[0] == "raw"
    except (IndexError, ValueError):
        return False


def _is_curated_wiki_page(path: Path, knowledge: Path) -> bool:
    try:
        relative = path.relative_to(knowledge)
    except ValueError:
        return False
    return len(relative.parts) >= 2 and relative.parts[0] == "wiki" and path.name != "README.md"


def _curated_metadata_warnings(path: Path, knowledge: Path, frontmatter: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    relative = path.relative_to(knowledge)
    for field in ("scope", "maturity", "owner", "last_reviewed", "source_refs"):
        if not frontmatter.get(field):
            warnings.append(f"{relative} is missing frontmatter field: {field}")
    reviewed = frontmatter.get("last_reviewed")
    if reviewed:
        try:
            reviewed_date = datetime.strptime(reviewed, "%Y-%m-%d").date()
        except ValueError:
            warnings.append(f"{relative} has invalid last_reviewed date: {reviewed}")
        else:
            if (date.today() - reviewed_date).days > STALE_REVIEW_DAYS:
                warnings.append(
                    f"{relative} has not been reviewed in more than {STALE_REVIEW_DAYS} days"
                )
    return warnings


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
        "foam": {
            "optional": True,
            "workspace_path": ".coding-scaffold/knowledge",
            "extension": "foam.foam-vscode",
            "open": (
                "Open .coding-scaffold/knowledge as a VS Code workspace; "
                "the Foam extension recommends itself on first open."
            ),
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
    foam_line = (
        "This scaffold also generated a VS Code workspace and Foam templates under "
        "`.coding-scaffold/knowledge/`."
        if backend == "foam"
        else (
            "Run `coding-scaffold knowledge --backend foam` later if you want a Foam workspace "
            "(MIT-licensed VS Code extension)."
        )
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

## Optional Foam

{foam_line}

Foam is a free, MIT-licensed VS Code extension that adds backlinks, a graph view, and templates on
top of plain Markdown. Use it when teammates want Obsidian-style ergonomics without the commercial
license (Obsidian is free for personal use but requires a paid Commercial license for
organizations of more than two people).

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

- [Curated wiki](wiki/)
- [Raw inputs](raw/README.md)
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


def _raw_readme() -> str:
    return """# Raw Knowledge Inputs

Drop rough source material here before distilling it into the curated wiki. Raw notes can be messy,
but they should still avoid secrets and customer-private data.

Use `coding-scaffold knowledge distill --target . --source raw --review` to create reviewable
`.new` proposals under `wiki/`.
"""


def _raw_folder_readme(label: str) -> str:
    return f"""# Raw {label.title()}

Store uncurated {label} here. Link or copy only what the team is allowed to review in Git.
"""


def _curated_wiki_page(topic: str) -> str:
    title = topic.title()
    today = date.today().isoformat()
    return f"""---
scope: team
maturity: draft
owner: platform-ai
last_reviewed: {today}
source_refs: []
---
# {title}

Curated project knowledge for {topic}. Add only reviewed, durable information here. Link raw notes
through `source_refs` when promoting material from `../raw/`.
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
    collect_text(files, skipped, knowledge / "00 Start Here.md", _obsidian_start_here())
    collect_text(files, skipped, knowledge / "10 Decisions" / "README.md", _obsidian_decisions_readme())
    collect_text(files, skipped, knowledge / "20 Skills" / "README.md", _obsidian_skills_readme())
    collect_text(files, skipped, knowledge / "30 Agents" / "README.md", _obsidian_agents_readme())
    collect_text(files, skipped, knowledge / "40 Sessions" / "README.md", _obsidian_sessions_readme())
    collect_text(files, skipped, knowledge / "50 Glossary" / "README.md", _obsidian_glossary_readme())
    collect_text(files, skipped, knowledge / "90 Inbox" / "README.md", _obsidian_inbox_readme())
    collect_text(files, skipped, knowledge / "Templates" / "Decision.md", _obsidian_decision_template())
    collect_text(files, skipped, knowledge / "Templates" / "Skill.md", _obsidian_skill_template())
    collect_text(files, skipped, knowledge / "Templates" / "Agent.md", _obsidian_agent_template())
    collect_text(files, skipped, knowledge / ".obsidian" / "app.json", _obsidian_app_json())
    collect_text(files, skipped, knowledge / ".obsidian" / "graph.json", _obsidian_graph_json())
    collect_text(files, skipped, knowledge / ".obsidian" / "templates.json", _obsidian_templates_json())


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


def _resolve_knowledge_source(root: Path, knowledge: Path, source: str) -> Path:
    candidate = Path(source)
    if candidate.is_absolute():
        return candidate
    knowledge_relative = knowledge / source
    if knowledge_relative.exists() or source == "raw":
        return knowledge_relative
    return root / source


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "note"


def _distilled_wiki_proposal(raw: Path, relative_source: Path) -> str:
    source_text = raw.read_text(encoding="utf-8").strip()
    title = _title_from_markdown(source_text) or raw.stem.replace("-", " ").replace("_", " ").title()
    today = date.today().isoformat()
    excerpt = _first_content_lines(source_text)
    return f"""---
scope: team
maturity: draft
owner: platform-ai
last_reviewed: {today}
source_refs:
  - raw/{relative_source.as_posix()}
---
# {title}

## Distilled Summary

Review this proposal and replace rough notes with durable team knowledge.

## Source Notes

{excerpt}
"""


def _title_from_markdown(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or None
    return None


def _first_content_lines(content: str, limit: int = 12) -> str:
    lines = [line for line in content.splitlines() if line.strip()]
    if not lines:
        return "- No source text found."
    excerpt = lines[:limit]
    if len(lines) > limit:
        excerpt.append("...")
    return "\n".join(f"> {line}" for line in excerpt)


def _opencode_share_agent_pattern() -> str:
    return """Turn a useful agent behavior into shared team knowledge.

Inspect `.coding-scaffold/knowledge/agents/README.md`, `.opencode/agents/`, and the recent session
context. Propose a small documented agent role or update an existing one. Include when to use it,
what it may read or edit, verification expectations, and handoff rules.
"""


def _collect_foam_files(files: list[Path], skipped: list[Path], knowledge: Path) -> None:
    collect_text(files, skipped, knowledge / "FOAM.md", _foam_start_here())
    collect_text(files, skipped, knowledge / ".vscode" / "extensions.json", _foam_extensions_json())
    collect_text(files, skipped, knowledge / ".vscode" / "settings.json", _foam_settings_json())
    collect_text(files, skipped, knowledge / ".foam" / "templates" / "decision.md", _foam_decision_template())
    collect_text(files, skipped, knowledge / ".foam" / "templates" / "skill.md", _foam_skill_template())
    collect_text(files, skipped, knowledge / ".foam" / "templates" / "agent.md", _foam_agent_template())


def _foam_start_here() -> str:
    return """# Foam Workspace

This directory is also wired as a Foam workspace. Open `.coding-scaffold/knowledge/` in VS Code
and accept the `foam.foam-vscode` recommendation to enable backlinks, the graph view, and the
templates under `.foam/templates/`.

Foam reads plain Markdown with `[[wikilink]]` syntax. The scaffold's curated wiki pages under
`wiki/` use standard relative links so they render on GitHub; feel free to use `[[wikilinks]]` in
your own notes under `raw/`, `sessions/`, `decisions/`, and the layered scopes.

## Suggested workflow

1. Capture raw notes from agent sessions in `raw/code-notes/` or `raw/incidents/`.
2. Use Foam's graph view to spot recurring topics.
3. Promote stable notes into `wiki/`, `decisions/`, or one of the hierarchical-sharing scopes
   (`team/`, `department/`, `unit/`, `company/`) via pull request.
4. Use the templates under `.foam/templates/` when starting a new decision, skill, or agent note
   (right-click in VS Code → "Foam: Create new note from template").

## Why Foam

Foam is MIT-licensed and runs entirely in VS Code. It's a free alternative to Obsidian for teams
that need a commercial license for organizational use. Markdown stays the source of truth — Git
remains the review and sharing mechanism.
"""


def _foam_extensions_json() -> str:
    return json.dumps(
        {
            "recommendations": [
                "foam.foam-vscode",
            ],
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def _foam_settings_json() -> str:
    return json.dumps(
        {
            "foam.edit.linkReferenceDefinitions": "off",
            "foam.files.defaultExtension": ".md",
            "foam.files.ignore": [
                "**/.git/**",
                "**/.coding-scaffold/**/_repo/**",
            ],
            "foam.graph.style": {
                "background": "#202020",
                "fontSize": 12,
            },
            "foam.openDailyNote.directory": "raw/meetings",
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def _foam_decision_template() -> str:
    return """---
foam_template:
  name: Decision
  description: Architecture, model routing, tool choice, data handling, or workflow decision.
---
# Decision: $FOAM_TITLE

Date: $FOAM_DATE_YEAR-$FOAM_DATE_MONTH-$FOAM_DATE_DATE
Status: proposed | accepted | superseded

Related: [[FOAM]]

## Context

What forced this decision?

## Decision

What did we decide?

## Consequences

What changes downstream? What did we trade off?

## Agent Notes

What should an AI coding agent know about this decision?
"""


def _foam_skill_template() -> str:
    return """---
foam_template:
  name: Skill
  description: A reusable prompt or workflow that the team has validated.
---
# Skill: $FOAM_TITLE

Status: draft | validated | recommended | standard

Related agents:

## When To Use

## Workflow

## Verification

## Maintenance Notes
"""


def _foam_agent_template() -> str:
    return """---
foam_template:
  name: Agent
  description: A trusted agent role with explicit scope and handoff rules.
---
# Agent: $FOAM_TITLE

Status: draft | validated | recommended | standard

Related skills:

## Responsibility

## Allowed Context

## Write Scope

## Handoff Rules
"""
