# Core Concepts

## Scaffold, Not Agent

CodingScaffold is the bootstrap and governance layer around existing coding agents. It prepares
project-local guidance, credentials, adapters, model recommendations, policy, and knowledge. It
does not replace Claude Code, Codex, OpenCode, Cursor, Copilot, Hermes, or Pi.

## Local-First, Not Local-Only

CodingScaffold prefers local inference for routine work, but it can use cloud providers when the
project allows that and credentials are available. This keeps sensitive or routine edits close to
the machine while still leaving room for stronger models on architecture, security, and difficult
reviews.

## Provider, Model Family, Deployment

The scaffold keeps three ideas separate:

- provider: where the request is sent, such as Ollama, OpenAI, Anthropic, Azure OpenAI, or Azure AI
- model family: what kind of model answers, such as local, OpenAI, Anthropic, or Google
- deployment: a provider-specific name, common in Azure environments

This matters because Azure can be the endpoint while the deployed model family is OpenAI,
Anthropic, or another model family.

## Agentic Coding

Agentic coding is a workflow, not just a bigger prompt. A good loop has:

- context loading
- a small plan
- bounded edits
- local verification
- review
- a summary with changed files and residual risk

## Skills

Skills are team-owned workflows encoded as reusable Markdown instructions. They are useful when a
team repeats work such as release checks, dependency upgrades, incident reviews, or API contract
changes.

## Team Knowledge

Team memory should be durable, reviewable, and searchable. CodingScaffold uses Markdown as the
source of truth and can shape that Markdown for plain Git, Obsidian, or MemPalace indexing.

Raw notes belong under `knowledge/raw/`. Curated, reviewed pages belong under `knowledge/wiki/`
with ownership, maturity, freshness, and source references.
