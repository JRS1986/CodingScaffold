from __future__ import annotations

import json
from pathlib import Path

from .model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from .router import RoutingPlan


def load_routing_payload(target: Path) -> dict[str, object]:
    path = target.expanduser().resolve() / ".coding-scaffold" / "routing.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_routing_plan(target: Path) -> RoutingPlan | None:
    payload = load_routing_payload(target)
    if not payload:
        return None
    return RoutingPlan(
        strategy=str(payload.get("strategy") or "local-first-router"),
        weak_model=_optional_str(payload.get("weak_model")),
        strong_model=_optional_str(payload.get("strong_model")),
        route_threshold=float(payload.get("route_threshold", ROUTELLM_MF_DEFAULT_THRESHOLD)),
        local_endpoint=_optional_str(payload.get("local_endpoint")),
        cloud_provider=_optional_str(payload.get("cloud_provider")),
        cloud_model_family=_optional_str(payload.get("cloud_model_family")),
        route_rules=_list_of_strings(payload.get("route_rules")),
        model_policy=_dict_payload(payload.get("model_policy")),
    )


def _optional_str(value: object) -> str | None:
    return str(value) if value else None


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _dict_payload(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}
