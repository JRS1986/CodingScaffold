# Coding Agent Notes

Tone: efficient engineering toolset with clear, practical onboarding

Project language: ${language}
Project target: ${project_target}
Existing codebase: ${existing_codebase}
Privacy mode: ${privacy}
Guidance mode: ${mode}

## Operating Contract

- Inspect the project before editing.
- Keep changes small, tested, and reversible.
- Do not collect or write API keys into this repository.
- Prefer local inference unless the task explicitly needs cloud quality and credentials are available.
- Keep generated guidance direct, neutral, and project-focused.

## Model Routing

- Routine model: `${weak_model}`
- Heavy-lift model: `${strong_model}`
- Route threshold: `${route_threshold}`
- Cloud provider: `${cloud_provider}`
- Cloud model family: `${cloud_model_family}`

## Skill Habits

- Context first: read the tree, README, tests, and config before asking an LLM for edits.
- Prompt small: ask for one inspectable change or one bounded plan.
- Verify locally: run the narrowest meaningful test before broad checks.
- Review like a maintainer: ask what could break, what is untested, and what changed.
- Route deliberately: local for routine work, stronger model for architecture or repeated failure.

## Orchestration Habits

- Solo for narrow changes.
- Pair for normal implementation plus review.
- Team for broad work with disjoint file ownership.
- Never let multiple agents edit the same file without an explicit maintainer merge step.

## Communication Habits

- Routing recheck: pause and reassess when an answer feels off.
- Change checkpoint: pause before migrations, dependency upgrades, or broad refactors.
- Explicit handoff: state assumptions, commands, expected signals, and next steps.
- Small change, fast test, clear rollback.

## Knowledge Nudge

At the end of each substantial chat or coding session, use the current coding environment's
configured model to ask what reusable knowledge should be remembered. Capture only durable
candidates: project facts, team preferences, decisions, failed attempts, useful commands, gotchas,
or reusable prompts. Do not save raw chat transcripts, secrets, personal data, or transient
conversation.

Prefer reviewable outputs:

- Add bullets to the active session trace under `## Reusable Knowledge Discovered`.
- Use the native `knowledge-propose` command or skill when available.
- Write proposals as `.new` files under `.coding-scaffold/knowledge/wiki/` or short-lived entries
  under `.coding-scaffold/memory/session_lesson/` only when asked.
- Keep source references back to the session trace, issue, PR, or raw note that justified the
  proposal.
