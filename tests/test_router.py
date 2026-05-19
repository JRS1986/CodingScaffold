import random

from coding_scaffold.intake import IntakeAnswers
from coding_scaffold.model_catalog import LOCAL_CODER_MODELS, ROUTELLM_MF_DEFAULT_THRESHOLD
from coding_scaffold.router import _select_local_model, build_routing_plan


def test_local_only_never_selects_cloud_provider(hardware_profile, provider_factory) -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        hardware_profile(
            cpu_count=16, ram_gb=64, gpu_name="GPU", vram_gb=48, llmfit_available=False
        ),
        [
            provider_factory(
                name="openai",
                kind="cloud",
                status="OPENAI_API_KEY set",
                endpoint=None,
                model_family="openai",
            )
        ],
    )

    assert plan.cloud_provider is None
    assert plan.cloud_model_family is None
    assert plan.strategy == "local-only"
    assert plan.route_threshold == ROUTELLM_MF_DEFAULT_THRESHOLD


def test_cloud_can_backfill_strong_model(hardware_profile, provider_factory) -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        hardware_profile(ram_gb=16, llmfit_available=False, local_runtimes=[]),
        [
            provider_factory(
                name="anthropic",
                kind="cloud",
                status="ANTHROPIC_API_KEY set",
                endpoint=None,
                model_family="anthropic",
            )
        ],
    )

    assert plan.cloud_provider == "anthropic"
    assert plan.cloud_model_family == "anthropic"
    assert plan.strong_model == "anthropic/claude-sonnet"


def test_strong_route_falls_back_to_routine_when_no_heavy_model_exists(hardware_profile) -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        hardware_profile(ram_gb=16, llmfit_available=False, local_runtimes=[]),
        [],
    )

    assert plan.weak_model == "qwen2.5-coder:7b-instruct"
    assert plan.strong_model == "qwen2.5-coder:7b-instruct"


def test_azure_provider_keeps_endpoint_and_model_family_separate(
    hardware_profile, provider_factory
) -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        hardware_profile(ram_gb=16, llmfit_available=False, local_runtimes=[]),
        [
            provider_factory(
                name="azure-ai",
                kind="cloud",
                status="Azure AI endpoint and key set",
                endpoint="https://example.services.ai.azure.com",
                model_family="anthropic",
                deployment="team-sonnet",
            )
        ],
    )

    assert plan.cloud_provider == "azure-ai"
    assert plan.cloud_model_family == "anthropic"
    assert plan.strong_model == "azure-ai/team-sonnet"


def test_local_model_thresholds_pick_expected_strong_models(hardware_profile) -> None:
    qwen_32b_plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        hardware_profile(
            cpu_count=16, gpu_name="GPU", vram_gb=24, llmfit_available=False, local_runtimes=[]
        ),
        [],
    )
    qwen_40b_plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        hardware_profile(
            cpu_count=16,
            ram_gb=56,
            gpu_name="GPU",
            vram_gb=32,
            llmfit_available=False,
            local_runtimes=[],
        ),
        [],
    )

    assert qwen_32b_plan.strong_model == "qwen2.5-coder:32b-instruct"
    assert qwen_40b_plan.strong_model == "qwen/qwen3-coder-40b"


def test_missing_vram_does_not_exclude_ram_only_candidates(hardware_profile) -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        hardware_profile(ram_gb=10, llmfit_available=False, local_runtimes=[]),
        [],
    )

    assert plan.weak_model == "qwen2.5-coder:7b-instruct"


def test_select_local_model_is_independent_of_catalog_order(monkeypatch, hardware_profile) -> None:
    hardware = hardware_profile(
        cpu_count=16,
        ram_gb=64,
        gpu_name="GPU",
        vram_gb=48,
        llmfit_available=False,
        local_runtimes=[],
    )

    baseline = _select_local_model(hardware, "strong")

    shuffled = list(LOCAL_CODER_MODELS)
    rng = random.Random(1234)
    rng.shuffle(shuffled)
    monkeypatch.setattr("coding_scaffold.router.LOCAL_CODER_MODELS", shuffled)

    assert _select_local_model(hardware, "strong") == baseline

    monkeypatch.setattr(
        "coding_scaffold.router.LOCAL_CODER_MODELS",
        list(reversed(LOCAL_CODER_MODELS)),
    )

    assert _select_local_model(hardware, "strong") == baseline


def test_low_memory_machine_has_no_local_model_candidate(hardware_profile) -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        hardware_profile(cpu_count=4, ram_gb=8, llmfit_available=False, local_runtimes=[]),
        [],
    )

    assert plan.weak_model is None
    assert plan.strong_model is None
