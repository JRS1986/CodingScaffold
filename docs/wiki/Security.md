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
