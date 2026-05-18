# Getting Started

This page walks through the first useful session. The goal is not to configure every advanced
backend immediately; the goal is to make one small, inspected, verified change.

## What Needs A Model?

The scaffold bootstrap does not need one. `coding-scaffold setup run`, `probe`, `credentials`,
`tools adapt`, and `tools select-model` run locally in Python. `tools select-model` classifies the text and recommends
a route; it does not send the prompt to an LLM.

The first LLM call happens when the coding adapter starts doing agent work, for example when
OpenCode runs `/first-session`. Before that step, OpenCode needs access to a model through a local
runtime, an authenticated CLI, or a cloud/API provider.

## Install

Recommended with uv:

```bash
git clone https://github.com/JRS1986/CodingScaffold.git
cd CodingScaffold
uv venv
source .venv/bin/activate
uv sync --extra dev
```

Classic venv/pip works too:

```bash
git clone https://github.com/JRS1986/CodingScaffold.git
cd CodingScaffold
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows PowerShell outside WSL:

```powershell
.venv\Scripts\Activate.ps1
```

`uv.lock` is committed. Use `uv sync --extra dev` for reproducible development and CI parity.

## Prepare A Project

```bash
coding-scaffold setup run --target ~/dev/my-project
cd ~/dev/my-project
```

Setup writes `.coding-scaffold/` with project facts, provider hints, routing guidance, and
first-session documentation. It also asks which coding environment to use:

- `opencode`: default, recommended for the first rollout.
- `claude-code`: native Claude Code project guidance and settings.
- `codex`: native Codex project guidance and skills.
- `openclaude`: experimental option for teams tracking that workflow.
- `hermes`: broader autonomous agent harness with memory, skills, MCP, and backend choices.
- `pi`: minimal terminal coding harness with project instructions, sessions, and extensions.
- `both`: generate both sets of guidance.
- `manual`: skip tool adapter generation and wire your own environment.

If the selected tool is missing and stdin is interactive, setup asks before installing it.
Nothing is installed silently. Setup can also configure the knowledge backend and shared Git
remote during this setup phase.

When CodingScaffold itself improves later, refresh generated files without overwriting local edits:

```bash
coding-scaffold setup update --target .
```

Files that still match the last generated checksum are updated in place. Files you edited are left
alone and the newer generated version is staged next to them as `.new`.

If you need project-local credentials, create an ignored template and fill only the providers you
intend to use:

```bash
coding-scaffold credentials --target . --format env
```

Configure shared knowledge during setup:

```bash
coding-scaffold setup knowledge --target . \
  --backend obsidian \
  --shared-remote https://github.com/acme/team-ai-knowledge.git
```

If you are joining an experienced team, prefer the team manifest:

```bash
coding-scaffold team connect --target . \
  --manifest https://github.com/acme/platform-ai-onboarding.git
coding-scaffold team doctor --target .
```

## Install OpenCode

OpenCode is the recommended default adapter for the first team rollout.

```bash
coding-scaffold setup tool --tool opencode
coding-scaffold tools adapt --target . --tool opencode
opencode
```

Use `coding-scaffold setup tool --tool opencode --install` when you want the CLI to install a
missing tool without a second prompt, for example in a prepared dev container.

## 10-Minute Happy Path

This is the first useful path for Lena, the curious coding newbie, and for a small team pilot. The
goal is not to enable every governance feature. The goal is one inspected repo, one named verifier,
and one tiny change the developer understands.

Use an existing repo and start with OpenCode:

```bash
coding-scaffold setup run --target ~/dev/my-project --mode beginner --tool opencode
cd ~/dev/my-project
coding-scaffold probe --target .
coding-scaffold context budget --target . --source knowledge
coding-scaffold setup tool --tool opencode
opencode
```

Inside OpenCode:

```text
/first-session
```

Then ask:

```text
Inspect the repo, identify the build/test commands, name the key files, and propose one small safe
improvement. Do not edit yet.
```

Continue only if the plan is understandable. For the first edit, keep the scope narrow:

```text
/agentic-change
```

Stop after the first bounded change and review:

- what files were inspected
- what files changed
- which command verifies the change
- whether any generated credential or provider file needs local-only handling
- whether the developer could explain the diff without trusting the agent blindly

For a team under 20 people, run this once with a second developer before adding a shared manifest.
When both sessions produce a repeatable shape, add the lightweight team layer:

```bash
coding-scaffold pr-template init --target .
coding-scaffold permissions write --target .
coding-scaffold knowledge create --target . --backend markdown
```

Leave RouteLLM, multi-agent workflows, large MCP setups, and enterprise policy layering for later.
They are useful once the team has a repeated workflow worth standardizing.

## Optional Add-Ons

Use the same validate-or-install flow for optional pieces:

```bash
coding-scaffold setup addon --target . --addon llmfit
coding-scaffold setup addon --target . --addon obsidian
coding-scaffold setup addon --target . --addon routellm
coding-scaffold setup addon --target . --addon open-multi-agent
coding-scaffold setup addon --target . --addon caveman-compression
```

`llmfit` is useful early because it improves hardware-aware model choice. RouteLLM and Open
Multi-Agent are advanced; add them after the first agentic coding loop is working. Obsidian is a
desktop app, so WSL users should usually install it on Windows and open `.coding-scaffold/knowledge`
as a vault. Context sidecars work without the Caveman add-on; install it only when you want to try
the upstream compression engine with `context compress --engine caveman`.

Inside OpenCode:

```text
/first-session
```

Expected result: the agent inspects before editing, identifies run/test commands, maps key files,
and proposes one safe improvement. This command is where a working LLM connection becomes required.

## Run One Agentic Loop

Inside OpenCode:

```text
/agentic-change
```

Expected result:

- explorer maps relevant files
- implementer makes a bounded change
- verification runs
- reviewer challenges the result
- you receive changed files, checks, findings, and follow-up

## Capture The Habit

If the loop helped, create a reusable skill:

```bash
coding-scaffold skill --target . --adapter opencode --name "Small Safe Improvement"
```

Then create a knowledge base to preserve decisions and useful patterns:

```bash
coding-scaffold knowledge create --target . --backend obsidian
```
