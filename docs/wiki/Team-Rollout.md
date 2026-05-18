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

## Persona Paths

Pick the path that matches the developer you're onboarding. Each path lists who it's for, what
"done" looks like for them, and the smallest command set that gets them there.

### Beginner path — for a junior developer new to agentic coding

**Who:** writes Python or web code, hasn't worked with an autonomous coding agent before. Wants
guardrails, not freedom.

**Success looks like:** after one session, they've inspected the repo with the agent, understood
the test command, and landed one small reviewable change without "magic" edits.

```bash
coding-scaffold setup run --target . --mode beginner
# Review the generated AGENTS.md, .opencode/, and .coding-scaffold/.
opencode  # or: claude
# Inside the agent, run /first-session, then /agentic-change on one small issue.
```

The beginner mode includes a first-project guide and conservative defaults
(`permission.edit: ask`, `share: disabled`). Keep policy at `--scope team` until the developer is
comfortable.

### Control / reproducibility path — for the skeptical senior

**Who:** deep expertise in their domain (firmware, embedded, kernel, etc.). Wants traceability,
no surprise edits, and a way to undo anything the agent did.

**Success looks like:** every agent action is visible in `git diff` and reproducible from the
scaffold files alone. They can disable any provider, any MCP server, and audit what the agent saw.

```bash
coding-scaffold setup run --target . --privacy local-only --tool claude-code
coding-scaffold policy --target . --scope team --strict
coding-scaffold credentials --target . --format env
# Review .claude/settings.json (permission.edit: ask, permission.bash: ask).
# Review .coding-scaffold/policy/*.md for the disabled-providers list.
```

Pair with the [Threat Model](Security.md#threat-model) so they see the boundaries explicitly.

### Security review path — for a compliance engineer

**Who:** approves whether the team can use AI coding tools at all. Wants policy defaults,
credential handling, provider constraints, and audit expectations on paper.

**Success looks like:** they can answer "what does this tool generate, what does it not enforce,
and where do real controls live?" using the scaffold's own docs.

```bash
coding-scaffold setup run --target . --tool opencode
coding-scaffold policy --target . --scope company
# Read .coding-scaffold/policy/company.md, opencode.json.new, providers.json.
# Read docs/wiki/Security.md — Threat Model section.
```

The acceptance artifact is the policy diff plus a checklist of which platform controls back it
(identity, network egress, secret scanning, repository protection, CI). The scaffold doesn't
replace any of those; it surfaces what's expected.

### Team-lead path — for a lead establishing shared defaults

**Who:** runs a team where some developers use AI tools privately. Wants AI to become a team
capability with shared prompts, shared knowledge, shared policy.

**Success looks like:** every developer can `team connect` against the same manifest and get the
same generated config, knowledge layer, and policy. New joiners are productive on day one.

```bash
coding-scaffold team init --target . --team platform-api --knowledge-remote <repo-url>
# Customize .coding-scaffold/team-onboarding.json, then commit it.
# Each developer runs:
coding-scaffold team connect --target . --manifest <team-repo>
coding-scaffold team doctor --target .
```

When the manifest changes, every developer runs `team sync` and reviews the diff before merging
imports into their working knowledge.

## Pilot Metrics

These are measurement templates, not features. Track them manually during the pilot. If a number
moves the wrong way, that's the signal to revisit the scaffold or the policy, not the metric.

| Metric | How to measure | Target after 2 weeks |
| --- | --- | --- |
| Time to first safe agentic change | From `setup run` to the first merged PR generated via `/agentic-change`. | < 1 day for the beginner path; < 2 hours for AI power users. |
| Correct-test-command rate | Of agent sessions that ran a test, what fraction ran the project's actual test command (not a guess). | > 80%. Lower means `AGENTS.md` needs more explicit test guidance. |
| CI pass rate after agentic edits | Of PRs containing `/agentic-change` output, what fraction passed CI on first push. | At least matches non-agentic baseline. Below baseline means policy is too permissive or review is too thin. |
| Reusable skills captured | Count of skill entries committed to `.coding-scaffold/knowledge/skills/` during the pilot. | Two or more from each persona path. Zero means workflows aren't being abstracted. |
| Knowledge entries with `last_reviewed` | Of curated wiki pages under `knowledge/wiki/`, what fraction have a `last_reviewed` value within 90 days. | > 90% by end of pilot. Lower means the knowledge layer is decaying. |
| Reverted agentic changes | Count of merged `/agentic-change` PRs reverted within 7 days. | 0-1. Higher signals the scaffold is letting through changes the team can't validate. |

Run a 30-minute retrospective at the end of the pilot. Surface which metric was easiest to gather,
which was hardest, and whether any persona path under- or over-served the developer.
