# Hermes Adapter

Hermes is a broader autonomous agent harness with terminal backends, skills, memory, MCP, and
messaging integrations. Use it as a project-aware coding harness only after its tool permissions,
runtime backend, and model profile are configured deliberately.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes setup
hermes
```

If your environment prefers Python isolation, use `pipx install hermes-agent`.

## Suggested Profiles

- Routine/editing model: `${weak}`
- Heavy-lift/review model: `${strong}`
- Local endpoint: use Ollama, vLLM, llama.cpp, or another OpenAI-compatible endpoint when available.

Run `hermes model`, `hermes tools`, and `hermes env` before the first project session. Keep project
guidance in `AGENTS.md` and `.coding-scaffold/AGENTS.md`, and keep real API keys in
`.coding-scaffold/.env.local` or Hermes' own credential flow, not in committed files.

## First Project Prompt

```text
Inspect this repository without editing. Identify the language, run command, test command, main
code paths, and one small safe improvement. Then wait for confirmation before changing files.
```
