from __future__ import annotations

from dataclasses import asdict, dataclass

from .hardware import HardwareProfile
from .intake import IntakeAnswers
from .model_catalog import CLOUD_STRONG_MODELS, LOCAL_CODER_MODELS
from .providers import Provider


@dataclass(frozen=True)
class RoutingPlan:
    strategy: str
    weak_model: str | None
    strong_model: str | None
    route_threshold: float
    local_endpoint: str | None
    cloud_provider: str | None
    route_rules: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_routing_plan(
    intake: IntakeAnswers,
    hardware: HardwareProfile,
    providers: list[Provider],
) -> RoutingPlan:
    local_endpoint = _first_endpoint(providers)
    weak = _select_local_model(hardware, "weak")
    strong_local = _select_local_model(hardware, "strong")
    preferred = intake.preferred_local_model
    if preferred and preferred != "auto":
        strong_local = preferred

    cloud_provider = _first_cloud_provider(providers)
    cloud_strong = CLOUD_STRONG_MODELS.get(cloud_provider or "")

    privacy = intake.privacy or "local-first"
    strong = strong_local if privacy == "local-only" else strong_local or cloud_strong
    strategy = "local-only" if privacy == "local-only" else "local-first-router"

    return RoutingPlan(
        strategy=strategy,
        weak_model=weak or strong,
        strong_model=strong,
        route_threshold=0.11593,
        local_endpoint=local_endpoint,
        cloud_provider=None if privacy == "local-only" else cloud_provider,
        route_rules=[
            "Use weak/local model for short edits, explanation, search, formatting, and tests.",
            "Use strong model for architecture, multi-file refactors, security, migrations, and failed attempts.",
            "Prefer local providers unless privacy mode allows cloud escalation and credentials are present.",
        ],
    )


def _select_local_model(hardware: HardwareProfile, role: str) -> str | None:
    ram = hardware.ram_gb
    vram = hardware.vram_gb
    candidates = [model for model in LOCAL_CODER_MODELS if model.role == role]
    fitted = [
        model
        for model in candidates
        if ram >= model.min_ram_gb and (model.min_vram_gb is None or vram is None or vram >= model.min_vram_gb)
    ]
    if not fitted:
        return None
    return fitted[-1].name


def _first_endpoint(providers: list[Provider]) -> str | None:
    for provider in providers:
        if provider.kind == "local" and provider.available and provider.endpoint:
            return provider.endpoint
    return None


def _first_cloud_provider(providers: list[Provider]) -> str | None:
    priority = ["anthropic", "openai", "openrouter", "github-models", "gemini", "groq"]
    available = {provider.name for provider in providers if provider.kind == "cloud" and provider.available}
    for name in priority:
        if name in available:
            return name
    return None
