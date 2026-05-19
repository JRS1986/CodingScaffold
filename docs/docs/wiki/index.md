# CodingScaffold Wiki

CodingScaffold is a local-first onboarding, configuration, and governance scaffold for
AI-assisted software development teams. The README is the quick front door; this wiki explains the
project in more depth and gives teams a shared rollout playbook.

## What CodingScaffold Does

CodingScaffold creates project-local guidance and lightweight configuration for:

- local-first model guidance
- provider and credential discovery
- prompt-based model selection
- OpenCode, Claude Code, Codex, OpenClaude, Hermes, and Pi adapters
- reusable team skills
- agent orchestration profiles
- shared Markdown, Obsidian, or MemPalace-ready knowledge bases
- experienced-team onboarding manifests
- policy packs for provider, sharing, permission, and MCP defaults
- context budgeting and optional compression sidecars
- optional RouteLLM and Open Multi-Agent workflows

It does not collect secrets, does not require one model vendor, and does not force a hosted service
into the workflow.

It is not a coding agent, a replacement for existing coding tools, an autonomous development
platform, a security boundary, or a universal model router.

## First-Start Rule

CodingScaffold itself can start without an LLM. Setup, hardware probe, credential templates,
adapter generation, and `tools select-model` command are local Python workflows. The first actual model
call happens later, inside the coding tool, when a developer runs an agent command such as
`/first-session` in OpenCode.

## Recommended Reading

1. [Getting Started](./Getting-Started.md): install, run setup, refresh safely, and complete the first agentic coding session.
2. [Core Concepts](./Core-Concepts.md): understand the main ideas before introducing it to a team.
3. [Model Selection and Providers](./Model-Selection-and-Providers.md): local-first routing, Azure/OpenAI/Anthropic abstraction, and auto mode.
4. [Skills and Agents](./Skills-and-Agents.md): how teams turn good workflows into reusable assets.
5. [Knowledge Base](./Knowledge-Base.md): Markdown, Obsidian, MemPalace, and shared GitHub/GitLab memory.
6. [Context Hygiene](./Context-Hygiene.md): avoid oversized or stale context and add optional compression.
7. [Team Onboarding](./Team-Onboarding.md): connect new developers to shared knowledge, skills, agents, and policy.
8. [Policy Packs](./Policy-Packs.md): local OpenCode policy defaults for company/unit/team rollout.
9. [Team Rollout](./Team-Rollout.md): a practical adoption plan for a team workshop or internal pilot.

## Design Posture

CodingScaffold is intentionally boring where that helps:

- Git is the sharing mechanism.
- Markdown is the source of truth.
- Local credentials stay local.
- Generated files are readable and editable by hand.
- Advanced orchestration is optional and comes after the team validates the workflow.
