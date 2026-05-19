---
pageType: home

hero:
  name: CodingScaffold
  text: Local-first AI coding setup for real teams
  tagline: Start with three commands, then grow into shared knowledge, policies, and repeatable agent workflows only when you need them.
  actions:
    - theme: brand
      text: Start Here
      link: /wiki/Getting-Started
    - theme: alt
      text: Team Pilot
      link: /wiki/Team-Rollout
---

## Start Small

CodingScaffold helps a project use existing coding agents without turning day one into a tool
migration. It writes reviewable project-local files for agent instructions, provider hints,
knowledge, policies, and workflows.

For a new repo or a small team pilot, use only this:

```bash
coding-scaffold doctor --target .
coding-scaffold pilot --target . --tool opencode
# follow the printed steps
```

`doctor` tells you what is already present and recommends the next 1-3 commands. `pilot` runs
read-only local checks and prints a safe 10-minute path. Neither command installs tools or writes
files.

## Choose Your Path

| If you are... | Read this | Outcome |
| --- | --- | --- |
| Trying CodingScaffold for the first time | [Getting Started](/wiki/Getting-Started) | One inspected, verified, reviewable agent session. |
| Piloting with a small team | [Team Rollout](/wiki/Team-Rollout) | A two-person pilot before shared manifests or advanced governance. |
| Reviewing security posture | [Security](/wiki/Security) | Clear boundaries: what the scaffold generates and what it does not enforce. |
| Comparing tool support | [Tool Adapters](/wiki/Tool-Adapters) | Which coding agents get deep config, native guidance, or lightweight docs. |
| Planning shared knowledge | [Knowledge Base](/wiki/Knowledge-Base) | Markdown-first team memory that stays reviewable in Git. |

Advanced surfaces such as MCP governance, RouteLLM, skills, memory classes, and team manifests are
available, but they are intentionally not required for the first useful session.
