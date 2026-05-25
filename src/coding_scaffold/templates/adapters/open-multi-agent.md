# Open Multi-Agent

Open Multi-Agent is an optional advanced workflow backend. Use it after your team has validated an
agentic workflow interactively and wants to run it repeatedly from a TypeScript backend, script, or
CI-like automation.

## Why It Fits

- Open source and TypeScript-native.
- Goal-to-task-DAG orchestration with independent tasks running in parallel.
- Multiple model providers, including OpenAI-compatible local endpoints.
- MCP support, token budgets, retries, context strategies, and tracing hooks.
- `planOnly` mode lets you inspect the task DAG before execution.

## When To Use

Use OpenCode for the first human-in-the-loop coding sessions. Use Open Multi-Agent when the team
wants to automate a proven workflow: dependency review, API contract checks, release review,
security triage, migration planning, or other repeatable engineering processes.

## Install

```bash
npm install @jackchen_me/open-multi-agent
```

## Generated Files

- `.coding-scaffold/open-multi-agent.team.json`: team roles and model routes.
- `examples/open-multi-agent/team-coding-workflow.ts`: starter TypeScript workflow.

## Suggested Model Routes

- Routine model: `${routine}`
- Heavy-lift model: `${heavy}`

## Safe Adoption Path

1. Run `/first-session` and `/agentic-change` in OpenCode.
2. Capture the useful workflow as a skill.
3. Generate this backend with `coding-scaffold workflow --target . --backend open-multi-agent`.
4. Run the generated TypeScript example in plan-only mode first.
5. Add execution only after a maintainer reviews the task DAG and permissions.

This is the point where agentic coding becomes internal tooling: not one-off prompts, but repeatable,
observable workflows your peers can run and improve.
