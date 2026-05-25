# OpenClaude Adapter

OpenClaude support is intentionally lightweight because the project moves quickly. Use this as a
profile checklist rather than a locked config format.

## Install

```bash
npm install -g @gitlawb/openclaude
openclaude
```

## Suggested Profiles

- Routine/editing model: `${weak}`
- Heavy-lift/review model: `${strong}`
- Local endpoint: use Ollama or another OpenAI-compatible endpoint when available.

Inside OpenClaude, run `/provider` and configure the provider profile to match these values. Keep
real API keys in `.coding-scaffold/.env.local` or the tool's secure login flow, not in committed
files.
