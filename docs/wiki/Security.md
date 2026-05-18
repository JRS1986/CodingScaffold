# Security

CodingScaffold writes reviewable guardrails. It is not a security boundary by itself.

## Company Checklist

- Keep real credentials in ignored local files or the coding tool's secure auth flow.
- Review provider allow/deny lists before using cloud models.
- Treat MCP servers as code execution and data-access surfaces.
- Keep shared knowledge free of secrets, customer data, private incidents, and unreleased strategy.
- Review skills, agents, policy packs, and generated config by pull request.
- Back local policy with company identity policy, endpoint allowlists, network controls, secret
  scanning, and CI.

## Credentials

`coding-scaffold credentials` writes templates such as `.coding-scaffold/.env.local`; it does not
collect, print, or commit secret values. Generated adapter config should point to provider or tool
authentication flows instead of embedding keys.

## Policy Packs

Policy packs can disable sharing, prefer local providers, ask before edit/bash actions, and disable
named MCP servers where the target tool supports it. They reduce accidents, but enforcement belongs
in the underlying tool, identity layer, network, repository protections, and CI.

## Shared Knowledge

Raw notes should stay narrow and reviewable. Curated wiki pages should include owner,
`last_reviewed`, maturity, and `source_refs` so stale or unsourced guidance does not quietly become
agent default behavior.

## Threat Model

CodingScaffold is a bootstrap layer. Security depends on the underlying coding tool, the model
provider, the host OS, and team review discipline. Treat the items below as boundaries the scaffold
**does not** cross, with the mitigation the scaffold provides.

### Install scripts

`coding-scaffold setup tool` and `setup addon` can invoke third-party install commands
(`bash -lc "curl ... | bash"` for OpenCode and Hermes; `npm install -g` for Claude Code, Codex,
OpenClaude, Pi). When stdin is interactive, the scaffold prompts before installing. In
`--non-interactive` mode, installs run unattended with a 300-second timeout and captured output.

- **Risk:** the install URL is whatever the upstream project publishes; a compromised CDN affects
  every user.
- **Mitigation:** review the install URL each time the scaffold logs one; pin to a tool version
  when your environment supports it; prefer your distribution's package manager when available.

### MCP servers

MCP (Model Context Protocol) servers are code-execution and data-access surfaces. A configured
server can read files, run commands, and call out to external APIs on the agent's behalf.

- **Risk:** an MCP server installed by a teammate may exfiltrate repository contents or run
  arbitrary commands during an agent session.
- **Mitigation:** the OpenCode policy pack supports a disable list; review every entry under
  `mcp.<server>` in `opencode.json` before merging. Treat team-shared MCP configurations the same
  way you'd treat new CI plugins — by code review, not by trust.

### Local model runtimes

Ollama, LM Studio, and llama-server expose OpenAI-compatible endpoints on `127.0.0.1`. The
scaffold probes the endpoint before claiming a runtime is available.

- **Risk:** any process on the same host can call the local endpoint. A malicious local process
  could query the model with arbitrary prompts using your loaded weights.
- **Mitigation:** treat local-model endpoints as un-authenticated. Don't bind them to non-loopback
  interfaces. Local models are good for code that should not leave the machine; they are not a
  multi-tenant access control.

### Cloud providers

The scaffold generates provider records (`providers.json`) and adapter configs that name providers
by env var. API keys never enter generated files. Azure endpoint and deployment values are
redacted from serialized config because the subdomain typically encodes tenant identity.

- **Risk:** the act of using a cloud model sends prompt + context to that provider. Review the
  provider's data-retention and training-data policies before allowing it in a project.
- **Mitigation:** `policy --scope company` lets you set an explicit `enabled_providers` /
  `disabled_providers` list. Keep secrets in the tool's native auth flow when possible
  (GitHub Copilot sign-in, Anthropic OAuth, Azure managed identity).

### Generated policy

Policy packs are guardrail guidance, not enforcement. The underlying tool reads them as
configuration; nothing prevents the user from running the tool with a different config.

- **Risk:** a developer can bypass `share: disabled` or `permission.bash: ask` by editing
  `opencode.json` locally.
- **Mitigation:** back local policy with company controls — identity policy on the provider,
  network egress rules, secret scanning, repository protection rules, and CI checks. The scaffold
  surfaces what *should* be configured; only the platform can enforce it.

### Team manifest content

`team connect` and `team sync` pull markdown content from a remote manifest. Imports land under
`.coding-scaffold/team/sources/` (never in the user's curated `knowledge/`). Local-path and
`file://` remotes require `--allow-local`.

- **Risk:** a teammate's manifest can ship prompt-injection content disguised as a knowledge note,
  steering future agent sessions.
- **Mitigation:** team imports are third-party input. Review them before linking from your own
  curated knowledge tree. Treat the diff of `team/sources/` like a pull request — because that's
  what it is.

### Audit expectations

The scaffold is reviewable by design — generated files live in the repo and change via commits.
Auditors should expect:

- `git log` shows every change to generated config, policy, knowledge, and skills.
- `.env.local`, `credentials.local.json`, and similar files are git-ignored by the generated
  `.gitignore`.
- `scaffold-version.json` records the hashes of generated files; drift is detectable via
  `coding-scaffold setup update`.
- Sensitive runtime values (API keys, Azure endpoints/deployments) are not present in committed
  config; they live in `.env.local` and are resolved at agent-start time.

## What this scaffold does not promise

- It does not sandbox agent execution.
- It does not enforce network egress rules.
- It does not validate model output before it reaches your codebase.
- It does not detect prompt injection in team-imported knowledge.
- It does not encrypt anything in `.coding-scaffold/`; it relies on the host filesystem's controls.

Those responsibilities belong to the coding tool, the OS, the network layer, and the team's CI
and review process.
