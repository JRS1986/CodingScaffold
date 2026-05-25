# Claude Code Project Guide

This project uses CodingScaffold as a local-first onboarding, configuration, and governance layer
for AI-assisted development. Claude Code should use this file as project memory, not as a runtime
router.

## Team Contract

- Inspect before editing.
- Keep changes bounded to the requested task.
- Prefer reviewed Markdown knowledge in `.coding-scaffold/knowledge/`.
- Keep credentials in local ignored files or Claude Code's secure auth flow.
- Ask before broad rewrites, dependency changes, destructive commands, or cloud/provider changes.

## Model Guidance

- Routine/profile model: `${weak}`
- Heavy-lift/review model: `${strong}`

Use Claude Code's native `/model`, settings, and account configuration for actual model selection.
CodingScaffold only provides guidance and shared project context here.

## First Session

Run `/first-session` and wait for the repository map, test commands, risk areas, and one safe
proposed improvement before making edits.
