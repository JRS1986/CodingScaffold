# Getting Started

This page walks through the first useful session. The goal is not to configure every advanced
backend immediately; the goal is to make one small, inspected, verified change.

## What Needs A Model?

The scaffold bootstrap does not need one. `coding-scaffold wizard`, `probe`, `credentials`,
`adapt`, and `select-model` run locally in Python. `select-model` classifies the text and recommends
a route; it does not send the prompt to an LLM.

The first LLM call happens when the coding adapter starts doing agent work, for example when
OpenCode runs `/first-session`. Before that step, OpenCode needs access to a model through a local
runtime, an authenticated CLI, or a cloud/API provider.

## Install

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

## Prepare A Project

```bash
coding-scaffold wizard --target ~/dev/my-project
cd ~/dev/my-project
```

The wizard writes `.coding-scaffold/` with project facts, provider hints, routing guidance, and
first-session documentation. It also asks which coding environment to use:

- `opencode`: default, recommended for the first rollout.
- `openclaude`: experimental option for teams tracking that workflow.
- `both`: generate both sets of guidance.
- `manual`: skip tool adapter generation and wire your own environment.

If the selected tool is missing and stdin is interactive, the wizard asks before installing it.
Nothing is installed silently. The wizard can also configure the knowledge backend and shared Git
remote during this setup phase.

If you need project-local credentials, create an ignored template and fill only the providers you
intend to use:

```bash
coding-scaffold credentials --target . --format env
```

Configure shared knowledge during setup:

```bash
coding-scaffold setup-knowledge --target . \
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
coding-scaffold setup-tool --tool opencode
coding-scaffold adapt --target . --tool opencode
opencode
```

Use `coding-scaffold setup-tool --tool opencode --install` when you want the CLI to install a
missing tool without a second prompt, for example in a prepared dev container.

## Optional Add-Ons

Use the same validate-or-install flow for optional pieces:

```bash
coding-scaffold setup-addon --target . --addon llmfit
coding-scaffold setup-addon --target . --addon obsidian
coding-scaffold setup-addon --target . --addon routellm
coding-scaffold setup-addon --target . --addon open-multi-agent
```

`llmfit` is useful early because it improves hardware-aware model choice. RouteLLM and Open
Multi-Agent are advanced; add them after the first agentic coding loop is working. Obsidian is a
desktop app, so WSL users should usually install it on Windows and open `.coding-scaffold/knowledge`
as a vault.

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
coding-scaffold knowledge --target . --backend obsidian
```
