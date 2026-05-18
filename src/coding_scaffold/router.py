from __future__ import annotations

from dataclasses import asdict, dataclass

from .hardware import HardwareProfile
from .intake import IntakeAnswers
from .model_catalog import (
    CLOUD_ROUTINE_MODELS,
    CLOUD_STRONG_MODELS,
    LOCAL_CODER_MODELS,
    ROUTELLM_MF_DEFAULT_THRESHOLD,
)
from .providers import Provider


@dataclass(frozen=True)
class RoutingPlan:
    strategy: str
    weak_model: str | None
    strong_model: str | None
    route_threshold: float
    local_endpoint: str | None
    cloud_provider: str | None
    cloud_model_family: str | None
    route_rules: list[str]
    model_policy: dict[str, object]

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

    cloud = _first_cloud_provider(providers)
    cloud_provider = cloud.name if cloud else None
    cloud_family = _cloud_family(cloud)
    cloud_strong = _cloud_model(cloud, "strong")
    cloud_routine = _cloud_model(cloud, "routine")

    privacy = intake.privacy or "local-first"
    strong = strong_local if privacy == "local-only" else strong_local or cloud_strong
    weak = weak or (None if privacy == "local-only" else cloud_routine)
    strong = strong or weak
    strategy = "local-only" if privacy == "local-only" else "local-first-router"

    return RoutingPlan(
        strategy=strategy,
        weak_model=weak or strong,
        strong_model=strong,
        route_threshold=ROUTELLM_MF_DEFAULT_THRESHOLD,
        local_endpoint=local_endpoint,
        cloud_provider=None if privacy == "local-only" else cloud_provider,
        cloud_model_family=None if privacy == "local-only" else cloud_family,
        route_rules=[
            "Use weak/local model for short edits, explanation, search, formatting, and tests.",
            "Use strong model for architecture, multi-file refactors, security, migrations, and failed attempts.",
            "Prefer local providers unless privacy mode allows cloud escalation and credentials are present.",
        ],
        model_policy={
            "selection_mode": "recommend",
            "routine_route": "local-first",
            "heavy_lift_route": "cloud-allowed" if privacy != "local-only" else "local-only",
            "provider_abstraction": "provider endpoint is separate from model family",
            "prompt_router": "coding-scaffold select-model --target . --prompt '...'",
        },
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
    # Pick the strongest fit by required resources rather than list order: a
    # higher min_ram_gb / min_vram_gb requirement is a proxy for capability,
    # so we don't silently downgrade if LOCAL_CODER_MODELS gets reordered.
    return max(fitted, key=lambda model: (model.min_ram_gb, model.min_vram_gb or 0)).name


def _first_endpoint(providers: list[Provider]) -> str | None:
    for provider in providers:
        if provider.kind == "local" and provider.available and provider.endpoint:
            return provider.endpoint
    return None


def _first_cloud_provider(providers: list[Provider]) -> Provider | None:
    priority = [
        "azure-openai",
        "azure-ai",
        "anthropic",
        "openai",
        "openrouter",
        "github-models",
        "gemini",
        "groq",
    ]
    available = {
        provider.name: provider
        for provider in providers
        if provider.kind == "cloud" and provider.available
    }
    for name in priority:
        if name in available:
            return available[name]
    return None


def _cloud_model(provider: Provider | None, role: str) -> str | None:
    if not provider:
        return None
    catalog = CLOUD_ROUTINE_MODELS if role == "routine" else CLOUD_STRONG_MODELS
    template = catalog.get(provider.name)
    if not template:
        return None
    deployment = provider.deployment or "configure-deployment"
    return template.format(deployment=deployment)


def _cloud_family(provider: Provider | None) -> str | None:
    if not provider:
        return None
    if provider.model_family:
        return provider.model_family
    family_by_provider = {
        "anthropic": "anthropic",
        "openai": "openai",
        "azure-openai": "openai",
        "gemini": "google",
    }
    return family_by_provider.get(provider.name)
