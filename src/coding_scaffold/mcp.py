"""MCP (Model Context Protocol) policy, scan, snapshot, diff.

The scaffold's role is review, not enforcement. These helpers:

- generate a reviewable team MCP policy (`mcp policy init`)
- inspect known MCP config locations and report a structured finding list (`mcp scan`)
- snapshot the current MCP server set (`mcp snapshot`) so subsequent runs can detect drift
- diff the current state against the last snapshot (`mcp diff`)

No commands are executed. No network calls. Detection is pure config-file reading.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


MCP_POLICY_RELATIVE = Path(".coding-scaffold") / "mcp-policy.json"
MCP_SNAPSHOT_RELATIVE = Path(".coding-scaffold") / "mcp-snapshot.json"

# Config locations searched when scanning a project. Each entry is a path relative to the
# project root and the table/key under which MCP server definitions live.
#
# Codex's `.codex/config.toml` puts servers under `[mcp_servers.<name>]` (snake_case); older
# Codex layouts and some templates use a plain `[mcp]` table. We accept both.
MCP_CONFIG_SOURCES: tuple[tuple[str, str], ...] = (
    ("opencode.json", "mcp"),
    (".claude/settings.json", "mcp"),
    (".claude/settings.local.json", "mcp"),
    (".codex/config.toml", "mcp_servers"),
)

# Capability hints — heuristic, derived from server name or launch command. Each hint is
# (substring, capability_label).
CAPABILITY_HINTS: tuple[tuple[str, str], ...] = (
    ("filesystem", "filesystem"),
    ("fs-mcp", "filesystem"),
    ("file-system", "filesystem"),
    ("shell", "shell"),
    ("bash", "shell"),
    ("exec", "shell"),
    ("browser", "browser"),
    ("puppeteer", "browser"),
    ("playwright", "browser"),
    ("chrome", "browser"),
    ("github", "github"),
    ("gitlab", "gitlab"),
    ("jira", "jira"),
    ("linear", "linear"),
    ("slack", "slack"),
    ("notion", "notion"),
    ("network", "network"),
    ("http", "network"),
    ("fetch", "network"),
    ("postgres", "database"),
    ("sqlite", "database"),
    ("mysql", "database"),
    ("redis", "database"),
)

# Commands that look risky to run unattended in an MCP launcher.
RISKY_COMMAND_TOKENS: tuple[str, ...] = (
    "rm",
    "sudo",
    "curl",
    "wget",
    "bash -c",
    "sh -c",
    "eval",
    "kubectl",
    "docker run --privileged",
)

# Filesystem-path strings that indicate broad access.
BROAD_PATH_TOKENS: tuple[str, ...] = (
    "/",  # bare root, when given as an args entry
    "~",
    "$HOME",
    "/Users",
    "/home",
)


@dataclass(frozen=True)
class McpServer:
    name: str
    source: str  # config-file path that defined it
    kind: str  # "local" or "remote"
    command: str | None  # launch command (local servers)
    args: tuple[str, ...]  # launch args (local servers)
    url: str | None  # endpoint (remote servers)
    package: str | None  # detected npm package name
    package_version: str | None  # detected pin
    capabilities: tuple[str, ...]
    raw: dict[str, object]  # original config block (for snapshot fingerprint)

    @property
    def fingerprint(self) -> str:
        """Stable hash of the server's identifying configuration."""

        payload = json.dumps(
            {
                "name": self.name,
                "source": self.source,
                "kind": self.kind,
                "command": self.command,
                "args": list(self.args),
                "url": self.url,
                "package": self.package,
                "package_version": self.package_version,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "source": self.source,
            "kind": self.kind,
            "command": self.command,
            "args": list(self.args),
            "url": self.url,
            "package": self.package,
            "package_version": self.package_version,
            "capabilities": list(self.capabilities),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class McpFinding:
    severity: str  # "error" | "warning" | "info"
    rule: str
    server: str | None
    source: str | None
    message: str
    suggested_fix: str

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "server": self.server,
            "source": self.source,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True)
class McpReport:
    servers: list[McpServer] = field(default_factory=list)
    findings: list[McpFinding] = field(default_factory=list)
    scanned_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    def to_dict(self) -> dict[str, object]:
        return {
            "servers": [s.to_dict() for s in self.servers],
            "findings": [f.to_dict() for f in self.findings],
            "scanned_sources": list(self.scanned_sources),
            "warnings": list(self.warnings),
            "counts": {
                "servers": len(self.servers),
                "errors": self.error_count,
                "warnings": self.warning_count,
            },
        }


@dataclass(frozen=True)
class McpDiff:
    added: list[McpServer] = field(default_factory=list)
    removed: list[dict[str, object]] = field(default_factory=list)
    changed: list[tuple[McpServer, dict[str, object]]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "added": [s.to_dict() for s in self.added],
            "removed": list(self.removed),
            "changed": [
                {"current": current.to_dict(), "previous": previous}
                for current, previous in self.changed
            ],
            "warnings": list(self.warnings),
            "counts": {
                "added": len(self.added),
                "removed": len(self.removed),
                "changed": len(self.changed),
            },
        }


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


def default_mcp_policy() -> dict[str, object]:
    return {
        "$schema_version": 1,
        "description": (
            "Generated by `coding-scaffold mcp policy init`. Reviewable team policy for MCP "
            "servers. Edit `approved_servers` and `denied_servers` by pull request."
        ),
        "defaults": {
            "remote_servers": "requires_approval",
            "unapproved_servers": "deny",
            "package_pinning_required": True,
        },
        "review_required_capabilities": [
            "filesystem",
            "shell",
            "network",
            "browser",
            "github",
            "gitlab",
            "slack",
            "jira",
            "linear",
            "notion",
            "database",
        ],
        "approved_servers": [],
        "denied_servers": [],
    }


def write_mcp_policy(target: Path, *, force: bool = False) -> dict[str, object]:
    """Write `.coding-scaffold/mcp-policy.json`. Skipped if it already exists unless force=True."""

    root = target.expanduser().resolve()
    path = root / MCP_POLICY_RELATIVE
    if path.exists() and not force:
        return {"path": str(path), "created": False, "skipped": True}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(default_mcp_policy(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"path": str(path), "created": True, "skipped": False}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


def scan_mcp(target: Path) -> McpReport:
    """Inspect every known MCP-config location and report a structured finding list."""

    root = target.expanduser().resolve()
    servers: list[McpServer] = []
    findings: list[McpFinding] = []
    scanned: list[str] = []
    warnings: list[str] = []

    for rel_path, mcp_key in MCP_CONFIG_SOURCES:
        full = root / rel_path
        if not full.exists():
            continue
        scanned.append(rel_path)
        payload = _load_config(full)
        if payload is None:
            warnings.append(f"Could not parse {rel_path}.")
            continue
        if not isinstance(payload, dict):
            continue
        mcp_section = payload.get(mcp_key)
        # `.codex/config.toml` may use the legacy `[mcp]` table instead of `[mcp_servers]`.
        if mcp_section is None and rel_path.endswith(".toml"):
            mcp_section = payload.get("mcp")
        if not isinstance(mcp_section, dict):
            continue
        for server_name, server_config in sorted(mcp_section.items()):
            if not isinstance(server_config, dict):
                continue
            servers.append(_parse_server(server_name, server_config, source=rel_path))

    # Load policy if present so the scanner can flag unapproved servers.
    policy = _load_policy(root)
    approved = {s for s in policy.get("approved_servers", [])} if policy else set()
    denied = {s for s in policy.get("denied_servers", [])} if policy else set()
    review_caps = set(policy.get("review_required_capabilities", [])) if policy else set()
    defaults = policy.get("defaults", {}) if policy else {}
    if not isinstance(defaults, dict):
        defaults = {}
    package_pinning_required = bool(defaults.get("package_pinning_required", False))
    unapproved_posture = str(defaults.get("unapproved_servers", "")).lower()

    for server in servers:
        findings.extend(
            _check_server(
                server,
                approved=approved,
                denied=denied,
                review_caps=review_caps,
                package_pinning_required=package_pinning_required,
                unapproved_posture=unapproved_posture,
                policy_present=policy is not None,
            )
        )

    findings.sort(key=lambda f: (
        {"error": 0, "warning": 1, "info": 2}[f.severity],
        f.source or "",
        f.server or "",
        f.rule,
    ))

    return McpReport(servers=servers, findings=findings, scanned_sources=scanned, warnings=warnings)


def _parse_server(name: str, config: dict[str, object], *, source: str) -> McpServer:
    url_value = config.get("url")
    url = str(url_value) if isinstance(url_value, str) else None
    command = config.get("command")
    raw_args = config.get("args")
    args = tuple(str(a) for a in raw_args) if isinstance(raw_args, list) else ()
    package, version = _detect_package(command, args)

    capabilities_set: set[str] = set()
    fingerprint_haystack = " ".join([
        name.lower(),
        str(command or "").lower(),
        " ".join(args).lower(),
        str(url or "").lower(),
    ])
    for token, label in CAPABILITY_HINTS:
        if token in fingerprint_haystack:
            capabilities_set.add(label)

    kind = "remote" if url else "local"
    return McpServer(
        name=name,
        source=source,
        kind=kind,
        command=str(command) if isinstance(command, str) else None,
        args=args,
        url=url,
        package=package,
        package_version=version,
        capabilities=tuple(sorted(capabilities_set)),
        raw={
            "command": command,
            "args": list(args),
            "url": url,
        },
    )


def _detect_package(command: object, args: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Best-effort detection of an npm/npx package and its pinned version.

    Supports common forms like `npx -y @scope/pkg@1.2.3 ...` and `npx pkg@1.2.3 ...`.
    Returns (package, version) or (None, None) when no package spec is identified.
    """

    if not isinstance(command, str):
        return (None, None)
    if command.split("/")[-1] not in ("npx", "npm"):
        return (None, None)
    # Walk the args until we find the first token that looks like a package spec.
    # We skip leading flags (`-y`, `--yes`, etc.) and any non-package positional tokens.
    candidate: str | None = None
    for arg in args:
        if not arg or arg.startswith("-"):
            continue
        # A package spec either starts with `@` (scoped) or a word char (unscoped).
        if arg[0].isalpha() or arg.startswith("@"):
            candidate = arg
            break
    if not candidate:
        return (None, None)
    # Parse `pkg@version` or `@scope/pkg@version`.
    if candidate.startswith("@"):
        # `@scope/pkg` or `@scope/pkg@version`
        rest = candidate[1:]
        scope, _, pkg_part = rest.partition("/")
        if not pkg_part:
            return (candidate, None)
        pkg_name, _, version = pkg_part.partition("@")
        return (f"@{scope}/{pkg_name}", version or None)
    pkg, _, version = candidate.partition("@")
    return (pkg, version or None)


def _check_server(
    server: McpServer,
    *,
    approved: set[str],
    denied: set[str],
    review_caps: set[str],
    package_pinning_required: bool,
    unapproved_posture: str = "",
    policy_present: bool = False,
) -> list[McpFinding]:
    findings: list[McpFinding] = []

    if server.name in denied:
        findings.append(McpFinding(
            severity="error",
            rule="server-denied-by-policy",
            server=server.name,
            source=server.source,
            message=f"Server {server.name!r} appears in the policy's denied_servers list.",
            suggested_fix="Remove the server from the config or remove the policy entry.",
        ))
        return findings  # No further checks on a denied server.

    if policy_present and server.name not in approved:
        # If the policy's `defaults.unapproved_servers` is `deny` or `requires_approval`, an
        # empty approved list does NOT silently allow every server. Severity tracks the policy
        # posture: `deny` -> error; `requires_approval` -> warning. A permissive default keeps
        # the existing "informational" silence.
        severity = (
            "error" if unapproved_posture == "deny"
            else "warning" if unapproved_posture in ("requires_approval", "requires-approval")
            else None
        )
        if severity is not None:
            posture_label = unapproved_posture or "deny"
            findings.append(McpFinding(
                severity=severity,
                rule="server-not-approved",
                server=server.name,
                source=server.source,
                message=(
                    f"Server {server.name!r} is not in `approved_servers`. Policy default "
                    f"for unapproved servers is {posture_label!r}."
                ),
                suggested_fix=(
                    "Review the server, then add its name to `approved_servers` in "
                    ".coding-scaffold/mcp-policy.json via pull request."
                ),
            ))

    if server.kind == "remote":
        findings.append(McpFinding(
            severity="warning",
            rule="remote-server",
            server=server.name,
            source=server.source,
            message=f"Remote MCP server ({server.url}). Remote servers run untrusted code paths.",
            suggested_fix=(
                "Verify the remote endpoint's owner, network exposure, and authentication "
                "before approving."
            ),
        ))

    if package_pinning_required and server.package and not server.package_version:
        findings.append(McpFinding(
            severity="warning",
            rule="unpinned-package",
            server=server.name,
            source=server.source,
            message=f"Package {server.package!r} is not pinned to a specific version.",
            suggested_fix=(
                f"Pin the version, e.g. `npx -y {server.package}@1.0.0`. Unpinned packages can "
                "silently upgrade between sessions."
            ),
        ))

    risky_caps = sorted(set(server.capabilities) & review_caps)
    if risky_caps:
        findings.append(McpFinding(
            severity="info",
            rule="review-required-capability",
            server=server.name,
            source=server.source,
            message=(
                f"Server declares review-required capabilities: {', '.join(risky_caps)}."
            ),
            suggested_fix=(
                "Confirm the server's data access matches the team's policy and add an owner "
                "to the approved list."
            ),
        ))

    command_blob = " ".join([str(server.command or ""), *server.args]).lower()
    matched_risky = [token for token in RISKY_COMMAND_TOKENS if token in command_blob]
    if matched_risky:
        findings.append(McpFinding(
            severity="warning",
            rule="risky-launcher",
            server=server.name,
            source=server.source,
            message=(
                f"Launcher includes risky tokens: {', '.join(matched_risky)}."
            ),
            suggested_fix=(
                "Prefer a well-known launcher (`npx <pkg>` or a vetted binary). Inline shell "
                "commands hide what the server actually runs."
            ),
        ))

    for arg in server.args:
        if arg in BROAD_PATH_TOKENS:
            findings.append(McpFinding(
                severity="warning",
                rule="broad-filesystem-arg",
                server=server.name,
                source=server.source,
                message=f"Launcher arg {arg!r} grants broad filesystem access.",
                suggested_fix=(
                    "Scope the server to specific project directories instead of the home or "
                    "root filesystem."
                ),
            ))
            break  # one finding per server is enough

    return findings


# ---------------------------------------------------------------------------
# Snapshot + diff
# ---------------------------------------------------------------------------


def snapshot_mcp(target: Path) -> dict[str, object]:
    """Write `.coding-scaffold/mcp-snapshot.json` with the current set of detected servers.

    Always overwrites — the snapshot is a checkpoint, not a template.
    """

    root = target.expanduser().resolve()
    report = scan_mcp(root)
    snapshot = {
        "$schema_version": 1,
        "servers": [s.to_dict() for s in report.servers],
        "scanned_sources": report.scanned_sources,
    }
    path = root / MCP_SNAPSHOT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "path": str(path),
        "servers": len(report.servers),
        "scanned_sources": report.scanned_sources,
    }


def diff_mcp(target: Path) -> McpDiff:
    """Compare the live scan with the saved snapshot, by fingerprint."""

    root = target.expanduser().resolve()
    snapshot_path = root / MCP_SNAPSHOT_RELATIVE
    if not snapshot_path.exists():
        return McpDiff(
            warnings=[
                f"No snapshot at {snapshot_path}. Run `coding-scaffold mcp snapshot` first."
            ],
        )
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return McpDiff(warnings=[f"Could not read snapshot: {exc}"])

    previous_servers = snapshot.get("servers", []) if isinstance(snapshot, dict) else []
    if not isinstance(previous_servers, list):
        previous_servers = []
    previous_by_name = {
        s.get("name"): s for s in previous_servers if isinstance(s, dict) and s.get("name")
    }

    current_report = scan_mcp(root)
    current_by_name = {s.name: s for s in current_report.servers}

    added: list[McpServer] = []
    changed: list[tuple[McpServer, dict[str, object]]] = []
    for name, server in current_by_name.items():
        if name not in previous_by_name:
            added.append(server)
            continue
        previous_fp = previous_by_name[name].get("fingerprint")
        if previous_fp != server.fingerprint:
            changed.append((server, previous_by_name[name]))

    removed = [previous_by_name[name] for name in previous_by_name if name not in current_by_name]

    return McpDiff(added=added, removed=removed, changed=changed)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_policy(root: Path) -> dict[str, object] | None:
    path = root / MCP_POLICY_RELATIVE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _load_config(path: Path) -> dict[str, object] | None:
    """Read a JSON or TOML config file. Returns the parsed mapping or None on any error.

    Dispatches by extension: ``.toml`` -> stdlib ``tomllib``; everything else -> ``json``.
    """

    suffix = path.suffix.lower()
    try:
        if suffix == ".toml":
            with path.open("rb") as fh:
                payload = tomllib.load(fh)
        else:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
