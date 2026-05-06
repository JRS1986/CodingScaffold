# Knowledge Base

The knowledge base is the team memory for agentic coding. It stores decisions, session notes,
project vocabulary, skill notes, agent patterns, and source-of-truth links.

## Markdown First

Plain Markdown is the default:

```bash
coding-scaffold knowledge --target ~/dev/my-project
```

This creates:

- `.coding-scaffold/KNOWLEDGE.md`
- `.coding-scaffold/knowledge.json`
- `.coding-scaffold/knowledge/`

## Shared GitHub Or GitLab Memory

Use a shared remote when multiple people should contribute:

```bash
coding-scaffold setup-knowledge --target ~/dev/my-project \
  --backend markdown \
  --shared-remote https://github.com/acme/team-ai-knowledge.git
```

You can keep the knowledge base inside the project repo, or clone a separate repo into
`.coding-scaffold/knowledge`.

## Hierarchical Sharing

Hierarchical sharing is an optional organization pattern. Start with structure before adding
multiple remotes:

```text
.coding-scaffold/knowledge/
  company/
  unit/
  department/
  team/
  sharing/
```

Use each layer for a different audience:

- `team`: project facts, local prompts, first skill drafts, session findings.
- `department`: reusable runbooks, system patterns, validated agent roles.
- `unit`: domain vocabulary, reference architecture, shared provider policy.
- `company`: standards, approved skills, approved agents, security and privacy rules.

Use frontmatter to make ownership and promotion visible:

```yaml
scope: team
maturity: draft
owner: platform-ai
tags: [testing, opencode]
source_project: billing-api
reviewed_by: ""
expires: 2026-12-31
```

Use maturity levels as a trust ladder:

- `draft`: captured from real work but not reviewed.
- `validated`: tried in at least one project and reviewed by peers.
- `recommended`: useful across multiple teams or systems.
- `standard`: approved default for this scope.

Promote knowledge upward by pull request. Keep secrets out of every layer. Use separate Git remotes
only when access boundaries differ; otherwise one shared repo with folders, tags, and CODEOWNERS is
easier to operate.

Check the current state:

```bash
coding-scaffold knowledge-status --target ~/dev/my-project
```

The status command counts notes by scope and maturity, and flags missing frontmatter on layered
notes.

## Obsidian

Obsidian mode keeps Markdown as the source of truth while adding vault structure, backlinks,
frontmatter templates, and graph-friendly navigation:

```bash
coding-scaffold setup-addon --target ~/dev/my-project --addon obsidian
coding-scaffold knowledge --target ~/dev/my-project --backend obsidian
```

Use this when humans want a better reading and navigation layer. In WSL, install the desktop app on
Windows and open `.coding-scaffold/knowledge` as a vault.

## MemPalace

MemPalace mode adds notes for optional local semantic retrieval and MCP-compatible memory workflows:

```bash
coding-scaffold knowledge --target ~/dev/my-project --backend mempalace
```

Use this when the Markdown corpus grows large enough that search and semantic retrieval matter.

## What To Capture

Good knowledge entries answer:

- what did we decide?
- why did we decide it?
- where is the source of truth?
- which skill or agent should use this?
- when should this knowledge be reviewed or removed?
