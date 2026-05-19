# Advanced Workflows

Start simple. Add advanced workflows only after the team has validated the basics.

## RouteLLM

RouteLLM can expose one OpenAI-compatible endpoint that routes actual requests between weak/routine
and strong/heavy-lift models. It is optional and advanced; most tools should start with
recommendation or static profile guidance.

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon routellm
coding-scaffold tools route --target ~/dev/my-project --backend routellm
```

Generated files:

- `.coding-scaffold/ROUTELLM.md`
- `.coding-scaffold/routellm.config.yaml`

Use RouteLLM when endpoint-level model routing matters. For simple explainable recommendations, use
`coding-scaffold tools select-model`.

## Context Compression

The built-in compressor writes token-saving sidecars for large knowledge bases without extra
installation:

```bash
coding-scaffold context budget --target ~/dev/my-project --source team
coding-scaffold context compress --target ~/dev/my-project --source knowledge
```

Caveman Compression is optional when you want to try the upstream engine explicitly:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon caveman-compression
coding-scaffold context compress --target ~/dev/my-project --source knowledge --engine caveman
```

Use either path after the team has reviewed the source notes. Compressed sidecars are agent input,
not the canonical record.

## Open Multi-Agent

Open Multi-Agent is an optional workflow backend for repeatable TypeScript automation:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon open-multi-agent
coding-scaffold tools workflow --target ~/dev/my-project --backend open-multi-agent
```

Generated files:

- `.coding-scaffold/OPEN_MULTI_AGENT.md`
- `.coding-scaffold/open-multi-agent.team.json`
- `examples/open-multi-agent/team-coding-workflow.ts`

Recommended adoption path:

1. Validate the workflow interactively in OpenCode.
2. Capture it as a skill.
3. Run the generated workflow in plan-only mode.
4. Review permissions, traces, and verification signals.
5. Automate only after the team trusts the process.
