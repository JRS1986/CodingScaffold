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
