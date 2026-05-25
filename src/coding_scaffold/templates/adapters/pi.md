# Pi Adapter

Pi is a minimal terminal coding harness. It loads `AGENTS.md`/`CLAUDE.md` project instructions,
supports slash commands and sessions, and can be extended with TypeScript extensions, skills,
prompt templates, themes, and Pi packages.

## Install

```bash
npm install -g @earendil-works/pi-coding-agent
pi
```

## Suggested Profiles

- Routine/editing model: `${weak}`
- Heavy-lift/review model: `${strong}`
- Local endpoint: use an OpenAI-compatible local endpoint when available.

Authenticate with `/login` for subscription providers or API-key providers, or set environment
variables from `.coding-scaffold/.env.local` before launching `pi`. Restart Pi or run `/reload`
after changing project instruction files.

## First Project Prompt

```text
Summarize this repository, tell me how to run its checks, and recommend one small safe change. Do
not edit files yet.
```
