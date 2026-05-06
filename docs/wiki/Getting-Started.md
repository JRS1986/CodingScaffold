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
first-session documentation.

If you need project-local credentials, create an ignored template and fill only the providers you
intend to use:

```bash
coding-scaffold credentials --target . --format env
```

## Install OpenCode

OpenCode is the recommended default adapter for the first team rollout.

```bash
curl -fsSL https://opencode.ai/install | bash
coding-scaffold adapt --target . --tool opencode
opencode
```

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
