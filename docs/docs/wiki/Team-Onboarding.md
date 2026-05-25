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
writes `.coding-scaffold/team-provenance.json`. Pin a reviewed manifest when rollout needs a
stable baseline:

```bash
coding-scaffold team connect \
  --manifest https://github.com/acme/platform-ai-onboarding.git \
  --to-version 1.2.0 \
  --to-ref 7f4c2a1
```

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

Manifests use semantic versions:

```json
{
  "manifest_schema_version": 1,
  "manifest_version": "1.0.0",
  "min_scaffold_version": "0.5.0",
  "team": "platform-api"
}
```

Increment `manifest_version` when team norms change. Use patch versions for clarifications, minor
versions for additive guidance, and major versions for breaking policy or layout changes.
`team sync` refuses a manifest whose `min_scaffold_version` is newer than the installed
CodingScaffold and records the applied manifest version plus source ref in
`.coding-scaffold/team-provenance.json`.

## Sync Model

The default sync mode is copy:

- shared knowledge is copied or cloned to `.coding-scaffold/team/sources/knowledge/<slug>/`
- skills are copied to `.coding-scaffold/skills`
- agents are copied to `.opencode/agents`
- policy is copied to `.coding-scaffold/policy/imported`
- configs are copied to `.coding-scaffold/configs`

Copy mode is intentionally boring. It works offline after sync, is easy to inspect in Git, and
avoids surprising submodule or symlink behavior for new joiners.

Precedence is explicit, lowest to highest:

1. CodingScaffold defaults.
2. Parent org or unit manifest imported through `extends`.
3. Team manifest.
4. Repo-local overrides in `.coding-scaffold/policy/`, `.coding-scaffold/knowledge/local/`,
   `.coding-scaffold/skills/`, and `.opencode/agents/`.
5. Per-command flags.

When an imported artifact would overwrite a different local file, sync keeps the local file and
writes a `.conflict` sidecar containing the team version. `team doctor` reports these as local
deviations from team defaults.

Manifests can inherit from a parent:

```json
{
  "extends": "https://github.com/acme/org-ai-onboarding.git",
  "team": "platform-api",
  "mcp": {
    "allowlist": ["filesystem"]
  }
}
```

Children may tighten an inherited MCP allowlist, but cannot loosen it unless the parent explicitly
marks the allowlist as relaxable:

```json
{
  "mcp": {
    "allowlist": ["filesystem", "github"],
    "inheritable": {
      "allowlist": "relax"
    }
  }
}
```

## Commands

```bash
coding-scaffold team init --target .
coding-scaffold team connect --target . --manifest <file-or-git-repo>
coding-scaffold team sync --target . --to-version 1.2.0
coding-scaffold team doctor --target .
coding-scaffold team doctor --target . --format json
coding-scaffold team push --target . --dry-run
coding-scaffold team push --target . --open-pr
```

Use `team sync` after team knowledge, agents, skills, or policy changes. Use `team doctor` before a
first agentic coding session to confirm the local project sees the shared assets.

Use `team push --dry-run` to see local skills, team knowledge, or policy files that differ from the
imported manifest. Running `team push` writes a reviewable nomination bundle under
`.coding-scaffold/team/outbox/`; it does not commit or push upstream. Pass `--open-pr` to attempt a
draft PR against a GitHub-hosted manifest repo. If GitHub, `gh`, auth, clone, push, or PR creation is
unavailable, the command keeps the outbox bundle and prints a warning.

## Trust model

Team manifest content is third-party input. `coding-scaffold team sync`
treats every remote as untrusted: imports land under
`.coding-scaffold/team/sources/<kind>/<slug>/`, never inside your curated
`.coding-scaffold/knowledge/` tree. Review imported markdown before
linking it from your own pages.

`file://` and local-path remotes require `--allow-local` so a teammate's
manifest cannot redirect a sync at an arbitrary directory on your
machine without explicit consent.
