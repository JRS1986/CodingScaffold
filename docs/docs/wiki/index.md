# CodingScaffold Wiki

CodingScaffold is a local-first onboarding, configuration, and governance scaffold for
AI-assisted software development teams. The README is the quick front door; this wiki explains the
project in more depth and gives teams a shared rollout playbook.

**New here?** Read the [Glossary](./Glossary.md) first — every term `doctor` prints
(artifact, persona, MCP, skill, manifest, scope, maturity) is defined in one place.

## What CodingScaffold Does

CodingScaffold creates project-local guidance and lightweight configuration for:

- local-first model guidance
- provider and credential discovery
- prompt-based model selection
- OpenCode, Claude Code, Codex, OpenClaude, Hermes, and Pi adapters
- reusable team skills
- agent orchestration profiles
- shared Markdown, HTML, Obsidian, or MemPalace-ready knowledge bases
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

Start with the smallest path that matches your job today:

| Need | Page | What you get |
| --- | --- | --- |
| Define a term you saw in `--help` | [Glossary](./Glossary.md) | One paragraph per term (artifact, persona, MCP, manifest, scope, ...). |
| First useful session | [Getting Started](./Getting-Started.md) | The `doctor` + `pilot` path and the first bounded agentic change. |
| Small-team pilot | [Team Rollout](./Team-Rollout.md) | A two-person rollout plan + the four persona paths surfaced by `--persona`. |
| Security/compliance review | [Security](./Security.md) | Credential, provider, MCP, policy, and trust-boundary notes. |
| Tool comparison | [Tool Adapters](./Tool-Adapters.md) | Capability matrix for OpenCode, Claude Code, Codex, OpenClaude, Hermes, and Pi. |
| Shared memory | [Knowledge Base](./Knowledge-Base.md) | Markdown, HTML, Obsidian, Foam, MemPalace, and shared Git workflows. |
| Upgrade a project | [Upgrading](./Upgrading.md) | What `setup update` does, the `.new` recipe, rollback, version pinning. |
| Decide what to depend on | [Stability](./Stability.md) | What `[stable]` / `[preview]` / `[experimental]` markers in `--help` promise. |
| Recover from a CLI failure | [Errors and Recovery](./Errors-and-Recovery.md) | The three-line error format and the recurring failure modes. |

Then use the reference pages when the need appears:

- [Core Concepts](./Core-Concepts.md): the vocabulary behind local-first scaffolding.
- [Model Selection and Providers](./Model-Selection-and-Providers.md): routine vs heavy-lift guidance.
- [Skills and Agents](./Skills-and-Agents.md): reusable playbooks and agent definitions.
- [Context Hygiene](./Context-Hygiene.md): context budgets, linting, and compression sidecars.
- [Team Onboarding](./Team-Onboarding.md): manifests for teams that already have shared assets.
- [Team Sync](./Team-Sync.md): sync precedence, cascade, versioning, and nomination pointers.
- [Policy Packs](./Policy-Packs.md): reviewable provider, sharing, permission, and MCP defaults.

## Design Posture

CodingScaffold is intentionally boring where that helps:

- Git is the sharing mechanism.
- Markdown is the source of truth.
- Local credentials stay local.
- Generated files are readable and editable by hand.
- Advanced orchestration is optional and comes after the team validates the workflow.
