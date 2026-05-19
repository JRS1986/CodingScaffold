from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from coding_scaffold.hardware import HardwareProfile
from coding_scaffold.intake import IntakeAnswers
from coding_scaffold.model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from coding_scaffold.providers import Provider
from coding_scaffold.router import RoutingPlan


@dataclass(frozen=True)
class ScaffoldInputs:
    intake: IntakeAnswers
    hardware: HardwareProfile
    providers: list[Provider]
    routing: RoutingPlan


@pytest.fixture
def hardware_profile() -> Callable[..., HardwareProfile]:
    def factory(
        os_name: str = "linux",
        is_wsl: bool = False,
        cpu_count: int = 8,
        ram_gb: float = 32,
        gpu_name: str | None = None,
        vram_gb: float | None = None,
        llmfit_available: bool = True,
        local_runtimes: list[str] | None = None,
    ) -> HardwareProfile:
        return HardwareProfile(
            os_name,
            is_wsl,
            cpu_count,
            ram_gb,
            gpu_name,
            vram_gb,
            llmfit_available,
            ["ollama"] if local_runtimes is None else local_runtimes,
        )

    return factory


@pytest.fixture
def provider_factory() -> Callable[..., Provider]:
    def factory(
        name: str = "ollama",
        kind: str = "local",
        available: bool = True,
        status: str = "CLI found",
        endpoint: str | None = "http://127.0.0.1:11434/v1",
        model_family: str | None = "local",
        deployment: str | None = None,
        redact_fields: tuple[str, ...] = (),
    ) -> Provider:
        return Provider(
            name,
            kind,
            available,
            status,
            endpoint,
            model_family,
            deployment,
            redact_fields,
        )

    return factory


@pytest.fixture
def local_provider(provider_factory: Callable[..., Provider]) -> Provider:
    return provider_factory()


@pytest.fixture
def intake_answers() -> Callable[..., IntakeAnswers]:
    def factory(
        language: str = "python",
        project_target: str = "CLI",
        existing_codebase: bool = True,
        privacy: str = "local-first",
        tool: str = "manual",
        preferred_local_model: str | None = None,
        mode: str | None = None,
    ) -> IntakeAnswers:
        return IntakeAnswers(
            language=language,
            project_target=project_target,
            existing_codebase=existing_codebase,
            privacy=privacy,
            tool=tool,
            preferred_local_model=preferred_local_model,
            mode=mode,
        )

    return factory


@pytest.fixture
def routing_plan_factory() -> Callable[..., RoutingPlan]:
    def factory(
        strategy: str = "local-first-router",
        weak_model: str | None = "qwen2.5-coder:14b-instruct",
        strong_model: str | None = "qwen2.5-coder:32b-instruct",
        route_threshold: float = ROUTELLM_MF_DEFAULT_THRESHOLD,
        local_endpoint: str | None = "http://127.0.0.1:11434/v1",
        cloud_provider: str | None = None,
        cloud_model_family: str | None = None,
        route_rules: list[str] | None = None,
        model_policy: dict[str, object] | None = None,
    ) -> RoutingPlan:
        return RoutingPlan(
            strategy,
            weak_model,
            strong_model,
            route_threshold,
            local_endpoint,
            cloud_provider,
            cloud_model_family,
            ["route locally"] if route_rules is None else route_rules,
            {"selection_mode": "recommend"} if model_policy is None else model_policy,
        )

    return factory


@pytest.fixture
def scaffold_inputs(
    intake_answers: Callable[..., IntakeAnswers],
    hardware_profile: Callable[..., HardwareProfile],
    local_provider: Provider,
    routing_plan_factory: Callable[..., RoutingPlan],
) -> Callable[..., ScaffoldInputs]:
    def factory(language: str = "python", tool: str | None = "manual") -> ScaffoldInputs:
        return ScaffoldInputs(
            intake=intake_answers(language=language, tool=tool),
            hardware=hardware_profile(),
            providers=[local_provider],
            routing=routing_plan_factory(route_threshold=0.1),
        )

    return factory
