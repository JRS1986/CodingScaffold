# Native contract fixtures

Reviewed 2026-09-19. These are small, manually reviewed examples of the fields we
generate, not complete copies of upstream schemas. Tests run offline; no fixture
commands or MCP endpoints are executed.

- Codex config: https://learn.chatgpt.com/docs/config-file/config-reference
- Codex hooks: https://learn.chatgpt.com/docs/hooks
- Claude settings: https://code.claude.com/docs/en/settings
- Claude MCP: https://code.claude.com/docs/en/mcp#project-scope
- Claude hooks: https://code.claude.com/docs/en/hooks
- OpenCode schema: https://opencode.ai/config.json
- Skills: https://agentskills.io/specification

When upstream changes, review the actual fields first, then update these fixtures,
the adapters, compatibility review metadata, and migration documentation together.
Do not regenerate expected fixtures from the implementation under test.
