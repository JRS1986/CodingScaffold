# Local Credentials

Credentials are intentionally local. The scaffold writes examples and an ignore file, but it never
asks you to paste real keys into committed project files.

## Recommended Path

Create a local env file:

```bash
coding-scaffold credentials --target . --format env
```

Then fill `.coding-scaffold/.env.local` with only the providers you intend to use.

For JSON-based tooling:

```bash
coding-scaffold credentials --target . --format json
```

This creates `.coding-scaffold/credentials.local.json`.

## Supported Keys

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and optional `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_AI_API_KEY`, `AZURE_AI_ENDPOINT`, optional `AZURE_AI_MODEL`, and optional
  `AZURE_AI_MODEL_FAMILY`
- Azure AI Services or Cognitive Services aliases: `AZURE_AI_SERVICES_KEY`,
  `AZURE_AI_SERVICES_ENDPOINT`, `AZURE_COGNITIVE_SERVICES_KEY`, and
  `AZURE_COGNITIVE_SERVICES_ENDPOINT`
- `OPENROUTER_API_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `GITHUB_TOKEN` or `GH_TOKEN`

## Safety Rules

- Do not commit `.env.local` or `credentials.local.json`.
- Prefer project-local credentials over shell-global exports when comparing providers.
- Use `coding-scaffold probe --target .` to verify which providers appear configured.
- If a provider offers device login, prefer that over long-lived plaintext keys.

## Azure Model Families

Azure is treated as a provider endpoint, not a model family. If your Azure gateway serves OpenAI
models, set `AZURE_OPENAI_*` or set `AZURE_AI_MODEL_FAMILY=openai`. If it serves Anthropic models,
set `AZURE_AI_MODEL_FAMILY=anthropic`. Skills and agents can then ask for `routine` or
`heavy-lift` without caring whether the request travels through Azure, OpenAI directly, Anthropic
directly, or a local OpenAI-compatible endpoint.

Azure endpoint and deployment values are treated as sensitive. The
generated `providers.json` and adapter configs contain a placeholder; the
real values live only in `.env.local` and are resolved at agent start.
