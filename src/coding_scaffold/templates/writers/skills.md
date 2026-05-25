# AI Coding Skills

These are practical skills for using local and routed LLMs as an efficient coding toolset.

A skill is a reusable senior-engineer habit. It tells the agent what context to load, what workflow
to follow, how to verify, and what not to touch. Good skills make peers faster because they encode
the team's judgment, not just a prompt.

## Context Loading

Tell the agent what to read before it edits:

- README and architecture docs
- package files and test config
- the smallest relevant source files
- failing test output or reproduction steps

Prompt example:

```text
Inspect the README, pyproject, and tests before editing. Then explain the smallest safe change.
```

## Bounded Implementation

Ask for one slice at a time:

- one bug
- one file cluster
- one command path
- one failing test

## Verification

Use the agent to run checks, but keep the signal concrete:

```text
Run the narrowest relevant test first. If it passes, run the broader check.
```

## Review

Ask for code-review mode before merging:

```text
Review this change for regressions, missing tests, and confusing behavior. Findings first.
```

## Routing

Use local models for routine edits, explanations, and test fixes. Route to the stronger model for
architecture, migrations, security, multi-file refactors, or when the local answer fails twice.

## Writing A Project Skill

A useful skill is short and procedural:

- When to use it
- What files to inspect
- The step-by-step workflow
- How to verify
- What not to do

Create a template:

```bash
coding-scaffold skill --target . --name "Release Review" --description "Review a release candidate before tagging."
```

The template is written to `.coding-scaffold/skills/`.

## Useful Starter Skills

- Release Review: check changelog, tests, migration notes, and rollback.
- Dependency Upgrade: inspect breaking changes, update lockfiles, run compatibility checks.
- API Contract Change: update schema, tests, docs, and clients together.
- Frontend QA: verify responsive layout, accessibility labels, and visual regressions.
- Incident Review: reconstruct timeline, root cause, mitigation, and follow-up tasks.

## Validate Skills

- Run the skill on a small real change.
- Check whether it loaded the right files.
- Check whether verification was specific enough.
- Ask a teammate to review the output.
- Update the skill when it misses an important project convention.

## Graduate Proven Skills

When a skill consistently helps, turn it into repeatable automation:

```bash
coding-scaffold tools workflow --target . --backend open-multi-agent
```

Use the generated Open Multi-Agent example as a starting point for reviewed TypeScript workflows
that peers can run, inspect, and improve without tying the team to one vendor.
