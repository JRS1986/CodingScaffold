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


LOCAL_CODER_MODELS = [
    ModelCandidate("qwen2.5-coder:7b-instruct", "weak", 10, 6, "Fast baseline for small edits."),
    ModelCandidate("qwen2.5-coder:14b-instruct", "weak", 18, 10, "Good local default."),
    ModelCandidate("deepseek-coder-v2:16b-lite-instruct", "weak", 22, 12, "Useful MoE-style local option."),
    ModelCandidate("codestral:22b", "strong", 32, 16, "Strong code completion/editing option."),
    ModelCandidate("qwen2.5-coder:32b-instruct", "strong", 32, 24, "Strong local coding model."),
    ModelCandidate("qwen/qwen3-coder-40b", "strong", 56, 32, "User-preferred 40B-class Qwen coder slot."),
]

CLOUD_STRONG_MODELS = {
    "anthropic": "anthropic/claude-sonnet",
    "openai": "openai/gpt-4.1",
    "azure-openai": "azure-openai/{deployment}",
    "azure-ai": "azure-ai/{deployment}",
    "openrouter": "openrouter/auto",
    "github-models": "github/models",
    "gemini": "google/gemini-pro",
    "groq": "groq/compound",
}

CLOUD_ROUTINE_MODELS = {
    "anthropic": "anthropic/claude-haiku",
    "openai": "openai/gpt-4.1-mini",
    "azure-openai": "azure-openai/{deployment}",
    "azure-ai": "azure-ai/{deployment}",
    "openrouter": "openrouter/auto",
    "github-models": "github/models",
    "gemini": "google/gemini-flash",
    "groq": "groq/compound",
}
