from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .providers import Provider
from .router import RoutingPlan


@dataclass(frozen=True)
class ModelSelection:
    mode: str
    prompt_profile: str
    route: str
    provider: str
    provider_kind: str
    model_family: str | None
    model: str | None
    confidence: float
    reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def select_model_for_prompt(
    prompt: str,
    routing: RoutingPlan,
    providers: list[Provider],
    mode: str = "recommend",
) -> ModelSelection:
    normalized = " ".join(prompt.lower().split())
    profile, route, reasons, confidence = _classify_prompt(normalized)
    model = routing.weak_model if route == "routine" else routing.strong_model or routing.weak_model
    provider = _provider_for_route(route, routing, providers)
    provider_name = provider.name if provider else "local"
    provider_kind = provider.kind if provider else "local"
    model_family = _model_family(provider, routing, route)
    if mode == "auto":
        reasons = [*reasons, "auto mode selected this route without asking for a per-prompt choice"]
    return ModelSelection(
        mode=mode,
        prompt_profile=profile,
        route=route,
        provider=provider_name,
        provider_kind=provider_kind,
        model_family=model_family,
        model=model,
        confidence=confidence,
        reasons=reasons,
    )


def _classify_prompt(prompt: str) -> tuple[str, str, list[str], float]:
    if not prompt:
        return "empty", "routine", ["no prompt was provided"], 0.1

    heavy_markers = {
        "architecture",
        "architectural",
        "auth",
        "authentication",
        "authorization",
        "cross-module",
        "incident",
        "migration",
        "migrate",
        "multi-file",
        "orchestration",
        "permission",
        "production",
        "refactor",
        "redesign",
        "security",
        "threat",
        "vulnerability",
    }
    heavy_phrases = {
        "agent orchestration",
        "agent runtime",
        "code review",
        "design doc",
        "design review",
        "security review",
        "system design",
    }
    routine_markers = {
        "comment",
        "doc",
        "docs",
        "document",
        "explain",
        "format",
        "formatting",
        "lint",
        "rename",
        "small",
        "summarize",
        "test",
        "tests",
        "typo",
    }
    token_list = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", prompt)
    tokens = set(token_list)
    heavy_hits = sorted(heavy_markers & tokens)
    phrase_hits = sorted(phrase for phrase in heavy_phrases if phrase in prompt)
    routine_hits = sorted(routine_markers & tokens)
    word_count = len(token_list)

    if heavy_hits or phrase_hits or word_count > 180:
        reasons = ["heavy-lift markers: " + ", ".join(heavy_hits)] if heavy_hits else []
        if phrase_hits:
            reasons.append("heavy-lift phrases: " + ", ".join(phrase_hits))
        if word_count > 180:
            reasons.append(f"prompt is long enough to need deeper context ({word_count} words)")
        return "complex-change", "heavy-lift", reasons, 0.78
    if routine_hits or word_count <= 40:
        reasons = ["routine markers: " + ", ".join(routine_hits)] if routine_hits else []
        if word_count <= 40:
            reasons.append(f"prompt is short ({word_count} words)")
        return "routine-coding", "routine", reasons, 0.72
    return "standard-change", "routine", ["no heavy-lift markers found"], 0.58

def _provider_for_route(route: str, routing: RoutingPlan, providers: list[Provider]) -> Provider | None:
    if route == "routine":
        return _available_local(providers) or _provider_named(providers, routing.cloud_provider)
    return _provider_named(providers, routing.cloud_provider) or _available_local(providers)


def _available_local(providers: list[Provider]) -> Provider | None:
    for provider in providers:
        if provider.kind == "local" and provider.available:
            return provider
    return None


def _provider_named(providers: list[Provider], name: str | None) -> Provider | None:
    for provider in providers:
        if name and provider.name == name and provider.available:
            return provider
    return None


def _model_family(provider: Provider | None, routing: RoutingPlan, route: str) -> str | None:
    if provider and provider.model_family:
        return provider.model_family
    if route == "heavy-lift":
        return routing.cloud_model_family
    return "local"
