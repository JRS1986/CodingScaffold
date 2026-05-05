from coding_scaffold.model_selection import select_model_for_prompt
from coding_scaffold.model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from coding_scaffold.providers import Provider
from coding_scaffold.router import RoutingPlan


def test_select_model_routes_security_review_to_heavy_lift_provider() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "azure-ai/team-sonnet",
        ROUTELLM_MF_DEFAULT_THRESHOLD,
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
        ROUTELLM_MF_DEFAULT_THRESHOLD,
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


def test_select_model_does_not_match_markers_inside_words() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "qwen-large",
        ROUTELLM_MF_DEFAULT_THRESHOLD,
        None,
        None,
        None,
        ["route locally first"],
        {"selection_mode": "recommend"},
    )

    selection = select_model_for_prompt(
        "Run the latest formatter test on the docker image, then check author metadata.",
        routing,
        [],
    )

    assert selection.route == "routine"
    joined_reasons = " ".join(selection.reasons)
    assert "auth" not in joined_reasons
    assert "doc" not in joined_reasons


def test_select_model_empty_prompt_profile() -> None:
    routing = RoutingPlan(
        "local-first-router",
        None,
        None,
        ROUTELLM_MF_DEFAULT_THRESHOLD,
        None,
        None,
        None,
        [],
        {},
    )

    selection = select_model_for_prompt("", routing, [])

    assert selection.prompt_profile == "empty"
    assert selection.confidence == 0.1


def test_select_model_heavy_marker_wins_over_routine_marker() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "qwen-large",
        ROUTELLM_MF_DEFAULT_THRESHOLD,
        None,
        None,
        None,
        [],
        {},
    )

    selection = select_model_for_prompt("Review this small test migration.", routing, [])

    assert selection.route == "heavy-lift"
    assert selection.model == "qwen-large"


def test_select_model_long_prompt_without_markers_routes_heavy_lift() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "qwen-large",
        ROUTELLM_MF_DEFAULT_THRESHOLD,
        None,
        None,
        None,
        [],
        {},
    )
    prompt = " ".join(f"word{i}" for i in range(181))

    selection = select_model_for_prompt(prompt, routing, [])

    assert selection.route == "heavy-lift"
    assert selection.prompt_profile == "complex-change"


def test_select_model_word_count_boundary() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "qwen-large",
        ROUTELLM_MF_DEFAULT_THRESHOLD,
        None,
        None,
        None,
        [],
        {},
    )
    forty_words = " ".join(f"word{i}" for i in range(40))
    forty_one_words = " ".join(f"word{i}" for i in range(41))

    assert select_model_for_prompt(forty_words, routing, []).prompt_profile == "routine-coding"
    assert select_model_for_prompt(forty_one_words, routing, []).prompt_profile == "standard-change"


def test_select_model_common_agent_design_review_words_stay_routine() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "qwen-large",
        ROUTELLM_MF_DEFAULT_THRESHOLD,
        None,
        None,
        None,
        [],
        {},
    )

    prompts = [
        "Update the user-agent header in this SDK client.",
        "Polish the design choices in this docstring.",
        "Review my README typo.",
    ]

    for prompt in prompts:
        selection = select_model_for_prompt(prompt, routing, [])
        assert selection.route == "routine"


def test_select_model_heavy_phrases_still_escalate() -> None:
    routing = RoutingPlan(
        "local-first-router",
        "qwen-small",
        "qwen-large",
        ROUTELLM_MF_DEFAULT_THRESHOLD,
        None,
        None,
        None,
        [],
        {},
    )

    selection = select_model_for_prompt("Write a system design for the agent runtime.", routing, [])

    assert selection.route == "heavy-lift"
    assert "system design" in " ".join(selection.reasons)
