# Getting Started

This page walks through the first useful session. The goal is not to configure every advanced
backend immediately; the goal is to make one small, inspected, verified change.

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
and proposes one safe improvement.

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

