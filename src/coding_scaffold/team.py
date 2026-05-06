from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class TeamResult:
    actions: list[str]
    warnings: list[str]


def write_team_manifest(
    target: Path,
    team: str = "team",
    knowledge_remote: str | None = None,
    knowledge_backend: str = "markdown",
    default_tool: str = "opencode",
) -> Path:
    root = target.expanduser().resolve()
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "team-onboarding.json"
    payload = {
        "team": team,
        "knowledge": {
            "backend": knowledge_backend,
            "path": ".coding-scaffold/knowledge",
            "remote": knowledge_remote or "",
        },
        "skills": {"remotes": []},
        "agents": {"remotes": []},
        "policy": {"remote": "", "scope": "team"},
        "configs": {"remotes": []},
        "tools": {
            "default": default_tool,
            "required_addons": ["llmfit"],
            "optional_addons": ["obsidian", "routellm", "open-multi-agent"],
        },
        "security": {
            "secrets_allowed": False,
            "review_imported_changes": True,
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def connect_team(target: Path, manifest: str | None = None) -> TeamResult:
    root = target.expanduser().resolve()
    source = _resolve_manifest(root, manifest)
    payload = _read_manifest(source)
    local_manifest = root / ".coding-scaffold" / "team-onboarding.json"
    local_manifest.parent.mkdir(parents=True, exist_ok=True)
    local_manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = sync_team(target)
    return TeamResult(
        [f"Connected team manifest: {source}", *result.actions],
        result.warnings,
    )


def sync_team(target: Path) -> TeamResult:
    root = target.expanduser().resolve()
    manifest = root / ".coding-scaffold" / "team-onboarding.json"
    if not manifest.exists():
        return TeamResult([], ["No team manifest found. Run `coding-scaffold team init` or `team connect`."])
    payload = _read_manifest(manifest)
    actions: list[str] = []
    warnings: list[str] = []

    knowledge = _dict(payload.get("knowledge"))
    knowledge_remote = str(knowledge.get("remote") or "")
    if knowledge_remote:
        destination = root / str(knowledge.get("path") or ".coding-scaffold/knowledge")
        message, warning = _sync_source(knowledge_remote, destination)
        actions.append(f"Knowledge: {message}")
        if warning:
            warnings.append(warning)

    for remote in _remotes(payload, "skills"):
        source, message, warning = _sync_shared_source(root, remote, "skills")
        actions.append(f"Skills source: {message}")
        if warning:
            warnings.append(warning)
        _copy_markdown(source, root / ".coding-scaffold" / "skills", actions, "skill")

    for remote in _remotes(payload, "agents"):
        source, message, warning = _sync_shared_source(root, remote, "agents")
        actions.append(f"Agents source: {message}")
        if warning:
            warnings.append(warning)
        _copy_markdown(source, root / ".opencode" / "agents", actions, "agent")

    for remote in _remotes(payload, "configs"):
        source, message, warning = _sync_shared_source(root, remote, "configs")
        actions.append(f"Config source: {message}")
        if warning:
            warnings.append(warning)
        _copy_tree(source, root / ".coding-scaffold" / "configs", actions, "config")

    policy = _dict(payload.get("policy"))
    policy_remote = str(policy.get("remote") or "")
    if policy_remote:
        source, message, warning = _sync_shared_source(root, policy_remote, "policy")
        actions.append(f"Policy source: {message}")
        if warning:
            warnings.append(warning)
        _copy_tree(source, root / ".coding-scaffold" / "policy" / "imported", actions, "policy")

    _write_provenance(root, payload, actions)
    return TeamResult(actions, warnings)


def doctor_team(target: Path) -> TeamResult:
    root = target.expanduser().resolve()
    manifest = root / ".coding-scaffold" / "team-onboarding.json"
    actions: list[str] = []
    warnings: list[str] = []
    if not manifest.exists():
        return TeamResult([], ["No team manifest found."])
    payload = _read_manifest(manifest)
    actions.append(f"Team: {payload.get('team', 'unknown')}")
    knowledge = _dict(payload.get("knowledge"))
    knowledge_path = root / str(knowledge.get("path") or ".coding-scaffold/knowledge")
    actions.append(f"Knowledge path: {'present' if knowledge_path.exists() else 'missing'}")
    skills = root / ".coding-scaffold" / "skills"
    agents = root / ".opencode" / "agents"
    actions.append(f"Skills available: {len(list(skills.glob('*.md'))) if skills.exists() else 0}")
    actions.append(f"Agents available: {len(list(agents.glob('*.md'))) if agents.exists() else 0}")
    if not (root / ".coding-scaffold" / "team-provenance.json").exists():
        warnings.append("No team provenance found. Run `coding-scaffold team sync`.")
    return TeamResult(actions, warnings)


def _resolve_manifest(root: Path, manifest: str | None) -> Path:
    if not manifest:
        return root / ".coding-scaffold" / "team-onboarding.json"
    candidate = Path(manifest).expanduser()
    if candidate.exists():
        return candidate.resolve()
    source_dir = root / ".coding-scaffold" / "team" / "manifest-source"
    _clone_or_pull(manifest, source_dir)
    for name in ["team-onboarding.json", "team-onboarding.yaml", "team-onboarding.yml"]:
        path = source_dir / name
        if path.exists():
            return path
    raise FileNotFoundError(f"No team-onboarding manifest found in {manifest}")


def _read_manifest(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        payload = json.loads(text)
    else:
        payload = _parse_simple_yaml(text)
    if not isinstance(payload, dict):
        raise ValueError("Team manifest must be an object.")
    if _dict(payload.get("security")).get("secrets_allowed") is True:
        raise ValueError("Team manifest cannot allow secrets.")
    return payload


def _parse_simple_yaml(text: str) -> dict[str, object]:
    lines = [
        line
        for raw in text.splitlines()
        if (line := raw.split("#", 1)[0].rstrip()).strip()
    ]
    payload, _ = _parse_yaml_block(lines, 0, 0)
    return payload if isinstance(payload, dict) else {}


def _parse_yaml_block(lines: list[str], index: int, indent: int) -> tuple[object, int]:
    if index >= len(lines):
        return {}, index
    if _indent(lines[index]) == indent and lines[index].strip().startswith("- "):
        items: list[object] = []
        while index < len(lines) and _indent(lines[index]) == indent:
            item = lines[index].strip()
            if not item.startswith("- "):
                break
            items.append(_scalar(item[2:].strip()))
            index += 1
        return items, index
    mapping: dict[str, object] = {}
    while index < len(lines):
        current_indent = _indent(lines[index])
        if current_indent < indent:
            break
        if current_indent > indent:
            index += 1
            continue
        item = lines[index].strip()
        key, _, value = item.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            mapping[key] = _scalar(value)
            index += 1
            continue
        child_indent = _next_indent(lines, index + 1, indent)
        if child_indent is None:
            mapping[key] = {}
            index += 1
            continue
        child, index = _parse_yaml_block(lines, index + 1, child_indent)
        mapping[key] = child
    return mapping, index


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_indent(lines: list[str], index: int, current: int) -> int | None:
    if index >= len(lines):
        return None
    value = _indent(lines[index])
    return value if value > current else None


def _scalar(value: str) -> object:
    cleaned = value.strip().strip('"').strip("'")
    if cleaned.lower() == "true":
        return True
    if cleaned.lower() == "false":
        return False
    return cleaned


def _remotes(payload: dict[str, object], key: str) -> list[str]:
    values = _dict(payload.get(key)).get("remotes")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if value]


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _sync_shared_source(root: Path, remote: str, kind: str) -> tuple[Path, str, str | None]:
    destination = root / ".coding-scaffold" / "team" / "sources" / kind / _slug(remote)
    message, warning = _sync_source(remote, destination)
    return destination, message, warning


def _sync_source(remote: str, destination: Path) -> tuple[str, str | None]:
    source = Path(remote).expanduser()
    if source.exists():
        if source.resolve() == destination.resolve():
            return f"already connected to {remote}", None
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git"))
        return f"copied {remote}", None
    return _clone_or_pull(remote, destination), None


def _clone_or_pull(remote: str, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        completed = subprocess.run(["git", "-C", str(destination), "pull", "--ff-only"], check=False)
        if completed.returncode == 0:
            return f"updated {remote}"
        return f"kept existing checkout for {remote}; git pull failed"
    completed = subprocess.run(["git", "clone", remote, str(destination)], check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Could not clone {remote}")
    return f"cloned {remote}"


def _copy_markdown(source: Path, destination: Path, actions: list[str], label: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*.md"):
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        actions.append(f"Imported {label}: {relative}")


def _copy_tree(source: Path, destination: Path, actions: list[str], label: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_dir() or ".git" in path.parts:
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        actions.append(f"Imported {label}: {relative}")


def _write_provenance(root: Path, manifest: dict[str, object], actions: list[str]) -> None:
    path = root / ".coding-scaffold" / "team-provenance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "team": manifest.get("team", "unknown"),
        "last_sync": datetime.now(UTC).isoformat(),
        "mode": "copy",
        "secrets_allowed": False,
        "actions": actions,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    parsed = urlparse(value)
    base = parsed.path or value
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", base.strip("/").lower()).strip("-")
    return slug or "source"
