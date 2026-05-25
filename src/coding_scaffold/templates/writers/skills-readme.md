# Project Skills

Project skills are reusable instructions for work your team repeats often: release reviews,
database migrations, frontend QA, API contract changes, incident analysis, or dependency upgrades.
They are how a team turns one person's good prompt into shared engineering acceleration.

Create one with an OpenCode command bridge:

```bash
coding-scaffold skill --target . --adapter opencode --name "Release Review" --description "Review a release candidate before tagging."
```

This writes `.coding-scaffold/skills/release-review.md` and `.opencode/commands/release-review.md`.
Keep skills short and procedural. Review them like code: run them on real work, check the output,
and update the skill when it misses context or suggests unsafe steps.
