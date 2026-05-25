# Codex Project Guide

CodingScaffold configures shared project guidance for Codex. It does not replace Codex, control
Codex runtime behavior, or store credentials.

## Operating Rules

- Inspect before editing and keep changes bounded.
- Use suggest/read-only behavior for unfamiliar areas and reviews.
- Prefer local-first workflows unless the task explicitly needs cloud quality and credentials are available.
- Keep secrets in ignored local files or provider auth flows, never in generated scaffold files.
- Review generated knowledge, adapters, and policy changes like code.

## Model Guidance

- Routine/profile model: `${weak}`
- Heavy-lift/review model: `${strong}`

Use Codex's native model and approval-mode controls for actual execution. Treat these values as
team guidance for choosing routine versus heavy-lift work.

## Knowledge

Start with `.coding-scaffold/knowledge/INDEX.md` when it exists. Curated wiki pages are preferred
over raw notes.

## Knowledge Nudge

At the end of each substantial chat, use Codex's currently configured model to identify reusable
knowledge candidates. Capture only durable project facts, decisions, team preferences, failed
attempts, useful commands, gotchas, or reusable prompts. Do not store raw transcripts, secrets,
personal data, or irrelevant conversation.

Prefer reviewable proposals: add bullets to `## Reusable Knowledge Discovered` in the active
session trace, or use the `knowledge-propose` skill to draft `.new` knowledge proposals with source
refs.
