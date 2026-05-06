# Team Rollout

This page is a practical plan for introducing CodingScaffold to a team.

## Pilot Session

Use one real project and one safe issue.

1. Run `coding-scaffold wizard`.
2. Install OpenCode.
3. Run `/first-session`.
4. Pick one small improvement.
5. Run `/agentic-change`.
6. Review the result as a team.
7. Capture the workflow as a skill.
8. Capture decisions in the knowledge base.

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
