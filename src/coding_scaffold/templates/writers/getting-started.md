# Getting Started

CodingScaffold is meant to be installed once as a global command, then run inside whichever project
you want to prepare for AI-assisted coding.

The goal is not just "better autocomplete." The goal is a controlled workflow where agents inspect,
plan, edit, verify, review, and preserve the best team habits as reusable skills.

## Fast Path

```bash
uv tool install git+https://github.com/JRS1986/CodingScaffold.git
coding-scaffold setup run --target /path/to/your/project
```

If you do not use `uv`, install the same isolated command with
`pipx install git+https://github.com/JRS1986/CodingScaffold.git`.

After installation, run `coding-scaffold` from the project you are preparing. You should not need
to activate a virtual environment from the CodingScaffold source checkout.

## What Setup Did Here

Project language: `${language}`
Project target: `${project_target}`
Privacy mode: `${privacy}`
Coding environment: `${tool}`
Guidance mode: `${mode}`
Routine model: `${weak_model}`
Heavy-lift model: `${strong_model}`

## Daily Use

1. ${setup_hint}
2. Start OpenCode with `opencode`, Claude Code with `claude`, Codex with `codex`, OpenClaude with `openclaude`, Hermes with `hermes`, Pi with `pi`, or your manually selected tool.
3. Run `/first-session` to inspect without editing.
4. Run `/agentic-change` for one small explorer -> implementer -> reviewer loop.
5. Read the verification output and review findings yourself.
6. Recheck the route when an answer feels wrong: restate the task, add context, or use the stronger model.
7. Ask `coding-scaffold tools select-model --target . --prompt "..."` when the right model route is unclear.
8. Configure local provider keys with `CREDENTIALS.md`.
9. Use `coding-scaffold setup addon --target . --addon llmfit` for deeper hardware-aware model sizing.
10. Check context health with `coding-scaffold context budget --target . --source team`.
11. Create repeatable project skills with `coding-scaffold skill --target . --adapter opencode --name "..."`.
12. Create shared team memory with `coding-scaffold setup knowledge --target . --backend markdown`.
13. Improve skills when they miss context, overreach, or fail to verify correctly.
14. Compress optional reference notes with `coding-scaffold context compress --target . --source knowledge`; use `--engine caveman` only after installing the optional Caveman Compression add-on.
15. Graduate proven skills into Open Multi-Agent workflows with `coding-scaffold setup addon --target . --addon open-multi-agent` and `coding-scaffold tools workflow --target . --backend open-multi-agent`.
