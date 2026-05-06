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
coding-scaffold knowledge --target ~/dev/my-project \
  --shared-remote https://github.com/acme/team-ai-knowledge.git
```

You can keep the knowledge base inside the project repo, or clone a separate repo into
`.coding-scaffold/knowledge`.

## Obsidian

Obsidian mode keeps Markdown as the source of truth while adding vault structure, backlinks,
frontmatter templates, and graph-friendly navigation:

```bash
coding-scaffold knowledge --target ~/dev/my-project --backend obsidian
```

Use this when humans want a better reading and navigation layer.

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

