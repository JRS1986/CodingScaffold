from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .file_ops import write_json, write_text


@dataclass(frozen=True)
class PolicyResult:
    files: list[Path]
    warnings: list[str]


def write_policy_pack(
    target: Path,
    scope: str = "company",
    adapter: str | None = "opencode",
    share: str = "disabled",
    mcp: str = "project-empty",
    enabled_providers: list[str] | None = None,
    disabled_providers: list[str] | None = None,
    disabled_mcp_servers: list[str] | None = None,
    strict_permissions: bool = True,
) -> PolicyResult:
    root = target.expanduser().resolve()
    scaffold = root / ".coding-scaffold"
    policy_dir = scaffold / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)

    enabled = _dedupe(enabled_providers or [])
    disabled = _dedupe(disabled_providers or [])
    mcp_servers = _dedupe(disabled_mcp_servers or [])
    files: list[Path] = []
    warnings: list[str] = []

    policy = _policy_payload(scope, share, mcp, enabled, disabled, mcp_servers, strict_permissions)
    files.append(write_json(policy_dir / "policy.json", policy))
    files.append(write_text(policy_dir / f"{scope}.md", _policy_md(policy)))

    if adapter == "opencode":
        opencode_payload = _opencode_policy_payload(
            share=share,
            mcp=mcp,
            enabled_providers=enabled,
            disabled_providers=disabled,
            disabled_mcp_servers=mcp_servers,
            strict_permissions=strict_permissions,
        )
        files.append(write_json(policy_dir / "opencode-policy.json", opencode_payload))
        updated, warning = _merge_opencode_config(root / "opencode.json", opencode_payload)
        files.append(updated)
        if warning:
            warnings.append(warning)

    return PolicyResult(files, warnings)


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _policy_payload(
    scope: str,
    share: str,
    mcp: str,
    enabled_providers: list[str],
    disabled_providers: list[str],
    disabled_mcp_servers: list[str],
    strict_permissions: bool,
) -> dict[str, object]:
    return {
        "scope": scope,
        "maturity": "draft",
        "review": {
            "recommended_flow": "change through pull request before treating as a default",
            "owners": [f"{scope}-ai-enablement"],
        },
        "opencode": {
            "share": share,
            "mcp": mcp,
            "enabled_providers": enabled_providers,
            "disabled_providers": disabled_providers,
            "disabled_mcp_servers": disabled_mcp_servers,
            "strict_permissions": strict_permissions,
        },
        "knowledge": {
            "promote_upward_by_pr": True,
            "scopes": ["team", "department", "unit", "company"],
            "maturity_levels": ["draft", "validated", "recommended", "standard"],
        },
    }


def _opencode_policy_payload(
    share: str,
    mcp: str,
    enabled_providers: list[str],
    disabled_providers: list[str],
    disabled_mcp_servers: list[str],
    strict_permissions: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "$schema": "https://opencode.ai/config.json",
        "share": share,
        "instructions": [".coding-scaffold/policy/*.md"],
    }
    if strict_permissions:
        payload["permission"] = {"edit": "ask", "bash": "ask"}
    if enabled_providers:
        payload["enabled_providers"] = enabled_providers
    if disabled_providers:
        payload["disabled_providers"] = disabled_providers
    if mcp == "project-empty" or disabled_mcp_servers:
        payload["mcp"] = {server: {"enabled": False} for server in disabled_mcp_servers}
    return payload


def _merge_opencode_config(path: Path, policy: dict[str, object]) -> tuple[Path, str | None]:
    from .file_ops import deep_merge_mapping

    current: dict[str, object] = {}
    warning = None
    target_path = path
    file_existed = path.exists()
    if file_existed:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            warning = f"Could not parse {path}; wrote policy overlay to {path}.new instead."
            target_path = path.with_suffix(path.suffix + ".new")
            write_json(target_path, policy)
            return target_path, warning
        if isinstance(loaded, dict):
            current = loaded

    merged = deep_merge_mapping(current, policy, deep_keys=("mcp", "permission"))
    if "instructions" in current or "instructions" in policy:
        merged["instructions"] = _merge_list(current.get("instructions"), policy.get("instructions"))

    if file_existed:
        target_path = path.with_suffix(path.suffix + ".new")
        warning = (
            f"Staged {target_path.name}; review and `mv {target_path.name} {path.name}` to apply."
        )
    write_json(target_path, merged)
    return target_path, warning


def _merge_list(left: object, right: object) -> list[object]:
    result: list[object] = []
    for value in [left, right]:
        if isinstance(value, list):
            for item in value:
                if item not in result:
                    result.append(item)
    return result


def _policy_md(policy: dict[str, object]) -> str:
    scope = policy["scope"]
    opencode = policy["opencode"]
    knowledge = policy["knowledge"]
    assert isinstance(opencode, dict)
    assert isinstance(knowledge, dict)
    return f"""# {str(scope).title()} AI Coding Policy

This policy pack records the local defaults for AI-enabled coding in this scope. Treat it as
reviewable configuration, not as a replacement for network controls, identity policy, or CI checks.

## OpenCode Defaults

- Share mode: `{opencode["share"]}`
- MCP policy: `{opencode["mcp"]}`
- Enabled providers: `{_format_list(opencode["enabled_providers"])}`
- Disabled providers: `{_format_list(opencode["disabled_providers"])}`
- Disabled MCP servers: `{_format_list(opencode["disabled_mcp_servers"])}`
- Ask before edit/bash: `{opencode["strict_permissions"]}`

`share`, `permission`, `mcp`, `enabled_providers`, and `disabled_providers` are OpenCode config
schema keys. Provider lists keep model routing explicit. MCP servers are best managed by name; if
an organization injects remote MCP defaults, disable each approved server explicitly and verify the
effective OpenCode config with `opencode debug config`.

## Knowledge Promotion

Use scopes as audience boundaries:

- `team`: project facts, local prompts, working notes, first skill drafts.
- `department`: reusable runbooks, system patterns, validated agent roles.
- `unit`: domain vocabulary, reference architecture, shared provider policy.
- `company`: standards, approved skills, approved agents, security and privacy rules.

Use maturity as trust level:

- `draft`: useful but not reviewed.
- `validated`: tried in a real project and reviewed by peers.
- `recommended`: useful across more than one team.
- `standard`: approved default for this scope.

Promote knowledge upward by pull request. Keep secrets out of all layers. When access boundaries
differ, use separate Git remotes per scope; otherwise prefer one repo with folders, frontmatter,
tags, and CODEOWNERS.
"""


def _format_list(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ", ".join(str(item) for item in value)
