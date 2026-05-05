from coding_scaffold.hardware import HardwareProfile
from coding_scaffold.intake import IntakeAnswers
from coding_scaffold.model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from coding_scaffold.providers import Provider
from coding_scaffold.router import build_routing_plan


def test_local_only_never_selects_cloud_provider() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        HardwareProfile("linux", False, 16, 64, "GPU", 48, False, ["ollama"]),
        [Provider("openai", "cloud", True, "OPENAI_API_KEY set")],
    )

    assert plan.cloud_provider is None
    assert plan.cloud_model_family is None
    assert plan.strategy == "local-only"
    assert plan.route_threshold == ROUTELLM_MF_DEFAULT_THRESHOLD


def test_cloud_can_backfill_strong_model() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        HardwareProfile("linux", False, 8, 16, None, None, False, []),
        [Provider("anthropic", "cloud", True, "ANTHROPIC_API_KEY set")],
    )

    assert plan.cloud_provider == "anthropic"
    assert plan.cloud_model_family == "anthropic"
    assert plan.strong_model == "anthropic/claude-sonnet"


def test_strong_route_falls_back_to_routine_when_no_heavy_model_exists() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        HardwareProfile("linux", False, 8, 16, None, None, False, []),
        [],
    )

    assert plan.weak_model == "qwen2.5-coder:7b-instruct"
    assert plan.strong_model == "qwen2.5-coder:7b-instruct"


def test_azure_provider_keeps_endpoint_and_model_family_separate() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        HardwareProfile("linux", False, 8, 16, None, None, False, []),
        [
            Provider(
                "azure-ai",
                "cloud",
                True,
                "Azure AI endpoint and key set",
                endpoint="https://example.services.ai.azure.com",
                model_family="anthropic",
                deployment="team-sonnet",
            )
        ],
    )

    assert plan.cloud_provider == "azure-ai"
    assert plan.cloud_model_family == "anthropic"
    assert plan.strong_model == "azure-ai/team-sonnet"


def test_local_model_thresholds_pick_expected_strong_models() -> None:
    qwen_32b_plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        HardwareProfile("linux", False, 16, 32, "GPU", 24, False, []),
        [],
    )
    qwen_40b_plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        HardwareProfile("linux", False, 16, 56, "GPU", 32, False, []),
        [],
    )

    assert qwen_32b_plan.strong_model == "qwen2.5-coder:32b-instruct"
    assert qwen_40b_plan.strong_model == "qwen/qwen3-coder-40b"


def test_missing_vram_does_not_exclude_ram_only_candidates() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        HardwareProfile("linux", False, 8, 10, None, None, False, []),
        [],
    )

    assert plan.weak_model == "qwen2.5-coder:7b-instruct"


def test_low_memory_machine_has_no_local_model_candidate() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        HardwareProfile("linux", False, 4, 8, None, None, False, []),
        [],
    )

    assert plan.weak_model is None
    assert plan.strong_model is None
