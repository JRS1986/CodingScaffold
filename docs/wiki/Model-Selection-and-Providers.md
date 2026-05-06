# Model Selection and Providers

CodingScaffold separates model recommendation from request routing.

## Bootstrap Boundary

Model recommendation is available before any LLM is configured. CodingScaffold reads local project
metadata, hardware facts, credential presence, and the prompt text. It then recommends a route. It
does not proxy the prompt or call a provider.

Actual request routing happens later in the coding tool or an optional backend such as RouteLLM.

## Recommendation

Use `select-model` when you want an explainable routing suggestion:

```bash
coding-scaffold select-model --target ~/dev/my-project \
  --prompt "Review this authentication refactor for security regressions."
```

The command does not call a model. It classifies the task and reports:

- prompt profile
- route: `routine` or `heavy-lift`
- provider
- model family
- model or deployment
- confidence
- reasons

## Auto Mode

Use auto mode when a developer does not want to choose each time:

```bash
coding-scaffold select-model --target ~/dev/my-project --mode auto \
  --prompt "Fix this failing formatter test."
```

Auto mode still prints the decision so the user can challenge it.

## Provider Detection

Provider detection checks:

- local runtimes such as Ollama, LM Studio, and llama-server
- local credential files in `.coding-scaffold/.env.local`
- project-local JSON credentials
- common cloud provider environment variables
- optional GitHub Copilot CLI status during explicit `probe` and `doctor` commands

Secrets are never printed.

## Azure Guidance

For Azure OpenAI, use:

```text
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=
```

For Azure AI or Cognitive Services style endpoints, use:

```text
AZURE_AI_API_KEY=
AZURE_AI_ENDPOINT=
AZURE_AI_MODEL=
AZURE_AI_MODEL_FAMILY=openai
```

If the endpoint serves Anthropic-family models, set:

```text
AZURE_AI_MODEL_FAMILY=anthropic
```
