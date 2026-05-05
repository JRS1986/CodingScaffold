from coding_scaffold.model_selection import select_model_for_prompt
from coding_scaffold.providers import Provider
from coding_scaffold.router import RoutingPlan


def test_select_model_routes_security_review_to_heavy_lift_provider() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "azure-ai/team-sonnet",
        0.11593,
        "http://127.0.0.1:11434/v1",
        "azure-ai",
        "anthropic",
        ["route locally first"],
        {"selection_mode": "recommend"},
    )
    providers = [
        Provider("ollama", "local", True, "CLI found", "http://127.0.0.1:11434/v1"),
        Provider(
            "azure-ai",
            "cloud",
            True,
            "Azure AI endpoint and key set",
            "https://example.services.ai.azure.com",
            "anthropic",
            "team-sonnet",
        ),
    ]

    selection = select_model_for_prompt(
        "Review this authentication refactor for security regressions.",
        routing,
        providers,
    )

    assert selection.route == "heavy-lift"
    assert selection.provider == "azure-ai"
    assert selection.model_family == "anthropic"
    assert selection.model == "azure-ai/team-sonnet"


def test_select_model_routes_short_fix_to_local_routine_model() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "azure-openai/team-gpt",
        0.11593,
        "http://127.0.0.1:11434/v1",
        "azure-openai",
        "openai",
        ["route locally first"],
        {"selection_mode": "recommend"},
    )
    providers = [
        Provider("ollama", "local", True, "CLI found", "http://127.0.0.1:11434/v1"),
        Provider("azure-openai", "cloud", True, "Azure OpenAI env set", None, "openai", "team-gpt"),
    ]

    selection = select_model_for_prompt("Fix this failing formatter test.", routing, providers, "auto")

    assert selection.route == "routine"
    assert selection.provider == "ollama"
    assert selection.model_family == "local"
    assert selection.model == "qwen-small"
    assert selection.mode == "auto"
