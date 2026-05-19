# Team Onboarding

Experienced teams should not ask every new developer to rediscover the team memory, approved
skills, trusted agents, policy, and config. Put those defaults in a reviewed non-secret manifest.

## New Developer Flow

Use this page after the team has a reviewed onboarding manifest. If you are trying the scaffold in
a repo that does not have a manifest yet, start with `coding-scaffold doctor --target .` and
`coding-scaffold pilot --target . --tool opencode` instead.

```bash
git clone https://github.com/acme/project.git
cd project
coding-scaffold team connect \
  --manifest https://github.com/acme/platform-ai-onboarding.git
coding-scaffold team doctor
opencode
```

Run `--dry-run` first when connecting to a new source:

```bash
coding-scaffold team connect \
  --manifest https://github.com/acme/platform-ai-onboarding.git \
  --dry-run
```

`team connect` copies the manifest into `.coding-scaffold/team-onboarding.json`, syncs shared
sources, imports Markdown skills, imports OpenCode agents, imports config and policy files, and
writes `.coding-scaffold/team-provenance.json`.

## Manifest

Create a starter manifest:

```bash
coding-scaffold team init --target . \
  --team platform-api \
  --knowledge-remote https://github.com/acme/team-ai-knowledge.git \
  --knowledge-backend obsidian
```

The manifest can point to:

- shared knowledge repo
- approved skills repos
- approved OpenCode agent repos
- policy repo
- config repo
- default coding tool
- required and optional add-ons

Keep it JSON and non-secret. It should contain repo URLs, scopes, paths, and defaults, not API keys
or tokens.

## Sync Model

The default sync mode is copy:

- shared knowledge is copied or cloned to `.coding-scaffold/knowledge`
- skills are copied to `.coding-scaffold/skills`
- agents are copied to `.opencode/agents`
- policy is copied to `.coding-scaffold/policy/imported`
- configs are copied to `.coding-scaffold/configs`

Copy mode is intentionally boring. It works offline after sync, is easy to inspect in Git, and
avoids surprising submodule or symlink behavior for new joiners.

## Commands

```bash
coding-scaffold team init --target .
coding-scaffold team connect --target . --manifest <file-or-git-repo>
coding-scaffold team sync --target .
coding-scaffold team doctor --target .
```

Use `team sync` after team knowledge, agents, skills, or policy changes. Use `team doctor` before a
first agentic coding session to confirm the local project sees the shared assets.

## Trust model

Team manifest content is third-party input. `coding-scaffold team sync`
treats every remote as untrusted: imports land under
`.coding-scaffold/team/sources/<kind>/<slug>/`, never inside your curated
`.coding-scaffold/knowledge/` tree. Review imported markdown before
linking it from your own pages.

`file://` and local-path remotes require `--allow-local` so a teammate's
manifest cannot redirect a sync at an arbitrary directory on your
machine without explicit consent.
