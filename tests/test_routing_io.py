import json

from coding_scaffold.model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from coding_scaffold.routing_io import load_routing_payload, load_routing_plan


def test_load_routing_payload_handles_missing_or_invalid_file(tmp_path) -> None:
    assert load_routing_payload(tmp_path) == {}

    scaffold = tmp_path / ".coding-scaffold"
    scaffold.mkdir()
    (scaffold / "routing.json").write_text("{not-json", encoding="utf-8")

    assert load_routing_payload(tmp_path) == {}


def test_load_routing_plan_round_trips_known_fields(tmp_path) -> None:
    scaffold = tmp_path / ".coding-scaffold"
    scaffold.mkdir()
    (scaffold / "routing.json").write_text(
        json.dumps(
            {
                "strategy": "local-first-router",
                "weak_model": "qwen-small",
                "strong_model": "qwen-large",
                "local_endpoint": "http://127.0.0.1:11434/v1",
                "cloud_provider": "azure-ai",
                "cloud_model_family": "anthropic",
                "route_rules": ["route locally first"],
                "model_policy": {"selection_mode": "recommend"},
            }
        ),
        encoding="utf-8",
    )

    plan = load_routing_plan(tmp_path)

    assert plan is not None
    assert plan.strong_model == "qwen-large"
    assert plan.cloud_model_family == "anthropic"
    assert plan.route_threshold == ROUTELLM_MF_DEFAULT_THRESHOLD


def test_load_routing_plan_uses_default_for_malformed_threshold(tmp_path) -> None:
    scaffold = tmp_path / ".coding-scaffold"
    scaffold.mkdir()
    (scaffold / "routing.json").write_text(
        json.dumps(
            {
                "strategy": "local-first-router",
                "route_threshold": "high",
            }
        ),
        encoding="utf-8",
    )

    plan = load_routing_plan(tmp_path)

    assert plan is not None
    assert plan.route_threshold == ROUTELLM_MF_DEFAULT_THRESHOLD
