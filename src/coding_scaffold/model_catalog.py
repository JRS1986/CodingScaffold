from __future__ import annotations

from dataclasses import dataclass


# RouteLLM's documented default threshold for the matrix-factorization router.
ROUTELLM_MF_DEFAULT_THRESHOLD = 0.11593


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    role: str
    min_ram_gb: float
    min_vram_gb: float | None
    notes: str


# Ollama tags, verified against registry.ollama.ai. Sizing leaves headroom for
# the KV cache on top of the download size. Review this list each release —
# local coding models turn over every few months.
LOCAL_CODER_MODELS = [
    ModelCandidate("qwen3.5:9b", "weak", 10, 8, "Fast default for small edits and explanation."),
    ModelCandidate("gpt-oss:20b", "weak", 24, 16, "Strong routine model for 16GB-class GPUs."),
    ModelCandidate("devstral-small-2:24b", "strong", 32, 20, "Agentic coding model; tight on 16GB cards."),
    ModelCandidate("qwen3-coder:30b", "strong", 32, 24, "Strong local coding default (MoE, 3B active)."),
    ModelCandidate("qwen3.6:35b-a3b-coding", "strong", 48, 32, "Coding-tuned MoE for 32GB+ GPUs."),
    ModelCandidate("qwen3-coder-next", "strong", 80, 64, "Workstation-class coder; ~52GB download."),
]

# Pinned provider model ids (models.dev naming, as used by OpenCode). Hosted
# model lineups change quickly; treat these as reviewed defaults, not truth.
CLOUD_STRONG_MODELS = {
    "anthropic": "anthropic/claude-sonnet-5",
    "openai": "openai/gpt-5.6",
    "azure-openai": "azure-openai/{deployment}",
    "azure-ai": "azure-ai/{deployment}",
    "openrouter": "openrouter/auto",
    "github-models": "github/models",
    "gemini": "google/gemini-3.1-pro-preview",
    "groq": "groq/compound",
}

CLOUD_ROUTINE_MODELS = {
    "anthropic": "anthropic/claude-haiku-4-5",
    "openai": "openai/gpt-5.4-mini",
    "azure-openai": "azure-openai/{deployment}",
    "azure-ai": "azure-ai/{deployment}",
    "openrouter": "openrouter/auto",
    "github-models": "github/models",
    "gemini": "google/gemini-flash-latest",
    "groq": "groq/compound",
}
