# CodingScaffold Wiki

CodingScaffold helps teams move from “AI autocomplete” to reviewable agentic coding workflows. The
README is the quick front door; this wiki explains the project in more depth and gives teams a
shared rollout playbook.

## What CodingScaffold Does

CodingScaffold creates project-local guidance and lightweight configuration for:

- local-first model routing
- provider and credential discovery
- prompt-based model selection
- OpenCode and OpenClaude adapters
- reusable team skills
- agent orchestration profiles
- shared Markdown, Obsidian, or MemPalace-ready knowledge bases
- optional RouteLLM and Open Multi-Agent workflows

It does not collect secrets, does not require one model vendor, and does not force a hosted service
into the workflow.

## Recommended Reading

1. [[Getting Started]]: install, run the wizard, and complete the first agentic coding session.
2. [[Core Concepts]]: understand the main ideas before introducing it to a team.
3. [[Model Selection and Providers]]: local-first routing, Azure/OpenAI/Anthropic abstraction, and auto mode.
4. [[Skills and Agents]]: how teams turn good workflows into reusable assets.
5. [[Knowledge Base]]: Markdown, Obsidian, MemPalace, and shared GitHub/GitLab memory.
6. [[Team Rollout]]: a practical adoption plan for a team workshop or internal pilot.

## Design Posture

CodingScaffold is intentionally boring where that helps:

- Git is the sharing mechanism.
- Markdown is the source of truth.
- Local credentials stay local.
- Generated files are readable and editable by hand.
- Advanced orchestration is optional and comes after the team validates the workflow.

