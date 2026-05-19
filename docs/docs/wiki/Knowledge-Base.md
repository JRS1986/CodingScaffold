# Knowledge Base

The knowledge base is the team memory for agentic coding. It stores decisions, session notes,
project vocabulary, skill notes, agent patterns, and source-of-truth links.

## Markdown First

Plain Markdown is the default:

```bash
coding-scaffold knowledge create --target ~/dev/my-project
```

This creates:

- `.coding-scaffold/KNOWLEDGE.md`
- `.coding-scaffold/knowledge.json`
- `.coding-scaffold/knowledge/`

The generated knowledge base separates raw inputs from curated wiki pages, and includes
scaffolding for decision records, session notes, reusable skills and agents, and the optional
hierarchical-sharing layers:

```text
.coding-scaffold/knowledge/
  INDEX.md                         # entry point — start reading here
  README.md
  glossary.md
  links.md
  sync.md
  raw/
    meetings/
    decisions/
    code-notes/
    incidents/
  wiki/                            # curated, reviewed source of truth
    architecture.md
    setup.md
    testing.md
    deployment.md
    domain-language.md
    decisions.md
  decisions/                       # ADR-style decision records
    0001-decision-template.md
  sessions/                        # captured agent-session notes
    session-template.md
  skills/                          # reusable team skills
  agents/                          # reusable agent patterns
  sharing/                         # hierarchical-sharing entry point
  team/                            # hierarchical layer: project facts, local prompts
  department/                      # hierarchical layer: runbooks, system patterns
  unit/                            # hierarchical layer: domain vocabulary, reference arch
  company/                         # hierarchical layer: approved standards
```

Raw notes are source material. Curated wiki pages are the reviewable source of truth for agents.
The layered folders (`team` / `department` / `unit` / `company`) are optional — see
[Hierarchical Sharing](#hierarchical-sharing) for when to use them.

## Shared GitHub Or GitLab Memory

Use a shared remote when multiple people should contribute:

```bash
coding-scaffold setup knowledge --target ~/dev/my-project \
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
coding-scaffold knowledge status --target ~/dev/my-project
coding-scaffold context budget --target ~/dev/my-project --source knowledge
```

The status command counts notes by scope and maturity, and flags missing frontmatter on layered
notes. It also distinguishes raw notes from curated wiki pages, flags missing `owner`,
`last_reviewed`, and `source_refs`, and warns when curated pages have not been reviewed recently.
The budget command estimates whether the knowledge base is still a healthy size for an agent
session. See [Context Hygiene](Context-Hygiene.md) before compressing or loading large shared notes.

Create reviewable curated proposals from raw notes:

```bash
coding-scaffold knowledge distill --target ~/dev/my-project --source raw --review
```

The first version is deterministic and review-first. It writes `.new` proposal files under
`knowledge/wiki/` and never silently rewrites curated pages.

## Obsidian

Obsidian mode keeps Markdown as the source of truth while adding vault structure, backlinks,
frontmatter templates, and graph-friendly navigation:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon obsidian
coding-scaffold knowledge create --target ~/dev/my-project --backend obsidian
```

Use this when humans want a better reading and navigation layer. In WSL, install the desktop app on
Windows and open `.coding-scaffold/knowledge` as a vault.

Obsidian is free for personal use. Organizations of more than two people using Obsidian for
business work need an Obsidian Commercial license (paid per user). If that's a blocker for your
team, see the [Foam](#foam) section below — Foam is MIT-licensed and offers a similar workflow
on top of VS Code.

## Foam

Foam mode is a free, MIT-licensed alternative to Obsidian. It runs as a VS Code extension and
reads plain Markdown with `[[wikilink]]` syntax. The scaffold writes a self-contained VS Code
workspace under `.coding-scaffold/knowledge/`:

```bash
coding-scaffold knowledge create --target ~/dev/my-project --backend foam
```

This generates:

- `.vscode/extensions.json` — recommends `foam.foam-vscode` on first open.
- `.vscode/settings.json` — Foam workspace defaults (graph view, daily-note directory, ignore
  patterns for `.git/` and `_repo/`).
- `.foam/templates/{decision,skill,agent}.md` — Foam note templates.
- `FOAM.md` — entry note explaining the workflow.

Open `.coding-scaffold/knowledge/` as a VS Code workspace and accept the extension recommendation
to enable backlinks, the graph view, and template-based note creation. The scaffold's curated
`wiki/` pages keep standard relative-link Markdown so they render on GitHub; use `[[wikilinks]]`
in your own notes under `raw/`, `sessions/`, `decisions/`, and the layered scopes if you want
Foam's graph view to connect them.

Pick Foam over Obsidian when your organization needs commercial-friendly licensing or already
standardizes on VS Code. Pick Obsidian when you want the dedicated desktop reading surface.

## MemPalace

MemPalace mode adds notes for optional local semantic retrieval and MCP-compatible memory workflows:

```bash
coding-scaffold knowledge create --target ~/dev/my-project --backend mempalace
```

Use this when the Markdown corpus grows large enough that search and semantic retrieval matter.

## What To Capture

Good knowledge entries answer:

- what did we decide?
- why did we decide it?
- where is the source of truth?
- which skill or agent should use this?
- when should this knowledge be reviewed or removed?
