# Skills and Agents

Skills and agents are the team acceleration layer. They turn one good workflow into something peers
can reuse and improve.

## Create A Skill

```bash
coding-scaffold skill --target ~/dev/my-project \
  --adapter opencode \
  --name "Release Review" \
  --description "Review a release candidate before tagging."
```

This creates:

- `.coding-scaffold/skills/release-review.md`
- `.opencode/commands/release-review.md`

## What A Good Skill Contains

A good skill is short and procedural:

- when to use it
- what context to inspect
- what not to touch
- the step-by-step workflow
- verification expectations
- escalation rules

## Agent Profiles

Generate an orchestration plan:

```bash
coding-scaffold orchestrate --target ~/dev/my-project --profile pair
```

Profiles:

- `solo`: one agent with explicit checkpoints
- `pair`: builder plus reviewer
- `team`: explorer, planner, implementer, verifier

## Review Skills Like Code

Skills should be reviewed when they:

- add broad write permissions
- change model routing assumptions
- introduce new verification behavior
- become team defaults
- encode project-specific architecture rules

The best skills are not clever prompts. They are reliable engineering habits.

