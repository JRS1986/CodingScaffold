"""Offline checks for reviewed native configuration contracts, not live tool probes."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .file_ops import sha256_text
from .model_catalog import CLOUD_ROUTINE_MODELS, CLOUD_STRONG_MODELS, LOCAL_CODER_MODELS
from .skills import lint_skills


COMPATIBILITY_RELATIVE = Path(".coding-scaffold/compatibility.json")
REVIEWED_AT = "2026-09-19"
REVIEW_INTERVAL_DAYS = 90
# Unversioned upstream docs are identified by their snapshot date, not an invented CLI version.
ADAPTER_SOURCES = {
    "codex": (
        "https://learn.chatgpt.com/docs/config-file/config-reference",
        "https://learn.chatgpt.com/docs/hooks",
    ),
    "claude-code": (
        "https://code.claude.com/docs/en/settings",
        "https://code.claude.com/docs/en/mcp",
        "https://code.claude.com/docs/en/hooks",
    ),
    "opencode": ("https://opencode.ai/config.json", "https://opencode.ai/docs/skills/"),
    "hermes": ("https://github.com/NousResearch/hermes-agent",),
    "pi": ("https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent",),
    "openclaude": ("https://github.com/gitlawb/openclaude",),
}


def compatibility_manifest() -> dict[str, object]:
    """Freeze provenance with generated files; refresh uses the normal .new workflow."""
    models = [
        {
            "id": model.name,
            "upstream_version": model.name,
            "source_url": f"https://ollama.com/library/{model.name}",
            "reviewed_at": REVIEWED_AT,
        }
        for model in LOCAL_CODER_MODELS
    ]
    models.extend(
        {
            "id": model,
            "upstream_version": model,
            "source_url": "https://models.dev/",
            "reviewed_at": REVIEWED_AT,
        }
        for model in sorted(set(CLOUD_ROUTINE_MODELS.values()) | set(CLOUD_STRONG_MODELS.values()))
    )
    return {
        "schema_version": 1,
        "review_interval_days": REVIEW_INTERVAL_DAYS,
        "adapters": {
            tool: {
                "upstream_version": f"documentation snapshot {REVIEWED_AT}"
                if tool
                in {
                    "codex",
                    "claude-code",
                    "opencode",
                }
                else None,
                "reviewed_at": REVIEWED_AT
                if tool in {"codex", "claude-code", "opencode"}
                else None,
                "source_urls": list(sources),
                "scope": "native-config"
                if tool in {"codex", "claude-code", "opencode"}
                else "guidance-only; not contract-tested",
            }
            for tool, sources in ADAPTER_SOURCES.items()
        },
        "model_catalog": {
            "reviewed_at": REVIEWED_AT,
            "upstream_version": "bundled catalog snapshot",
            "source_urls": ["https://models.dev/", "https://ollama.com/library"],
            "digest": sha256_text(json.dumps(models, sort_keys=True)),
            "models": models,
            "scope": "Recommendation provenance; no live availability or account access check.",
        },
    }


@dataclass(frozen=True)
class CompatibilityFinding:
    severity: str
    path: str
    rule: str
    message: str


@dataclass(frozen=True)
class CompatibilityReport:
    findings: list[CompatibilityFinding] = field(default_factory=list)
    scanned_files: list[str] = field(default_factory=list)
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(f.severity == "error" for f in self.findings)

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "errors": self.error_count,
            "warnings": sum(f.severity == "warning" for f in self.findings),
        }


def check_compatibility(target: Path, *, today: date | None = None) -> CompatibilityReport:
    root = target.expanduser().resolve()
    findings: list[CompatibilityFinding] = []
    scanned: list[str] = []
    today = today or date.today()

    def issue(path: str, rule: str, message: str, severity: str = "error") -> None:
        findings.append(CompatibilityFinding(severity, path, rule, message))

    def read(relative: str) -> dict | None:
        path = root / relative
        if not path.exists():
            return None
        scanned.append(relative)
        try:
            raw = path.read_text(encoding="utf-8-sig")
            payload = tomllib.loads(raw) if path.suffix == ".toml" else json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except (OSError, UnicodeError, ValueError):
            issue(relative, "invalid-config", "Configuration must be a readable JSON/TOML object.")
            return None

    for relative in (
        ".codex/config.toml",
        ".claude/settings.json",
        ".claude/settings.local.json",
        "opencode.json",
        ".mcp.json",
        ".codex/hooks.json",
    ):
        payload = read(relative)
        if payload is None:
            continue
        if relative == ".codex/config.toml":
            if "approval_mode" in payload:
                issue(
                    relative,
                    "retired-key",
                    "Replace approval_mode with approval_policy; review sandbox_mode separately.",
                )
            for key, choices in {
                "approval_policy": ("untrusted", "on-failure", "on-request", "never"),
                "sandbox_mode": ("read-only", "workspace-write", "danger-full-access"),
            }.items():
                value = payload.get(key)
                # Newer Codex also accepts a granular approval-policy table.
                if (
                    value is not None
                    and not (key == "approval_policy" and isinstance(value, dict))
                    and value not in choices
                ):
                    issue(
                        relative,
                        "invalid-value",
                        f"Review unsupported {key} against the upstream config reference.",
                    )
        if relative == "opencode.json":
            if "share" in payload and payload["share"] not in ("manual", "auto", "disabled"):
                issue(relative, "invalid-value", "share must be manual, auto or disabled.")
            if "default_agent" in payload and not isinstance(payload["default_agent"], str):
                issue(relative, "invalid-value", "default_agent must name an agent.")
        if relative.startswith(".claude/"):
            permissions = payload.get("permissions", {})
            if not isinstance(permissions, dict):
                issue(relative, "invalid-permissions", "permissions must be an object.")
            else:
                mode = permissions.get("defaultMode")
                if mode is not None and mode not in (
                    "default",
                    "acceptEdits",
                    "plan",
                    "dontAsk",
                    "bypassPermissions",
                    "auto",
                ):
                    issue(
                        relative,
                        "invalid-permissions",
                        "permissions.defaultMode is not a reviewed native mode.",
                    )
                for key in ("allow", "ask", "deny"):
                    rules = permissions.get(key, [])
                    if not isinstance(rules, list) or any(
                        not isinstance(rule, str) or not re_permission(rule) for rule in rules
                    ):
                        issue(
                            relative,
                            "invalid-permissions",
                            f"permissions.{key} needs tool rules such as Read(**/.env), not bare paths.",
                        )
            if "includeCoAuthoredBy" in payload:
                issue(
                    relative,
                    "retired-key",
                    "Use attribution.commit and attribution.pr instead of includeCoAuthoredBy.",
                    "warning",
                )
        for key in (
            ("mcpServers",)
            if relative == ".mcp.json"
            else ("mcp",)
            if relative == "opencode.json"
            else ("mcp_servers",)
            if relative.endswith(".toml")
            else ()
        ):
            servers = payload.get(key, {})
            if not isinstance(servers, dict) or any(
                not isinstance(item, dict) for item in servers.values()
            ):
                issue(relative, "invalid-mcp", f"{key} must map server names to objects.")
        if "hooks" in payload:
            findings.extend(validate_hooks(payload["hooks"], relative))

    for finding in lint_skills(root).findings:
        if finding.rule in {"invalid-frontmatter", "missing-skill-md", "unreadable"}:
            issue(finding.skill or "skills", finding.rule, finding.message)

    saved = read(str(COMPATIBILITY_RELATIVE))
    if (
        saved is None
        and not (root / COMPATIBILITY_RELATIVE).exists()
        and (scanned or (root / ".coding-scaffold/routing.json").exists())
    ):
        issue(
            str(COMPATIBILITY_RELATIVE),
            "missing-provenance",
            "No saved compatibility review; using bundled contracts. Run setup update for generated projects.",
            "warning",
        )
    provenance = saved if saved is not None else compatibility_manifest()
    if (
        provenance.get("schema_version") != 1
        or not isinstance(provenance.get("adapters"), dict)
        or not isinstance(provenance.get("model_catalog"), dict)
    ):
        issue(
            str(COMPATIBILITY_RELATIVE),
            "invalid-provenance",
            "Expected compatibility manifest schema_version 1, adapters and model_catalog objects.",
        )
    else:
        relevant = []
        for tool, marker in (
            ("codex", ".codex"),
            ("claude-code", ".claude"),
            ("opencode", "opencode.json"),
            ("hermes", ".coding-scaffold/HERMES.md"),
            ("pi", ".coding-scaffold/PI.md"),
            ("openclaude", ".coding-scaffold/OPENCLAUDE.md"),
        ):
            if (root / marker).exists():
                relevant.append((tool, provenance["adapters"].get(tool)))
        if (root / ".coding-scaffold/routing.json").exists():
            relevant.append(("model_catalog", provenance["model_catalog"]))
            if (
                provenance["model_catalog"].get("digest")
                != compatibility_manifest()["model_catalog"]["digest"]
            ):
                issue(
                    str(COMPATIBILITY_RELATIVE),
                    "catalog-changed",
                    "Bundled model catalog changed; review routing recommendations and refresh generated files.",
                    "warning",
                )
        for name, record in relevant:
            try:
                reviewed = date.fromisoformat(record["reviewed_at"])
                age = (today - reviewed).days
            except (TypeError, KeyError, ValueError):
                issue(
                    str(COMPATIBILITY_RELATIVE),
                    "unreviewed",
                    f"{name}: no recorded compatibility review.",
                    "warning",
                )
                continue
            if age > REVIEW_INTERVAL_DAYS or age < 0:
                issue(
                    str(COMPATIBILITY_RELATIVE),
                    "review-overdue",
                    f"{name}: review date {reviewed}; recheck upstream documentation and run setup update.",
                    "warning",
                )
    return CompatibilityReport(findings, scanned, provenance)


def re_permission(rule: str) -> bool:
    import re

    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_*.-]*(?:\([^\n]*\))?", rule))


def validate_hooks(hooks: object, path: str) -> list[CompatibilityFinding]:
    """Validate shared structural fields without rejecting future native hook types/events."""

    def invalid() -> list[CompatibilityFinding]:
        return [
            CompatibilityFinding(
                "error",
                path,
                "invalid-hooks",
                "hooks must map events to matcher groups containing typed hook handlers; command hooks need a non-empty command.",
            )
        ]

    if not isinstance(hooks, dict):
        return invalid()
    for event, groups in hooks.items():
        if event in {"managed_dir", "windows_managed_dir"} and isinstance(groups, str):
            continue
        if not isinstance(groups, list):
            return invalid()
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                return invalid()
            for hook in group["hooks"]:
                if not isinstance(hook, dict) or not isinstance(hook.get("type"), str):
                    return invalid()
                if hook["type"] == "command" and (
                    not isinstance(hook.get("command"), str) or not hook["command"].strip()
                ):
                    return invalid()
    return []
