from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
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
    try:
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
    except (OSError, RuntimeError, ValueError) as exc:
        return TeamResult([], [str(exc)])


def preview_team(target: Path, manifest: str | None = None) -> TeamResult:
    root = target.expanduser().resolve()
    try:
        if manifest:
            with tempfile.TemporaryDirectory() as temp:
                source = _resolve_manifest(Path(temp), manifest)
                payload = _read_manifest(source)
                result = _sync_team_payload(root, payload, dry_run=True)
                return TeamResult([f"Preview team manifest: {source}", *result.actions], result.warnings)
        local = root / ".coding-scaffold" / "team-onboarding.json"
        payload = _read_manifest(local)
        return _sync_team_payload(root, payload, dry_run=True)
    except (OSError, RuntimeError, ValueError) as exc:
        return TeamResult([], [str(exc)])


def sync_team(target: Path, *, dry_run: bool = False) -> TeamResult:
    root = target.expanduser().resolve()
    manifest = root / ".coding-scaffold" / "team-onboarding.json"
    if not manifest.exists():
        return TeamResult([], ["No team manifest found. Run `coding-scaffold team init` or `team connect`."])
    try:
        payload = _read_manifest(manifest)
        return _sync_team_payload(root, payload, dry_run=dry_run)
    except (OSError, RuntimeError, ValueError) as exc:
        return TeamResult([], [str(exc)])


def _sync_team_payload(root: Path, payload: dict[str, object], *, dry_run: bool) -> TeamResult:
    actions: list[str] = []
    warnings: list[str] = []

    knowledge = _dict(payload.get("knowledge"))
    knowledge_remote = str(knowledge.get("remote") or "")
    if knowledge_remote:
        destination = root / str(knowledge.get("path") or ".coding-scaffold/knowledge")
        message, warning = _sync_source(knowledge_remote, destination, dry_run=dry_run)
        actions.append(f"Knowledge: {message}")
        if warning:
            warnings.append(warning)

    for remote in _remotes(payload, "skills"):
        source, message, warning = _sync_shared_source(root, remote, "skills", dry_run=dry_run)
        actions.append(f"Skills source: {message}")
        if warning:
            warnings.append(warning)
        _copy_markdown(source, root / ".coding-scaffold" / "skills", actions, "skill", dry_run=dry_run)

    for remote in _remotes(payload, "agents"):
        source, message, warning = _sync_shared_source(root, remote, "agents", dry_run=dry_run)
        actions.append(f"Agents source: {message}")
        if warning:
            warnings.append(warning)
        _copy_markdown(source, root / ".opencode" / "agents", actions, "agent", dry_run=dry_run)

    for remote in _remotes(payload, "configs"):
        source, message, warning = _sync_shared_source(root, remote, "configs", dry_run=dry_run)
        actions.append(f"Config source: {message}")
        if warning:
            warnings.append(warning)
        _copy_tree(source, root / ".coding-scaffold" / "configs", actions, "config", dry_run=dry_run)

    policy = _dict(payload.get("policy"))
    policy_remote = str(policy.get("remote") or "")
    if policy_remote:
        source, message, warning = _sync_shared_source(root, policy_remote, "policy", dry_run=dry_run)
        actions.append(f"Policy source: {message}")
        if warning:
            warnings.append(warning)
        _copy_tree(
            source,
            root / ".coding-scaffold" / "policy" / "imported",
            actions,
            "policy",
            dry_run=dry_run,
        )

    if not dry_run:
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
    path = source_dir / "team-onboarding.json"
    if path.exists():
        return path
    raise FileNotFoundError(f"No team-onboarding manifest found in {manifest}")


def _read_manifest(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".json":
        raise ValueError("Team onboarding manifests must be JSON. Use team-onboarding.json.")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Team manifest must be an object.")
    if _dict(payload.get("security")).get("secrets_allowed") is True:
        raise ValueError("Team manifest cannot allow secrets.")
    return payload


def _remotes(payload: dict[str, object], key: str) -> list[str]:
    values = _dict(payload.get(key)).get("remotes")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if value]


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _sync_shared_source(
    root: Path,
    remote: str,
    kind: str,
    *,
    dry_run: bool,
) -> tuple[Path, str, str | None]:
    destination = root / ".coding-scaffold" / "team" / "sources" / kind / _slug(remote)
    candidate = Path(remote).expanduser()
    message, warning = _sync_source(remote, destination, dry_run=dry_run)
    source = candidate if dry_run and candidate.exists() else destination
    return source, message, warning


def _sync_source(remote: str, destination: Path, *, dry_run: bool) -> tuple[str, str | None]:
    source = Path(remote).expanduser()
    if source.exists():
        if source.resolve() == destination.resolve():
            return f"already connected to {remote}", None
        if dry_run:
            return f"would copy {remote}", None
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git"))
        return f"copied {remote}", None
    return _clone_or_pull(remote, destination, dry_run=dry_run), None


def _clone_or_pull(remote: str, destination: Path, *, dry_run: bool = False) -> str:
    if shutil.which("git") is None:
        raise RuntimeError(
            "git is required for team manifests pointing to a remote URL. "
            "Install git or pass a local path."
        )
    if dry_run:
        return f"would clone/update {remote}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not (destination / ".git").exists():
            shutil.rmtree(destination)
        else:
            completed = subprocess.run(["git", "-C", str(destination), "pull", "--ff-only"], check=False)
            if completed.returncode == 0:
                _remove_nested_git(destination)
                return f"updated {remote}"
            return f"kept existing checkout for {remote}; git pull failed"
    if not destination.exists():
        completed = subprocess.run(["git", "clone", remote, str(destination)], check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"Could not clone {remote}")
        _remove_nested_git(destination)
    return f"cloned {remote}"


def _remove_nested_git(destination: Path) -> None:
    git_dir = destination / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)


def _copy_markdown(
    source: Path,
    destination: Path,
    actions: list[str],
    label: str,
    *,
    dry_run: bool,
) -> None:
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*.md"):
        relative = path.relative_to(source)
        if dry_run:
            actions.append(f"Would import {label}: {relative} -> {destination / relative}")
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        actions.append(f"Imported {label}: {relative}")


def _copy_tree(
    source: Path,
    destination: Path,
    actions: list[str],
    label: str,
    *,
    dry_run: bool,
) -> None:
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_dir() or ".git" in path.parts:
            continue
        relative = path.relative_to(source)
        if dry_run:
            actions.append(f"Would import {label}: {relative} -> {destination / relative}")
            continue
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
