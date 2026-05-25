# RouteLLM

RouteLLM is optional. Use it when you want an OpenAI-compatible local routing server that decides
between a weak/routine model and a strong/heavy-lift model.

## When It Helps

- You have a cheap or local routine model and a stronger model.
- You want tools to call one endpoint while routing happens behind the scenes.
- You want to experiment with cost/quality thresholds.

## Install

```bash
python -m pip install "routellm[serve,eval]"
```

## Important Caveat

The commonly recommended `mf` router currently requires `OPENAI_API_KEY` for embeddings, even when
one of the routed models is local. Keep that key local in `.coding-scaffold/.env.local`.

## Start A Router Server

```bash
python -m routellm.openai_server \
  --routers mf \
  --strong-model ${strong} \
  --weak-model ${weak}
```

RouteLLM's OpenAI-compatible server defaults to port `6060`. Point OpenCode, OpenClaude, or another
OpenAI-compatible client at that endpoint, then use a model value such as
`router-mf-${threshold}`.
