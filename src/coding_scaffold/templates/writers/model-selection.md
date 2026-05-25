# Model Selection

Model selection is the small decision before the big token spend: should this prompt use the
routine route or the heavy-lift route?

Run a recommendation:

```bash
coding-scaffold tools select-model --target . --prompt "Review this migration for rollback risks."
```

Use auto mode when you do not want to choose each time:

```bash
coding-scaffold tools select-model --target . --mode auto --prompt "Fix this failing formatter test."
```

The command does not call a model. It reads the task text, classifies the risk, and returns the
recommended route, provider, model family, model or deployment, confidence, and reasons.

## Provider Abstraction

Keep these concepts separate:

- provider: where the request goes, such as local Ollama, OpenAI, Anthropic, Azure OpenAI, or Azure AI
- model family: what kind of model answers, such as OpenAI, Anthropic, Google, or local
- deployment: provider-specific name, especially common in Azure

This matters because an Azure endpoint can serve OpenAI-family or Anthropic-family models depending
on how the organization configured it. Skills should ask for a capability like `routine` or
`heavy-lift`, not hard-code one vendor's model name.

## Prompt Profiles

- routine-coding: short edits, tests, docs, explanations, formatting, and small fixes
- complex-change: architecture, security, migrations, reviews, orchestration, incidents, or long prompts
- standard-change: normal work with no obvious heavy-lift signal

If the recommendation feels wrong, treat that as a manual override: inspect context and pick the
safer route.
