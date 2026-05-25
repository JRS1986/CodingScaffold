# Agent Orchestration

Agent orchestration is the difference between "ask a model" and "run a controlled coding workflow".
In this scaffold it is not a separate runtime. It generates native OpenCode agents and commands
where possible, and keeps generic JSON/Markdown notes for other tools.

## Profiles

### Solo

Use for small tasks. One agent inspects, edits, verifies, and summarizes. Keep checkpoints explicit.

```bash
coding-scaffold tools orchestrate --target . --profile solo
```

### Pair

Use for normal feature work. A builder makes the change; a reviewer looks for regressions, missing
tests, and unclear behavior. This is the default because it catches more without adding much process.

```bash
coding-scaffold tools orchestrate --target . --profile pair
```

### Team

Use for larger changes. Split into explorer, planner, implementer, and verifier roles. Give each
agent a clear scope and avoid overlapping file ownership.

```bash
coding-scaffold tools orchestrate --target . --profile team
```

Add `--adapter none` if you only want the generic `.coding-scaffold/orchestration.json` file.

## Good Handoffs

- State the task and non-goals.
- Assign file or module ownership.
- Name the model route: routine or heavy-lift.
- Include the exact verification command.
- Summarize changed files and residual risk.

## First Useful Loop

Inside OpenCode:

```text
/first-session
/agentic-change
```

The first command builds context without editing. The second runs a small explorer -> implementer ->
reviewer loop so the user sees the difference between a coding assistant and an agentic workflow.

## Repeatable Workflow Backend

When an interactive workflow has proven itself, generate an optional Open Multi-Agent backend:

```bash
coding-scaffold tools workflow --target . --backend open-multi-agent
```

Use this for repeatable automation, not discovery. Keep discovery and skill validation in OpenCode;
move to Open Multi-Agent only when the team wants a reviewed, observable TypeScript workflow.

## When To Escalate

Use the heavy-lift route for architecture, migrations, security-sensitive code, production incident
debugging, or when the routine route fails twice.
