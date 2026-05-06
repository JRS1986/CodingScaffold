# FAQ

## Is CodingScaffold a coding agent?

No. It is a scaffold that prepares a project for coding agents and local-first model routing.

## Do I need an LLM for the first start?

No. The wizard, hardware probe, credential templates, adapter generation, and `select-model`
recommendations work without calling a model. You need an LLM only when a coding tool such as
OpenCode or OpenClaude starts an actual agent session.

## Does it require cloud APIs?

No. It can work local-only. Cloud providers are used only when credentials are configured and the
project privacy mode allows it.

## Does it store secrets?

No. It writes ignored templates such as `.coding-scaffold/.env.local`, but it does not commit,
print, or collect secret values.

## Why not just use GitHub Copilot?

Copilot is useful for completion and chat. CodingScaffold focuses on agentic workflows: inspect,
plan, edit, verify, review, and preserve reusable team habits.

## Why Markdown for knowledge?

Markdown works in Git, GitHub, GitLab, editors, Obsidian, and memory tools. It is easy to review
and easy to migrate.

## Should every team use RouteLLM or Open Multi-Agent?

No. Start with the wizard, OpenCode, skills, and knowledge. Add RouteLLM or Open Multi-Agent only
after the team has a proven need.
