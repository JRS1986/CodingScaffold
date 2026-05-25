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

from . import __version__

ALLOWED_REMOTE_SCHEMES = ("https", "http", "ssh")
SOURCES_SUBDIR = Path(".coding-scaffold") / "team" / "sources"
KNOWLEDGE_FORBIDDEN_PREFIX = Path(".coding-scaffold") / "knowledge"
MANIFEST_SCHEMA_VERSION = 1
DEFAULT_MANIFEST_VERSION = "1.0.0"
SUBSET_TIGHTEN_FIELDS = {
    "mcp.allowlist",
    "policy.allowed_mcp_servers",
    "policy.allowed_providers",
}
SUPERSET_TIGHTEN_FIELDS = {
    "security.required_review_modes",
    "tools.required_addons",
}
UNION_FIELDS = {
    "agents.remotes",
    "configs.remotes",
    "skills.remotes",
}


@dataclass(frozen=True)
class TeamResult:
    actions: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class ManifestSource:
    path: Path
    source: str
    source_ref: str | None = None


@dataclass(frozen=True)
class EffectiveManifest:
    payload: dict[str, object]
    layers: list[dict[str, object]]
    field_provenance: dict[str, dict[str, object]]


@dataclass(frozen=True)
class TeamDoctorReport:
    actions: list[str]
    warnings: list[str]
    payload: dict[str, object]
    layers: list[dict[str, object]]
    field_provenance: dict[str, dict[str, object]]
    stale_pulls: list[dict[str, object]]
    inbound_nominations: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "actions": self.actions,
            "warnings": self.warnings,
            "manifest": self.payload,
            "layers": self.layers,
            "field_provenance": self.field_provenance,
            "stale_pulls": self.stale_pulls,
            "inbound_nominations": self.inbound_nominations,
        }


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
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_version": DEFAULT_MANIFEST_VERSION,
        "min_scaffold_version": "0.5.0",
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
            "optional_addons": ["obsidian", "routellm", "open-multi-agent", "caveman-compression"],
        },
        "security": {
            "secrets_allowed": False,
            "review_imported_changes": True,
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def connect_team(
    target: Path,
    manifest: str | None = None,
    *,
    allow_local: bool = False,
    to_version: str | None = None,
    to_ref: str | None = None,
) -> TeamResult:
    root = target.expanduser().resolve()
    try:
        source = _resolve_manifest(root, manifest, to_ref=to_ref)
        payload = _read_manifest(source.path, to_version=to_version)
        if manifest:
            payload.setdefault(
                "_sync_source",
                {
                    "manifest": manifest,
                    "source_ref": source.source_ref or "",
                },
            )
        local_manifest = root / ".coding-scaffold" / "team-onboarding.json"
        local_manifest.parent.mkdir(parents=True, exist_ok=True)
        local_manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = sync_team(target, allow_local=allow_local, to_version=to_version)
        return TeamResult(
            [f"Connected team manifest: {source.path}", *result.actions],
            result.warnings,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return TeamResult([], [str(exc)])


def preview_team(
    target: Path,
    manifest: str | None = None,
    *,
    allow_local: bool = False,
    to_version: str | None = None,
    to_ref: str | None = None,
) -> TeamResult:
    root = target.expanduser().resolve()
    try:
        if manifest:
            with tempfile.TemporaryDirectory() as temp:
                source = _resolve_manifest(Path(temp), manifest, to_ref=to_ref)
                payload = _read_manifest(source.path, to_version=to_version)
                result = _sync_team_payload(
                    root,
                    payload,
                    dry_run=True,
                    allow_local=allow_local,
                    to_version=to_version,
                    manifest_source=source,
                )
                return TeamResult([f"Preview team manifest: {source.path}", *result.actions], result.warnings)
        local = root / ".coding-scaffold" / "team-onboarding.json"
        payload = _read_manifest(local, to_version=to_version)
        return _sync_team_payload(
            root,
            payload,
            dry_run=True,
            allow_local=allow_local,
            to_version=to_version,
            manifest_source=ManifestSource(local, str(local), _source_ref(local)),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return TeamResult([], [str(exc)])


def sync_team(
    target: Path,
    *,
    dry_run: bool = False,
    allow_local: bool = False,
    to_version: str | None = None,
    to_ref: str | None = None,
) -> TeamResult:
    root = target.expanduser().resolve()
    manifest = root / ".coding-scaffold" / "team-onboarding.json"
    if not manifest.exists():
        return TeamResult([], ["No team manifest found. Run `coding-scaffold team init` or `team connect`."])
    try:
        payload = _read_manifest(manifest, to_version=to_version)
        sync_source = _dict(payload.get("_sync_source"))
        if to_ref:
            if not sync_source.get("manifest"):
                return TeamResult([], ["team sync --to-ref requires a manifest previously connected from a source."])
            source = _resolve_manifest(root, str(sync_source["manifest"]), to_ref=to_ref)
            payload = _read_manifest(source.path, to_version=to_version)
        else:
            source = ManifestSource(manifest, str(manifest), _source_ref(manifest))
        return _sync_team_payload(
            root,
            payload,
            dry_run=dry_run,
            allow_local=allow_local,
            to_version=to_version,
            manifest_source=source,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return TeamResult([], [str(exc)])


def _sync_team_payload(
    root: Path,
    payload: dict[str, object],
    *,
    dry_run: bool,
    allow_local: bool,
    to_version: str | None = None,
    manifest_source: ManifestSource | None = None,
) -> TeamResult:
    actions: list[str] = []
    warnings: list[str] = []
    effective = _effective_manifest(root, payload, allow_local=allow_local)
    payload = effective.payload
    _validate_manifest_payload(payload, to_version=to_version)

    knowledge = _dict(payload.get("knowledge"))
    knowledge_remote = str(knowledge.get("remote") or "")
    if knowledge_remote:
        # Refuse any manifest-supplied path that resolves under
        # .coding-scaffold/knowledge/ — the user's curated knowledge dir is
        # off-limits to team sync.
        manifest_path = str(knowledge.get("path") or "")
        if manifest_path and _resolves_under_knowledge(root, manifest_path):
            warnings.append(
                "Team manifest knowledge.path resolves under .coding-scaffold/knowledge/. "
                "Falling back to the safe team/sources/knowledge/<slug>/ location."
            )
        try:
            destination = _team_destination(root, "knowledge", knowledge_remote)
        except ValueError as exc:
            warnings.append(str(exc))
        else:
            message, warning = _sync_source(
                knowledge_remote,
                destination,
                dry_run=dry_run,
                allow_local=allow_local,
            )
            actions.append(f"Knowledge: {message}")
            if warning:
                warnings.append(warning)

    for remote in _remotes(payload, "skills"):
        source, message, warning = _sync_shared_source(
            root, remote, "skills", dry_run=dry_run, allow_local=allow_local
        )
        actions.append(f"Skills source: {message}")
        if warning:
            warnings.append(warning)
        if source is not None:
            _copy_markdown(source, root / ".coding-scaffold" / "skills", actions, "skill", dry_run=dry_run)

    for remote in _remotes(payload, "agents"):
        source, message, warning = _sync_shared_source(
            root, remote, "agents", dry_run=dry_run, allow_local=allow_local
        )
        actions.append(f"Agents source: {message}")
        if warning:
            warnings.append(warning)
        if source is not None:
            _copy_markdown(source, root / ".opencode" / "agents", actions, "agent", dry_run=dry_run)

    for remote in _remotes(payload, "configs"):
        source, message, warning = _sync_shared_source(
            root, remote, "configs", dry_run=dry_run, allow_local=allow_local
        )
        actions.append(f"Config source: {message}")
        if warning:
            warnings.append(warning)
        if source is not None:
            _copy_tree(source, root / ".coding-scaffold" / "configs", actions, "config", dry_run=dry_run)

    policy = _dict(payload.get("policy"))
    policy_remote = str(policy.get("remote") or "")
    if policy_remote:
        source, message, warning = _sync_shared_source(
            root, policy_remote, "policy", dry_run=dry_run, allow_local=allow_local
        )
        actions.append(f"Policy source: {message}")
        if warning:
            warnings.append(warning)
        if source is not None:
            _copy_tree(
                source,
                root / ".coding-scaffold" / "policy" / "imported",
                actions,
                "policy",
                dry_run=dry_run,
                local_override_base=root / ".coding-scaffold" / "policy",
            )

    if not dry_run:
        _write_provenance(
            root,
            payload,
            actions,
            layers=effective.layers,
            manifest_source=manifest_source,
            field_provenance=effective.field_provenance,
        )
    return TeamResult(actions, warnings)


def inspect_team_doctor(target: Path) -> TeamDoctorReport:
    root = target.expanduser().resolve()
    manifest = root / ".coding-scaffold" / "team-onboarding.json"
    actions: list[str] = []
    warnings: list[str] = []
    if not manifest.exists():
        return TeamDoctorReport([], ["No team manifest found."], {}, [], {}, [], [])
    payload = _read_manifest(manifest)
    effective = _effective_manifest(root, payload, allow_local=True)
    payload = effective.payload
    layers = effective.layers
    actions.append(f"Team: {payload.get('team', 'unknown')}")
    actions.append(f"Manifest version: {payload.get('manifest_version', 'legacy')}")
    if payload.get("min_scaffold_version"):
        actions.append(f"Minimum scaffold version: {payload['min_scaffold_version']}")
    for layer in layers:
        layer_name = layer.get("team") or layer.get("source") or "unknown"
        actions.append(f"Manifest layer: {layer_name} ({layer.get('manifest_version', 'legacy')})")
    knowledge = _dict(payload.get("knowledge"))
    knowledge_path = root / str(knowledge.get("path") or ".coding-scaffold/knowledge")
    actions.append(f"Knowledge path: {'present' if knowledge_path.exists() else 'missing'}")
    skills = root / ".coding-scaffold" / "skills"
    agents = root / ".opencode" / "agents"
    actions.append(f"Skills available: {len(list(skills.glob('*.md'))) if skills.exists() else 0}")
    actions.append(f"Agents available: {len(list(agents.glob('*.md'))) if agents.exists() else 0}")
    for field, info in sorted(effective.field_provenance.items()):
        actions.append(
            f"Effective field: {field} = {_format_field_value(info.get('value'))} "
            f"[{info.get('layer', 'unknown')}]"
        )
    actions.extend(_effective_artifact_lines(root))
    provenance = _read_provenance(root)
    stale_pulls = _list_recent_stale_pulls(provenance)
    inbound_nominations = _list_inbound_nominations(provenance)
    for failure in stale_pulls:
        warnings.append(
            f"Recent team source update failed for {failure.get('remote', 'unknown')}: "
            f"{failure.get('error', 'git pull failed')} "
            f"(first seen {failure.get('first_seen', 'unknown')}, last seen {failure.get('last_seen', 'unknown')})"
        )
    for nomination in inbound_nominations:
        actions.append(
            "Inbound nomination: "
            f"{nomination.get('slug', 'unknown')} from {nomination.get('source_team', 'unknown')} "
            f"({nomination.get('manifest_ref', 'unknown ref')})"
        )
    if not provenance:
        warnings.append("No team provenance found. Run `coding-scaffold team sync`.")
    return TeamDoctorReport(
        actions,
        warnings,
        payload,
        layers,
        effective.field_provenance,
        stale_pulls,
        inbound_nominations,
    )


def doctor_team(target: Path) -> TeamResult:
    report = inspect_team_doctor(target)
    return TeamResult(report.actions, report.warnings)


def push_team(target: Path, *, dry_run: bool = False, open_pr: bool = False) -> TeamResult:
    root = target.expanduser().resolve()
    candidates = _nomination_candidates(root)
    if dry_run:
        if not candidates:
            return TeamResult(["No local artifacts differ from imported team sources."], [])
        return TeamResult([f"Would nominate {kind}: {relative}" for kind, relative, _ in candidates], [])
    if not candidates:
        return TeamResult(["No local artifacts differ from imported team sources."], [])
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    outbox = root / ".coding-scaffold" / "team" / "outbox" / stamp
    outbox.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Team Nomination",
        "",
        f"Created: {datetime.now(UTC).isoformat()}",
        f"Source repository: {root.name}",
        "",
        "## Candidates",
        "",
    ]
    actions: list[str] = []
    for kind, relative, path in candidates:
        destination = outbox / kind / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        lines.append(f"- `{kind}/{relative.as_posix()}` from `{path.relative_to(root).as_posix()}`")
        actions.append(f"Nominated {kind}: {relative}")
    nominated_at = datetime.now(UTC).isoformat()
    lines.extend(
        [
            "",
            "## Rationale",
            "",
            "Explain why these local artifacts should become team defaults before opening review.",
            "",
            "## Proposed Manifest Changes",
            "",
            "Update the team manifest after human review accepts the nomination.",
        ]
    )
    (outbox / "nomination.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_inbound_nomination_metadata(root, outbox, candidates, nominated_at)
    _record_nomination(root, outbox, actions)
    result_actions = [f"Wrote nomination bundle: {outbox}", *actions]
    warnings: list[str] = []
    if open_pr:
        pr_url, warning = _open_nomination_pr(root, outbox)
        if pr_url:
            result_actions.append(f"Opened draft PR: {pr_url}")
        if warning:
            warnings.append(warning)
    return TeamResult(result_actions, warnings)


def _resolve_manifest(root: Path, manifest: str | None, *, to_ref: str | None = None) -> ManifestSource:
    if not manifest:
        path = root / ".coding-scaffold" / "team-onboarding.json"
        return ManifestSource(path, str(path), _source_ref(path))
    candidate = Path(manifest).expanduser()
    if candidate.exists():
        resolved = candidate.resolve()
        if resolved.is_dir():
            resolved = resolved / "team-onboarding.json"
        return ManifestSource(resolved, str(candidate), _source_ref(resolved))
    source_dir = root / ".coding-scaffold" / "team" / "manifest-source"
    _clone_or_pull(manifest, source_dir, ref=to_ref)
    repo_dir = source_dir / "_repo"
    for candidate_path in (repo_dir / "team-onboarding.json", source_dir / "team-onboarding.json"):
        if candidate_path.exists():
            return ManifestSource(candidate_path, manifest, _source_ref(candidate_path))
    raise FileNotFoundError(f"No team-onboarding manifest found in {manifest}")


def _read_manifest(path: Path, *, to_version: str | None = None) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".json":
        raise ValueError("Team onboarding manifests must be JSON. Use team-onboarding.json.")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Team manifest must be an object.")
    _validate_manifest_payload(payload, to_version=to_version)
    return payload


def _validate_manifest_payload(payload: dict[str, object], *, to_version: str | None = None) -> None:
    schema_version = payload.get("manifest_schema_version")
    if schema_version is not None and schema_version != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported team manifest schema version {schema_version!r}; "
            f"this scaffold supports {MANIFEST_SCHEMA_VERSION}."
        )
    manifest_version = payload.get("manifest_version")
    if manifest_version is not None and not _valid_semver(str(manifest_version)):
        raise ValueError(f"Invalid team manifest version {manifest_version!r}; expected MAJOR.MINOR.PATCH.")
    if to_version and str(manifest_version or "") != to_version:
        raise ValueError(
            f"Requested manifest version {to_version}, but manifest is {manifest_version or 'legacy'}."
        )
    minimum = payload.get("min_scaffold_version")
    if minimum and _compare_semver(str(minimum), __version__) > 0:
        raise ValueError(
            f"Team manifest requires coding-scaffold >= {minimum}; installed version is {__version__}. "
            "Upgrade coding-scaffold or sync an older manifest version."
        )
    if _dict(payload.get("security")).get("secrets_allowed") is True:
        raise ValueError("Team manifest cannot allow secrets.")


def _remotes(payload: dict[str, object], key: str) -> list[str]:
    values = _dict(payload.get(key)).get("remotes")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if value]


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _classify_remote(remote: str) -> str:
    """Return 'url', 'local', or raise ValueError for empty/unknown."""
    if not remote:
        raise ValueError("Remote is empty.")
    if "://" in remote:
        scheme = remote.split("://", 1)[0].lower()
        if scheme in ALLOWED_REMOTE_SCHEMES:
            return "url"
        if scheme == "file":
            return "local"
        raise ValueError(f"Unsupported remote scheme: {scheme}")
    if remote.startswith("git@"):
        return "url"
    return "local"  # bare path


def _team_destination(root: Path, kind: str, remote: str) -> Path:
    """Compute the team-sources destination for a (kind, remote) pair.
    Always lives under SOURCES_SUBDIR — never under knowledge/."""
    slug = _slug(remote)
    return root / SOURCES_SUBDIR / kind / slug


def _resolves_under_knowledge(root: Path, manifest_path: str) -> bool:
    """True if a manifest-supplied path resolves inside .coding-scaffold/knowledge/."""
    try:
        candidate = (root / manifest_path).resolve()
    except (OSError, RuntimeError):
        return False
    forbidden = (root / KNOWLEDGE_FORBIDDEN_PREFIX).resolve()
    try:
        candidate.relative_to(forbidden)
        return True
    except ValueError:
        return False


def _sync_shared_source(
    root: Path,
    remote: str,
    kind: str,
    *,
    dry_run: bool,
    allow_local: bool,
) -> tuple[Path | None, str, str | None]:
    try:
        destination = _team_destination(root, kind, remote)
    except ValueError as exc:
        return None, f"refused {remote}", str(exc)
    message, warning = _sync_source(remote, destination, dry_run=dry_run, allow_local=allow_local)
    if warning and message.startswith(("refused", "skipped")):
        return None, message, warning
    source = destination
    if dry_run:
        candidate = Path(remote).expanduser()
        if candidate.exists():
            source = candidate
    return source, message, warning


def _sync_source(
    remote: str,
    destination: Path,
    *,
    dry_run: bool,
    allow_local: bool,
) -> tuple[str, str | None]:
    """Copy or clone `remote` into `destination`. Never touches paths outside
    SOURCES_SUBDIR."""
    try:
        classification = _classify_remote(remote)
    except ValueError as exc:
        return f"refused {remote}", str(exc)

    if classification == "local" and not allow_local:
        return (
            f"refused {remote}",
            f"Local path remote {remote!r} requires --allow-local. Skipped.",
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if classification == "local":
        # Strip file:// if present.
        if remote.startswith("file://"):
            source_str = remote[len("file://") :]
        else:
            source_str = remote
        source = Path(source_str).expanduser()
        if not source.exists():
            return f"skipped {remote}", f"Local path does not exist: {remote}"
        if dry_run:
            return f"would copy {remote}", None
        # Stage into _repo to mirror clone layout (no .git for local copies).
        repo_dir = destination / "_repo"
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, repo_dir, ignore=shutil.ignore_patterns(".git"))
        _publish_repo_contents(repo_dir, destination)
        return f"copied {remote}", None
    # URL clone
    message = _clone_or_pull(remote, destination, dry_run=dry_run)
    if "git pull failed" in message:
        return message, message
    return message, None


def _clone_or_pull(
    remote: str,
    destination: Path,
    *,
    dry_run: bool = False,
    ref: str | None = None,
) -> str:
    if shutil.which("git") is None:
        raise RuntimeError(
            "git is required for team manifests pointing to a remote URL. "
            "Install git or pass a local path with --allow-local."
        )
    if dry_run:
        return f"would clone/update {remote}"
    repo_dir = destination / "_repo"
    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    if (repo_dir / ".git").exists():
        completed = subprocess.run(
            ["git", "-C", str(repo_dir), "pull", "--ff-only"],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode == 0:
            if ref:
                _checkout_ref(repo_dir, ref)
            _publish_repo_contents(repo_dir, destination)
            suffix = f" at {ref}" if ref else ""
            return f"updated {remote}{suffix}"
        error = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
        return f"kept existing checkout for {remote}; git pull failed: {error}"
    # Fresh clone (or recovery from a stale partial checkout)
    if destination.exists() and any(destination.iterdir()):
        # Move aside, don't delete user-visible content.
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        legacy = destination.with_name(destination.name + f".legacy-{timestamp}")
        destination.rename(legacy)
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "clone", remote, str(repo_dir)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Could not clone {remote}: {completed.stderr.strip()}")
    if ref:
        _checkout_ref(repo_dir, ref)
    _publish_repo_contents(repo_dir, destination)
    suffix = f" at {ref}" if ref else ""
    return f"cloned {remote}{suffix}"


def _checkout_ref(repo_dir: Path, ref: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_dir), "checkout", "--detach", ref],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Could not checkout manifest ref {ref}: {completed.stderr.strip()}")


def _publish_repo_contents(repo_dir: Path, destination: Path) -> None:
    """Copy files from repo_dir to destination root, skipping any .git
    directories at any depth (handles submodules). Idempotent — clears
    previously published files first but never deletes the _repo subdir."""
    if destination.exists():
        for stale in destination.iterdir():
            if stale.name == "_repo":
                continue
            if stale.is_dir():
                shutil.rmtree(stale)
            else:
                stale.unlink()
    if not repo_dir.exists():
        return
    for path in repo_dir.rglob("*"):
        if ".git" in path.parts:
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(repo_dir)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


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
        if ".git" in path.parts or "_repo" in path.parts:
            continue
        relative = path.relative_to(source)
        if dry_run:
            actions.append(f"Would import {label}: {relative} -> {destination / relative}")
            continue
        target = destination / relative
        _copy_with_conflict(path, target, actions, label, relative, dry_run=dry_run)


def _copy_tree(
    source: Path,
    destination: Path,
    actions: list[str],
    label: str,
    *,
    dry_run: bool,
    local_override_base: Path | None = None,
) -> None:
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_dir() or ".git" in path.parts or "_repo" in path.parts:
            continue
        relative = path.relative_to(source)
        if dry_run:
            actions.append(f"Would import {label}: {relative} -> {destination / relative}")
            continue
        target = destination / relative
        _copy_with_conflict(path, target, actions, label, relative, dry_run=dry_run)
        if local_override_base is not None:
            local_override = local_override_base / relative
            if local_override.exists() and not _same_file(path, local_override):
                conflict = local_override.with_name(local_override.name + ".conflict")
                if dry_run:
                    actions.append(f"Would flag {label} override conflict: {relative} -> {conflict}")
                else:
                    shutil.copy2(path, conflict)
                    actions.append(f"Flagged {label} override conflict: {relative}")


def _copy_with_conflict(
    source: Path,
    target: Path,
    actions: list[str],
    label: str,
    relative: Path,
    *,
    dry_run: bool,
) -> None:
    if target.exists():
        if _same_file(source, target):
            actions.append(f"{label.title()} unchanged: {relative}")
            return
        conflict = target.with_name(target.name + ".conflict")
        if dry_run:
            actions.append(f"Would write {label} conflict: {relative} -> {conflict}")
            return
        conflict.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, conflict)
        actions.append(f"Conflict for {label}: kept local {relative}; wrote {conflict.name}")
        return
    if dry_run:
        actions.append(f"Would import {label}: {relative} -> {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    actions.append(f"Imported {label}: {relative}")


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def _write_provenance(
    root: Path,
    manifest: dict[str, object],
    actions: list[str],
    *,
    layers: list[dict[str, object]],
    manifest_source: ManifestSource | None,
    field_provenance: dict[str, dict[str, object]],
) -> None:
    path = root / ".coding-scaffold" / "team-provenance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = _read_provenance(root)
    new_stale_pulls = _stale_pulls_from_actions(actions)
    payload = {
        "team": manifest.get("team", "unknown"),
        "manifest_version": manifest.get("manifest_version", "legacy"),
        "manifest_schema_version": manifest.get("manifest_schema_version", "legacy"),
        "min_scaffold_version": manifest.get("min_scaffold_version", ""),
        "manifest_source": manifest_source.source if manifest_source else "",
        "source_ref": manifest_source.source_ref if manifest_source else "",
        "layers": layers,
        "field_provenance": field_provenance,
        "stale_pulls": _merge_stale_pulls(previous.get("stale_pulls"), new_stale_pulls),
        "inbound_nominations": _collect_inbound_nominations(root, manifest_source),
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


def _effective_manifest(
    root: Path,
    payload: dict[str, object],
    *,
    allow_local: bool,
) -> EffectiveManifest:
    return _effective_manifest_inner(root, payload, allow_local=allow_local, seen=set(), current_source=None)


def _effective_manifest_inner(
    root: Path,
    payload: dict[str, object],
    *,
    allow_local: bool,
    seen: set[str],
    current_source: ManifestSource | None,
) -> EffectiveManifest:
    parents = _manifest_parents(payload)
    effective: dict[str, object] = {}
    layers: list[dict[str, object]] = []
    field_provenance: dict[str, dict[str, object]] = {}
    for parent in parents:
        if not allow_local and _classify_remote(parent) == "local":
            raise ValueError(f"Local parent manifest {parent!r} requires --allow-local.")
        source = _resolve_manifest(root, parent)
        key = str(source.path)
        if key in seen:
            raise ValueError(f"Manifest cascade cycle detected at {source.path}.")
        seen.add(key)
        parent_payload = _read_manifest(source.path)
        parent_effective = _effective_manifest_inner(
            root,
            parent_payload,
            allow_local=allow_local,
            seen=seen,
            current_source=source,
        )
        effective = _merge_manifest(effective, parent_effective.payload)
        layers.extend(parent_effective.layers)
        field_provenance.update(parent_effective.field_provenance)
    layer = _layer_summary(payload, current_source)
    effective = _merge_manifest(effective, payload)
    for field, value in _flatten_manifest(payload).items():
        field_provenance[field] = {
            "layer": layer.get("team", "unknown"),
            "source": layer.get("source", "local"),
            "source_ref": layer.get("source_ref", ""),
            "value": _manifest_path_value(effective, field, value),
        }
    layers.append(layer)
    return EffectiveManifest(effective, layers, field_provenance)


def _manifest_parents(payload: dict[str, object]) -> list[str]:
    value = payload.get("extends") or payload.get("parent")
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        remote = value.get("manifest") or value.get("remote") or value.get("path")
        return [str(remote)] if remote else []
    if isinstance(value, list):
        parents: list[str] = []
        for item in value:
            if isinstance(item, str):
                parents.append(item)
            elif isinstance(item, dict):
                remote = item.get("manifest") or item.get("remote") or item.get("path")
                if remote:
                    parents.append(str(remote))
        return parents
    return []


def _merge_manifest(parent: dict[str, object], child: dict[str, object]) -> dict[str, object]:
    merged = dict(parent)
    for key, value in child.items():
        if key in {"extends", "parent", "_sync_source"}:
            continue
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_dict(existing, value, root_parent=parent, path=key)
        else:
            merged[key] = value
    return merged


def _merge_dict(
    parent: dict[str, object],
    child: dict[str, object],
    *,
    root_parent: dict[str, object],
    path: str,
) -> dict[str, object]:
    merged = dict(parent)
    for key, value in child.items():
        field_path = f"{path}.{key}"
        existing = merged.get(key)
        if field_path in UNION_FIELDS and isinstance(existing, list) and isinstance(value, list):
            merged[key] = _unique_strings([*existing, *value])
        elif field_path in SUBSET_TIGHTEN_FIELDS and isinstance(existing, list) and isinstance(value, list):
            _validate_subset_tighten(field_path, existing, value, root_parent)
            merged[key] = [str(item) for item in value]
        elif field_path in SUPERSET_TIGHTEN_FIELDS and isinstance(existing, list) and isinstance(value, list):
            _validate_superset_tighten(field_path, existing, value, root_parent)
            merged[key] = [str(item) for item in value]
        elif isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_dict(existing, value, root_parent=root_parent, path=field_path)
        else:
            merged[key] = value
    return merged


def _validate_subset_tighten(
    field_path: str,
    parent_values: list[object],
    child_values: list[object],
    root_parent: dict[str, object],
) -> None:
    if _field_relaxed(root_parent, field_path):
        return
    parent_set = set(_string_list(parent_values))
    child_set = set(_string_list(child_values))
    if parent_set and child_set and not child_set.issubset(parent_set):
        extra = ", ".join(sorted(child_set - parent_set))
        raise ValueError(f"Child manifest cannot loosen parent {field_path}: {extra}")


def _validate_superset_tighten(
    field_path: str,
    parent_values: list[object],
    child_values: list[object],
    root_parent: dict[str, object],
) -> None:
    if _field_relaxed(root_parent, field_path):
        return
    parent_set = set(_string_list(parent_values))
    child_set = set(_string_list(child_values))
    if parent_set and child_set and not parent_set.issubset(child_set):
        missing = ", ".join(sorted(parent_set - child_set))
        raise ValueError(f"Child manifest cannot loosen parent {field_path}: missing {missing}")


def _field_relaxed(root_parent: dict[str, object], field_path: str) -> bool:
    if _dict(root_parent.get("inheritable")).get(field_path) == "relax":
        return True
    parts = field_path.split(".")
    if len(parts) < 2:
        return False
    section = _dict(root_parent.get(parts[0]))
    return _dict(section.get("inheritable")).get(".".join(parts[1:])) == "relax"


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _flatten_manifest(payload: dict[str, object], prefix: str = "") -> dict[str, object]:
    fields: dict[str, object] = {}
    for key, value in payload.items():
        if key in {"extends", "parent", "_sync_source", "inheritable"}:
            continue
        field = f"{prefix}.{key}" if prefix else key
        if key == "inheritable":
            continue
        if isinstance(value, dict):
            fields.update(_flatten_manifest(value, field))
        else:
            fields[field] = value
    return fields


def _manifest_path_value(payload: dict[str, object], field: str, fallback: object) -> object:
    current: object = payload
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            return fallback
        current = current[part]
    return current


def _format_field_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _unique_strings(values: list[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _layer_summary(payload: dict[str, object], source: ManifestSource | None) -> dict[str, object]:
    return {
        "team": payload.get("team", "unknown"),
        "manifest_version": payload.get("manifest_version", "legacy"),
        "min_scaffold_version": payload.get("min_scaffold_version", ""),
        "source": source.source if source else "local",
        "source_ref": source.source_ref if source else "",
    }


def _source_ref(path: Path) -> str | None:
    if not path.exists():
        return None
    directory = path if path.is_dir() else path.parent
    completed = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return str(path)


def _valid_semver(value: str) -> bool:
    return re.fullmatch(r"\d+\.\d+\.\d+", value) is not None


def _compare_semver(left: str, right: str) -> int:
    left_parts = _parse_semver(left)
    right_parts = _parse_semver(right)
    return (left_parts > right_parts) - (left_parts < right_parts)


def _parse_semver(value: str) -> tuple[int, int, int]:
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


def _effective_artifact_lines(root: Path) -> list[str]:
    lines: list[str] = []
    for label, local in [
        ("skill", root / ".coding-scaffold" / "skills"),
        ("agent", root / ".opencode" / "agents"),
        ("policy", root / ".coding-scaffold" / "policy"),
    ]:
        if not local.exists():
            continue
        for path in sorted(local.rglob("*.conflict")):
            try:
                relative = path.relative_to(local)
            except ValueError:
                relative = path
            lines.append(f"{label.title()} deviates from team: {relative}")
    return lines


def _read_provenance(root: Path) -> dict[str, object]:
    path = root / ".coding-scaffold" / "team-provenance.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _stale_pulls_from_actions(actions: list[str]) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for action in actions:
        if "git pull failed" not in action:
            continue
        remote = action.split(" for ", 1)[1].split(";", 1)[0] if " for " in action else "unknown"
        error = action.split("git pull failed:", 1)[1].strip() if "git pull failed:" in action else action
        failures.append(
            {
                "remote": remote,
                "error": error,
                "last_seen": datetime.now(UTC).isoformat(),
            }
        )
    return failures


def _merge_stale_pulls(
    existing: object,
    new_failures: list[dict[str, object]],
    *,
    per_remote_limit: int = 10,
) -> list[dict[str, object]]:
    by_remote: dict[str, list[dict[str, object]]] = {}
    if isinstance(existing, list):
        for item in existing:
            if not isinstance(item, dict):
                continue
            remote = str(item.get("remote") or "unknown")
            by_remote.setdefault(remote, []).append(dict(item))
    for failure in new_failures:
        remote = str(failure.get("remote") or "unknown")
        now = str(failure.get("last_seen") or datetime.now(UTC).isoformat())
        error = str(failure.get("error") or "git pull failed")
        previous = by_remote.get(remote, [])
        first_seen = str(previous[0].get("first_seen") or previous[0].get("last_seen") or now) if previous else now
        previous.append(
            {
                "remote": remote,
                "error": error,
                "first_seen": first_seen,
                "last_seen": now,
            }
        )
        by_remote[remote] = previous[-per_remote_limit:]
    merged: list[dict[str, object]] = []
    for remote in sorted(by_remote):
        merged.extend(by_remote[remote][-per_remote_limit:])
    return merged


def _list_recent_stale_pulls(provenance: dict[str, object]) -> list[dict[str, object]]:
    values = provenance.get("stale_pulls")
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def _list_inbound_nominations(provenance: dict[str, object]) -> list[dict[str, object]]:
    values = provenance.get("inbound_nominations")
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def _write_inbound_nomination_metadata(
    root: Path,
    outbox: Path,
    candidates: list[tuple[str, Path, Path]],
    nominated_at: str,
) -> None:
    manifest = root / ".coding-scaffold" / "team-onboarding.json"
    payload = _read_manifest(manifest) if manifest.exists() else {}
    entries = []
    for kind, relative, _path in candidates:
        entries.append(
            {
                "slug": relative.with_suffix("").as_posix(),
                "source_team": str(payload.get("team") or root.name),
                "source_scope": _nomination_source_scope(kind, relative),
                "nominated_at": nominated_at,
                "accepted_at": "",
                "manifest_target": _manifest_target(payload),
                "manifest_ref": "",
                "rationale_ref": "nomination.md",
            }
        )
    metadata = {"inbound_nominations": entries}
    (outbox / "inbound-nominations.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _nomination_source_scope(kind: str, relative: Path) -> str:
    if kind == "knowledge":
        parts = relative.parts
        if parts and parts[0] in {"team", "department", "unit", "company"}:
            return parts[0]
        return "team"
    if kind == "skills":
        return "team"
    if kind == "policy":
        return "policy"
    return kind


def _manifest_target(payload: dict[str, object]) -> str:
    sync_source = _dict(payload.get("_sync_source"))
    if sync_source.get("manifest"):
        return str(sync_source["manifest"])
    knowledge = _dict(payload.get("knowledge"))
    if knowledge.get("remote"):
        return str(knowledge["remote"])
    return ""


def _collect_inbound_nominations(
    root: Path,
    manifest_source: ManifestSource | None,
) -> list[dict[str, object]]:
    nominations: list[dict[str, object]] = []
    for base in [root / SOURCES_SUBDIR, root / ".coding-scaffold" / "policy" / "imported"]:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.name not in {"inbound-nominations.json", "inbound_nominations.json", "nominations.json"}:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            entries = payload if isinstance(payload, list) else _dict(payload).get("inbound_nominations", [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                manifest_ref = entry.get("manifest_ref")
                if not manifest_ref and manifest_source is not None:
                    manifest_ref = manifest_source.source_ref
                normalized = {
                    "slug": str(entry.get("slug", "")),
                    "source_team": str(entry.get("source_team", "")),
                    "source_scope": str(entry.get("source_scope", "")),
                    "accepted_at": str(entry.get("accepted_at") or entry.get("nominated_at", "")),
                    "nominated_at": str(entry.get("nominated_at", "")),
                    "manifest_target": str(entry.get("manifest_target", "")),
                    "rationale_ref": str(entry.get("rationale_ref", "")),
                    "manifest_ref": str(manifest_ref or ""),
                }
                nominations.append(normalized)
    return nominations


def _open_nomination_pr(root: Path, outbox: Path) -> tuple[str | None, str | None]:
    manifest = root / ".coding-scaffold" / "team-onboarding.json"
    if not manifest.exists():
        return None, "team push --open-pr requires a connected team manifest; kept the outbox bundle."
    payload = _read_manifest(manifest)
    sync_source = _dict(payload.get("_sync_source"))
    remote = str(sync_source.get("manifest") or "")
    if not remote:
        return None, "team push --open-pr requires a GitHub manifest source; kept the outbox bundle."
    if "github.com" not in remote.lower():
        return None, "team push --open-pr only supports GitHub manifest remotes; kept the outbox bundle."
    if shutil.which("gh") is None:
        return None, "team push --open-pr requires gh on PATH; kept the outbox bundle."
    branch = f"nomination/{outbox.name}"
    with tempfile.TemporaryDirectory() as temp:
        checkout = Path(temp) / "manifest"
        clone = subprocess.run(
            ["git", "clone", remote, str(checkout)],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if clone.returncode != 0:
            return None, f"Could not clone manifest repo for PR: {clone.stderr.strip()}; kept the outbox bundle."
        checkout_branch = subprocess.run(
            ["git", "-C", str(checkout), "checkout", "-b", branch],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if checkout_branch.returncode != 0:
            return None, f"Could not create nomination branch: {checkout_branch.stderr.strip()}; kept the outbox bundle."
        destination = checkout / "nominations" / outbox.name
        shutil.copytree(outbox, destination)
        subprocess.run(["git", "-C", str(checkout), "add", "nominations"], check=False, timeout=300)
        commit = subprocess.run(
            ["git", "-C", str(checkout), "commit", "-m", f"Nominate team artifacts {outbox.name}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if commit.returncode != 0:
            return None, f"Could not commit nomination bundle: {commit.stderr.strip()}; kept the outbox bundle."
        push = subprocess.run(
            ["git", "-C", str(checkout), "push", "-u", "origin", branch],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if push.returncode != 0:
            return None, f"Could not push nomination branch: {push.stderr.strip()}; kept the outbox bundle."
        body = (outbox / "nomination.md").read_text(encoding="utf-8")
        pr = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                _github_repo_name(remote),
                "--head",
                branch,
                "--draft",
                "--title",
                f"Nominate team artifacts {outbox.name}",
                "--body",
                body,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if pr.returncode != 0:
            return None, f"Could not open nomination PR: {pr.stderr.strip()}; kept the outbox bundle."
        return pr.stdout.strip().splitlines()[-1], None


def _github_repo_name(remote: str) -> str:
    if remote.startswith("git@github.com:"):
        path = remote.split(":", 1)[1]
    else:
        parsed = urlparse(remote)
        path = parsed.path
    return path.strip("/").removesuffix(".git")


def _nomination_candidates(root: Path) -> list[tuple[str, Path, Path]]:
    checks = [
        ("skills", root / ".coding-scaffold" / "skills", root / SOURCES_SUBDIR / "skills"),
        ("knowledge", root / ".coding-scaffold" / "knowledge" / "team", root / SOURCES_SUBDIR / "knowledge"),
        ("policy", root / ".coding-scaffold" / "policy", root / ".coding-scaffold" / "policy" / "imported"),
    ]
    candidates: list[tuple[str, Path, Path]] = []
    for kind, local_base, imported_base in checks:
        if not local_base.exists():
            continue
        for path in sorted(local_base.rglob("*")):
            if not path.is_file() or ".git" in path.parts or path.name.endswith(".conflict"):
                continue
            if imported_base in path.parents:
                continue
            relative = path.relative_to(local_base)
            matches = [
                imported
                for imported in imported_base.rglob(relative.name)
                if imported.is_file() and imported.relative_to(imported_base).name == relative.name
            ] if imported_base.exists() else []
            if not matches or all(not _same_file(path, imported) for imported in matches):
                candidates.append((kind, relative, path))
    return candidates


def _record_nomination(root: Path, outbox: Path, actions: list[str]) -> None:
    path = root / ".coding-scaffold" / "team-provenance.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"team": "unknown", "actions": []}
    nominations = payload.setdefault("nominations", [])
    if isinstance(nominations, list):
        nominations.append(
            {
                "created": datetime.now(UTC).isoformat(),
                "bundle": str(outbox),
                "actions": actions,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
