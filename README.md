# CodingScaffold

ROUTE-42 | Festo Coding Challenge style | local-first coding scaffold

CodingScaffold is a local-first bootstrapper for AI-assisted coding environments. Clone it, install
it into a venv, run the setup wizard in your project, and get project-local configuration plus a
short guide to AI coding skills. It detects local and cloud providers and writes config hints for
tools such as OpenCode, OpenClaude-style CLIs, Ollama, OpenAI-compatible servers, and optional
RouteLLM routing.

The default posture is privacy-friendly: local models first, cloud providers only when keys or
authenticated CLIs are present.

## Festo Coding Challenge Style

The scaffold is an efficient coder enablement tool first. The Festo Coding Challenge-inspired
writing style is reserved for onboarding and beginner mode: second-person adventure, digital-archive
framing, a small AI companion, corrupted setup crystals, and concrete engineering tasks disguised as
portal repairs. Pop-culture references are signal words: ROUTE-42 for suspicious routing,
"Great Scott!" for timeline-risk refactors, protocol-droid clarity for handoffs, and hyperspace as a
metaphor for cloud escalation.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
coding-scaffold wizard --target /path/to/your/project
```

For WSL/Linux the commands are the same. On Windows PowerShell outside WSL, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

## Setup Wizard

Use the wizard in any project you want to prepare:

```bash
coding-scaffold wizard --target ~/dev/my-project
```

For a guided first-project experience:

```bash
coding-scaffold wizard --target ~/dev/my-project --beginner
```

For scripts or templates:

```bash
coding-scaffold init --target ~/dev/my-project --language python --non-interactive
```

## What It Creates

`coding-scaffold init` writes a `.coding-scaffold/` folder in the target project:

- `project.json`: project language, target, repo path, privacy mode, and user preferences.
- `hardware.json`: CPU, RAM, OS, WSL status, detected GPU/VRAM, and llmfit availability.
- `providers.json`: local and cloud providers detected from CLIs and environment variables.
- `routing.json`: local-first routing policy and selected weak/strong model candidates.
- `theme.json`: Festo TN-AI style tokens, copy voice, motifs, and reference labels.
- `GETTING_STARTED.md`: how to use the scaffold after cloning and running the wizard.
- `SKILLS.md`: quick intro to efficient AI coding skills.
- `BEGINNER_PATH.md`: optional Challenge-style first-project guide when using beginner mode.
- `THEME.md`: human-readable style guide for agents and reviewers.
- `opencode.json`: a portable provider/model hint file for OpenCode-style tools.
- `openclaude.json`: equivalent hints for OpenClaude-style tools.
- `routellm.config.yaml`: optional RouteLLM server config when a strong/weak pair exists.
- `AGENTS.md`: project-specific operating notes for coding agents.

## Suggested Flow

1. Run `coding-scaffold probe` to see what the machine can realistically host.
2. Install a local runtime if needed, usually Ollama, llama.cpp, LM Studio, vLLM, or MLX on Apple
   Silicon.
3. Install `llmfit` if you want a deeper model-fit ranking:

   ```bash
   brew install llmfit
   llmfit
   ```

4. Run `coding-scaffold init` in each codebase you want to prepare.
5. Point OpenCode/OpenClaude at the generated provider hints, or start RouteLLM:

   ```bash
   python -m pip install -e ".[routellm]"
   python -m routellm.openai_server --routers mf --config .coding-scaffold/routellm.config.yaml
   ```

## Notes On Models

The scaffold keeps model names configurable because model availability changes quickly. It seeds a
conservative catalog around Qwen Coder, DeepSeek Coder, Codestral, StarCoder2, and cloud fallbacks.
If you prefer a specific current model, such as a Qwen 40B-class coder, enter it during intake or
pass it non-interactively:

```bash
coding-scaffold init --preferred-local-model "qwen/qwen3-coder-40b"
```

## Commands

```bash
coding-scaffold probe --json
coding-scaffold wizard --target ~/dev/my-project --beginner
coding-scaffold init --target ~/dev/my-project --language python --non-interactive
coding-scaffold doctor
```

## Design Goals

- Cross-platform Linux and WSL behavior.
- No secret collection; the scaffold only records whether credentials appear available.
- Local-first routing with cloud escalation when explicitly available.
- Small, reviewable Python modules with minimal dependencies.
- Generated config that is transparent and easy to edit by hand.
