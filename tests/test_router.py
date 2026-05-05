from coding_scaffold.hardware import HardwareProfile
from coding_scaffold.intake import IntakeAnswers
from coding_scaffold.providers import Provider
from coding_scaffold.router import build_routing_plan


def test_local_only_never_selects_cloud_provider() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-only"),
        HardwareProfile("linux", False, 16, 64, "GPU", 48, False, ["ollama"]),
        [Provider("openai", "cloud", True, "OPENAI_API_KEY set")],
    )

    assert plan.cloud_provider is None
    assert plan.strategy == "local-only"


def test_cloud_can_backfill_strong_model() -> None:
    plan = build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        HardwareProfile("linux", False, 8, 16, None, None, False, []),
        [Provider("anthropic", "cloud", True, "ANTHROPIC_API_KEY set")],
    )

    assert plan.cloud_provider == "anthropic"
    assert plan.strong_model == "anthropic/claude-sonnet"
