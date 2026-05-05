# CodingScaffold

Your local-first coding scaffold

CodingScaffold helps teams prepare a project for AI-assisted coding without locking themselves into
one model provider. Clone it, install it into a venv, run the setup wizard inside a codebase, and it
will create project-local guidance for model routing, provider setup, agent behavior, and practical
AI coding habits.

The default posture is privacy-friendly: local models first, cloud providers only when credentials
or authenticated CLIs are already available. For experienced users, the output stays direct and
operational. For beginners, the wizard can also generate a more guided first-project path that makes
the first steps less intimidating without hiding what is happening.

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

## Credentials

Keep credentials local to the project and out of Git. The wizard writes examples and ignore rules
inside `.coding-scaffold/`; real keys go into local-only files.

```bash
coding-scaffold credentials --target ~/dev/my-project --format env
```

This creates `.coding-scaffold/.env.local`.

```bash
coding-scaffold credentials --target ~/dev/my-project --format json
```

This creates `.coding-scaffold/credentials.local.json`.

Both files are ignored by the generated `.coding-scaffold/.gitignore`. Run
`coding-scaffold probe --target ~/dev/my-project` to check which providers are configured without
printing secret values.

## Coding Tool Adapters

CodingScaffold does not require one coding agent. It writes adapter hints for current tools and is
designed to stay open for whatever arrives next.

OpenCode is the recommended default for most teams today. It appears more mature: official install
paths, terminal/desktop/IDE surfaces, LSP awareness, multi-session workflows, many providers,
local-model support, and GitHub Copilot sign-in.

```bash
curl -fsSL https://opencode.ai/install | bash
opencode
```

OpenClaude is worth tracking if your team wants to experiment with a fast-moving, Claude-Code-like
community workflow across OpenAI-compatible APIs, Ollama, GitHub Models, MCP, slash commands, and
provider profiles. Treat it as experimental and review provenance, licensing, and security before
standardizing on it.

```bash
npm install -g @gitlawb/openclaude
openclaude
```

Generated adapter hints live in `.coding-scaffold/opencode.json`,
`.coding-scaffold/openclaude.json`, and `.coding-scaffold/TOOLS.md`.

## What It Creates

`coding-scaffold init` writes a `.coding-scaffold/` folder in the target project:

- `.gitignore`: keeps generated local credential files out of Git.
- `.env.example`: env-based credential template.
- `credentials.example.json`: JSON-based credential template.
- `CREDENTIALS.md`: local credential setup guide.
- `TOOLS.md`: OpenCode/OpenClaude installation and adapter guidance.
- `project.json`: project language, target, repo path, privacy mode, and user preferences.
- `hardware.json`: CPU, RAM, OS, WSL status, detected GPU/VRAM, and llmfit availability.
- `providers.json`: local and cloud providers detected from CLIs and environment variables.
- `routing.json`: local-first routing policy and selected weak/strong model candidates.
- `GETTING_STARTED.md`: how to use the scaffold after cloning and running the wizard.
- `SKILLS.md`: quick intro to efficient AI coding skills.
- `BEGINNER_PATH.md`: optional first-project guide when using beginner mode.
- `THEME.md`: human-readable onboarding voice guide for agents and reviewers.
- `theme.json`: onboarding style tokens used by generated beginner guidance.
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
coding-scaffold credentials --target ~/dev/my-project --format env
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
