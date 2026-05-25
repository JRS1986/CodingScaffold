# FAQ

## Is CodingScaffold a coding agent?

No. It is a scaffold that prepares a project for coding agents, model guidance, team knowledge,
policy, and onboarding. It is not a replacement for Claude Code, Codex, OpenCode, Cursor, Copilot,
Hermes, or Pi.

## Do I need an LLM for the first start?

No. Setup, hardware probe, credential templates, adapter generation, and `tools select-model`
recommendations work without calling a model. You need an LLM only when a coding tool such as
OpenCode or OpenClaude starts an actual agent session.

## What should I run first?

Run `coding-scaffold doctor --target .`. It surveys the repo and recommends the next 1-3 commands.
If you want the smallest useful demo, run `coding-scaffold pilot --target . --tool opencode` next
and follow the printed recipe.

If the CLI vocabulary is unfamiliar, run `coding-scaffold tour` first — a read-only five-screen
walkthrough of what the tool does, the artifact families, and where to go next. Definitions for
every term live in the [Glossary](./Glossary.md).

## Can I get a focused recipe for my job (security, team lead, …)?

Yes. Pass `--persona {beginner,control,security,team-lead}` to `doctor` or `pilot`. A security
reviewer running `doctor --persona security` sees policy / MCP / permissions surfaced first
instead of the full firehose; a team lead gets a manifest / knowledge / skills recipe. The four
persona paths are documented in [Team Rollout](./Team-Rollout.md#persona-paths).

## A command failed and I don't know what to do — where do I look?

Every CLI failure path prints a three-line block: `error: <cause>` / `next: <one concrete
recovery step>` / `see: <optional wiki link>`. Read the `next:` line first. If you want to
understand the recurring failure modes (missing tool, untouched .env, eval on empty repo,
manifest version mismatch), the [Errors and Recovery](./Errors-and-Recovery.md) page
enumerates them.

## How do I know what I can build automation on?

Every top-level command in `coding-scaffold --help` carries a `[stable]` / `[preview]` /
`[experimental]` marker. The [Stability](./Stability.md) page defines the deprecation and
breaking-change contract for each marker — depend on `[stable]` freely; pin a version
when depending on `[preview]`; treat `[experimental]` as exploratory only.

## How do I upgrade a project after a new release?

`coding-scaffold setup update --target .` refreshes generated files without losing your edits.
Unchanged files are rewritten in place; edited files get a `.new` sidecar so you can merge.
The full upgrade contract — `.new` reconciliation recipe, rollback, version pinning, how to
read the CHANGELOG's Breaking section — is in [Upgrading](./Upgrading.md).

## Does setup install tools?

Yes, when it is running interactively and the selected coding environment is missing. It asks before
installing. You can also run `coding-scaffold setup tool --tool opencode` to validate the tool, or
add `--install` to `setup tool` to install a missing tool intentionally. If `pilot` prints a
`setup run` recipe for a missing tool, it uses `--install-tools`.

## Does the scaffold install optional add-ons too?

Yes. Use `coding-scaffold setup addon --addon llmfit`, `routellm`, `open-multi-agent`,
`obsidian`, or `caveman-compression`. Setup can also offer add-ons interactively. RouteLLM
installs into the active Python environment, Open Multi-Agent installs into the target Node.js
project, Caveman Compression is cloned under `.coding-scaffold/tools/` as an optional external
engine, and Obsidian remains manual on WSL because it is a desktop app.

## Can setup configure the shared knowledge remote?

Yes. Use `coding-scaffold setup knowledge --target . --backend obsidian --shared-remote <repo>`.
Setup can also ask for this during setup. The remote URL is metadata only; credentials and
tokens stay local.

## Can I refresh generated files later?

Yes. Use `coding-scaffold setup update --target .`. The command re-detects hardware and providers,
recreates generated scaffold files, updates files that still match their last generated checksum,
and writes `.new` files next to anything you edited locally.

## Does it require cloud APIs?

No. It can work local-only. Cloud providers are used only when credentials are configured and the
project privacy mode allows it.

## Does it store secrets?

No. It writes ignored templates such as `.coding-scaffold/.env.local`, but it does not commit,
print, or collect secret values.

## Why not just use GitHub Copilot?

Copilot is useful for completion and chat. CodingScaffold focuses on agentic workflows: inspect,
plan, edit, verify, review, and preserve reusable team habits.

## Why not just install a coding agent directly?

You should install and use the coding agent your team likes. CodingScaffold is the repo layer around
that agent: it generates language-aware and tool-specific guidance, points the agent at the right
local context, names verification habits, and gives the team a shared knowledge structure. The agent
does the coding work; CodingScaffold helps the project remember how that work should happen.

## Does it automatically turn chats into wiki pages?

No. Today it provides session traces, raw note folders, curated wiki pages, and
`knowledge distill --review` proposals. Durable team knowledge should be compressed, abstracted,
reviewed Markdown, not raw chat logs. If automatic ingestion is added later, it should summarize,
redact, deduplicate, and propose updates for review before they become team wiki pages.

Generated tool adapters can still remind the active coding agent to run a "knowledge nudge" at the
end of a substantial chat. That nudge uses the coding environment's configured model, not
CodingScaffold, and writes reviewable candidates such as session-trace bullets or `.new` proposal
files instead of silently updating curated knowledge.

## Why Markdown for knowledge?

Markdown works in Git, GitHub, GitLab, editors, Obsidian, and memory tools. It is easy to review
and easy to migrate.

## Can CodingScaffold avoid context poisoning?

It can catch the easy cases early. Run `coding-scaffold context budget --target . --source team`
to estimate whether shared knowledge, skills, policy, and agents are getting too large for a healthy
session. Run `coding-scaffold context compress --target . --source knowledge` to create optional
compressed sidecars with the built-in compressor. Use `context budget --prefer compressed` to
estimate a sidecar-first session. Still use human judgment: narrow retrieval, keep policy
uncompressed, and open a fresh session when history has become stale.

## Should every team use RouteLLM or Open Multi-Agent?

No. Start with setup, OpenCode, skills, and knowledge. Add RouteLLM or Open Multi-Agent only
after the team has a proven need.

## Is CodingScaffold a security boundary?

No. Policy packs and adapter settings are guardrails. Use company identity policy, provider
controls, network rules, secret scanning, CI, and code review for enforcement.
