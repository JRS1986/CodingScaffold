from coding_scaffold.model_selection import select_model_for_prompt


def test_select_model_routes_security_review_to_heavy_lift_provider(
    routing_plan_factory, provider_factory
) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="azure-ai/team-sonnet",
        cloud_provider="azure-ai",
        cloud_model_family="anthropic",
        route_rules=["route locally first"],
    )
    providers = [
        provider_factory(),
        provider_factory(
            name="azure-ai",
            kind="cloud",
            status="Azure AI endpoint and key set",
            endpoint="https://example.services.ai.azure.com",
            model_family="anthropic",
            deployment="team-sonnet",
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


def test_select_model_routes_short_fix_to_local_routine_model(
    routing_plan_factory, provider_factory
) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="azure-openai/team-gpt",
        cloud_provider="azure-openai",
        cloud_model_family="openai",
        route_rules=["route locally first"],
    )
    providers = [
        provider_factory(),
        provider_factory(
            name="azure-openai",
            kind="cloud",
            status="Azure OpenAI env set",
            endpoint=None,
            model_family="openai",
            deployment="team-gpt",
        ),
    ]

    selection = select_model_for_prompt(
        "Fix this failing formatter test.", routing, providers, "auto"
    )

    assert selection.route == "routine"
    assert selection.provider == "ollama"
    assert selection.model_family == "local"
    assert selection.model == "qwen-small"
    assert selection.mode == "auto"


def test_select_model_does_not_match_markers_inside_words(routing_plan_factory) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="qwen-large",
        local_endpoint=None,
        route_rules=["route locally first"],
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


def test_select_model_empty_prompt_profile(routing_plan_factory) -> None:
    routing = routing_plan_factory(
        weak_model=None,
        strong_model=None,
        local_endpoint=None,
        route_rules=[],
        model_policy={},
    )

    selection = select_model_for_prompt("", routing, [])

    assert selection.prompt_profile == "empty"
    assert selection.confidence == 0.1


def test_select_model_heavy_marker_wins_over_routine_marker(routing_plan_factory) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="qwen-large",
        local_endpoint=None,
        route_rules=[],
        model_policy={},
    )

    selection = select_model_for_prompt("Review this small test migration.", routing, [])

    assert selection.route == "heavy-lift"
    assert selection.model == "qwen-large"


def test_select_model_long_prompt_without_markers_routes_heavy_lift(routing_plan_factory) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="qwen-large",
        local_endpoint=None,
        route_rules=[],
        model_policy={},
    )
    prompt = " ".join(f"word{i}" for i in range(181))

    selection = select_model_for_prompt(prompt, routing, [])

    assert selection.route == "heavy-lift"
    assert selection.prompt_profile == "complex-change"


def test_select_model_word_count_boundary(routing_plan_factory) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="qwen-large",
        local_endpoint=None,
        route_rules=[],
        model_policy={},
    )
    forty_words = " ".join(f"word{i}" for i in range(40))
    forty_one_words = " ".join(f"word{i}" for i in range(41))

    assert select_model_for_prompt(forty_words, routing, []).prompt_profile == "routine-coding"
    assert select_model_for_prompt(forty_one_words, routing, []).prompt_profile == "standard-change"


def test_select_model_common_agent_design_review_words_stay_routine(routing_plan_factory) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="qwen-large",
        local_endpoint=None,
        route_rules=[],
        model_policy={},
    )

    prompts = [
        "Update the user-agent header in this SDK client.",
        "Polish the design choices in this docstring.",
        "Review my README typo.",
    ]

    for prompt in prompts:
        selection = select_model_for_prompt(prompt, routing, [])
        assert selection.route == "routine"


def test_select_model_heavy_phrases_still_escalate(routing_plan_factory) -> None:
    routing = routing_plan_factory(
        weak_model="qwen-small",
        strong_model="qwen-large",
        local_endpoint=None,
        route_rules=[],
        model_policy={},
    )

    selection = select_model_for_prompt("Write a system design for the agent runtime.", routing, [])

    assert selection.route == "heavy-lift"
    assert "system design" in " ".join(selection.reasons)
