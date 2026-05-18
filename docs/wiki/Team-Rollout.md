# Team Rollout

This page is a practical plan for introducing CodingScaffold to a team.

## Pilot Session

Use one real project and one safe issue.

1. Run `coding-scaffold setup run --target <repo>`.
2. Review provider and hardware detection.
3. Generate or confirm `AGENTS.md`, OpenCode config, policy defaults, and starter knowledge.
4. Run OpenCode `/first-session`.
5. Pick one small improvement.
6. Run `/agentic-change`.
7. Review generated files, credentials, provider policy, MCP settings, knowledge provenance, and tests.
8. Capture the workflow as a skill and one knowledge entry.
9. Have a second developer run `team connect` against the shared manifest.

## Team Defaults

Agree on:

- privacy mode
- preferred local runtime
- cloud escalation rules
- default coding adapter
- verification commands
- when to use heavy-lift models
- where shared knowledge lives

Publish those defaults as a team onboarding manifest:

```bash
coding-scaffold team init --target . --team platform-api
```

New joiners should be able to run:

```bash
coding-scaffold team connect --target . --manifest <team-onboarding-repo>
coding-scaffold team connect --target . --manifest <team-onboarding-repo> --dry-run
coding-scaffold team doctor --target .
```

That should expose the shared knowledge base, approved skills, approved agents, policy, config, and
required add-ons before the first agentic coding session.

## Governance

Review these changes like code:

- skills
- agent definitions
- model-routing defaults
- shared knowledge decisions
- workflow automation

## Success Signals

The rollout is working when:

- developers inspect before editing
- generated changes are smaller
- tests are run more consistently
- review findings are caught earlier
- good prompts become skills
- decisions move from chat history into shared knowledge
