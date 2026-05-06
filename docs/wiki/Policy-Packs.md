# Policy Packs

Policy packs capture company, unit, department, or team defaults for AI-enabled coding. They are
reviewable local configuration, not a replacement for identity policy, network controls, or CI.

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

## Scope Strategy

- `company`: approved standards, approved providers, security and privacy defaults.
- `unit`: domain defaults, model families, reference architecture, shared provider constraints.
- `department`: system runbooks, local MCP choices, validated agent roles.
- `team`: project-specific instructions and permissions.

Change policy by pull request. A local policy file helps prevent accidents, but sensitive routing
rules should also be backed by credentials, endpoint allowlists, network controls, and CI checks.
