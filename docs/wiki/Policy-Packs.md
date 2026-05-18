# Policy Packs

Policy packs capture company, unit, department, or team defaults for AI-enabled coding. They are
reviewable local configuration, not a replacement for identity policy, network controls, or CI.
See [Security](Security.md) before using policy packs in company repositories.

## Generate A Policy

```bash
coding-scaffold policy --target ~/dev/my-project --scope company
```

This writes:

- `.coding-scaffold/policy/policy.json`
- `.coding-scaffold/policy/company.md`
- `.coding-scaffold/policy/opencode-policy.json`
- `opencode.json`

## OpenCode Defaults

The default policy is conservative:

- `share: disabled`
- `.coding-scaffold/policy/*.md` added as instructions
- edit and bash permissions set to `ask`
- optional provider allow/deny lists using OpenCode's `enabled_providers` and `disabled_providers`
- project MCP configuration kept empty unless named servers are explicitly disabled

Example with explicit provider and MCP controls:

```bash
coding-scaffold policy --target ~/dev/my-project \
  --scope company \
  --enable-provider ollama \
  --enable-provider azure-ai \
  --disable-provider openai \
  --disable-mcp-server jira
```

Provider IDs and MCP server names should match the effective OpenCode configuration used by the
team. If organization-wide tooling injects remote MCP servers, disable known servers by name and
verify the final config in the coding tool.

## Available Flags

- `--scope {company,unit,department,team}` — audience and ownership layer for this policy.
- `--share {disabled,manual,auto}` — OpenCode share-mode default. `disabled` is the default and
  matches the recommended posture for company repositories.
- `--adapter {none,opencode}` — pick which adapter the policy should configure.
- `--enable-provider <id>` / `--disable-provider <id>` — explicit allow/deny lists, repeatable.
- `--disable-mcp-server <name>` — block a named MCP server, repeatable.
- `--mcp {project-empty,inherit}` — start the project's `mcp` config empty or inherit existing.
- `--relaxed-permissions` — disable the default `permission.edit: ask` / `permission.bash: ask`
  gate. Pass this only when the team has deliberately decided that ask-before-action is too
  noisy; the default (strict) is recommended for company and team scopes.

Example with the share mode and permissions explicitly opted out of strict:

```bash
coding-scaffold policy --target ~/dev/my-project \
  --scope team \
  --share manual \
  --relaxed-permissions
```

## Scope Strategy

- `company`: approved standards, approved providers, security and privacy defaults.
- `unit`: domain defaults, model families, reference architecture, shared provider constraints.
- `department`: system runbooks, local MCP choices, validated agent roles.
- `team`: project-specific instructions and permissions.

Change policy by pull request. A local policy file helps prevent accidents, but sensitive routing
rules should also be backed by credentials, endpoint allowlists, network controls, and CI checks.
