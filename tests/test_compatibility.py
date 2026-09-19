from __future__ import annotations

import json
import socket
import subprocess
import tomllib
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from coding_scaffold.adapters import write_tool_adapter
from coding_scaffold.cli import main
from coding_scaffold.compatibility import COMPATIBILITY_RELATIVE, check_compatibility
from coding_scaffold.doctor import run_doctor
from coding_scaffold.eval_harness import run_eval
from coding_scaffold.hooks import write_hooks
from coding_scaffold.mcp import scan_mcp
from coding_scaffold.updater import refresh_scaffold


FIXTURES = Path(__file__).parent / "fixtures/compatibility"
TODAY = date(2026, 9, 19)


def test_generated_native_contracts_against_reviewed_fixtures(tmp_path):
    expected = json.loads((FIXTURES / "native-contract.json").read_text())
    write_tool_adapter(tmp_path, ["codex", "claude-code", "opencode"])
    assert tomllib.loads((tmp_path / ".codex/config.toml").read_text()) == expected["codex"]
    assert json.loads((tmp_path / ".claude/settings.json").read_text()) == expected["claude-code"]
    assert json.loads((tmp_path / "opencode.json").read_text()) == expected["opencode"]
    assert check_compatibility(tmp_path, today=TODAY).findings == []
    write_hooks(tmp_path, ["codex", "claude-code"])
    for relative in (".codex/hooks.json", ".claude/settings.json"):
        hooks = json.loads((tmp_path / relative).read_text())["hooks"]
        assert set(hooks) == {"SessionStart", "Stop"}
        for event in hooks.values():
            assert event == [{"hooks": [expected["hook"]]}]
    assert check_compatibility(tmp_path, today=TODAY).error_count == 0


def test_standard_claude_mcp_is_scanned_and_gates_eval(tmp_path):
    (tmp_path / ".mcp.json").write_bytes((FIXTURES / "claude-mcp.json").read_bytes())
    report = scan_mcp(tmp_path)
    assert len(report.servers) == 2
    assert {s.kind for s in report.servers} == {"local", "remote"}
    assert report.servers[0].package_version == "1.2.3"
    check = next(
        c for c in run_eval(tmp_path).checks if c.name == "mcp_policy_exists_if_mcp_detected"
    )
    assert not check.passed
    assert check.detail["server_count"] == 2


@pytest.mark.parametrize(
    "content", ["{broken", "[]", '{"mcpServers": []}', '{"mcpServers":{"bad":1}}']
)
def test_malformed_mcp_cannot_pass_readiness_by_skipping(tmp_path, content):
    (tmp_path / ".mcp.json").write_text(content)
    assert scan_mcp(tmp_path).error_count > 0
    assert check_compatibility(tmp_path, today=TODAY).error_count > 0
    check = next(
        c for c in run_eval(tmp_path).checks if c.name == "mcp_policy_exists_if_mcp_detected"
    )
    assert not check.passed


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        (".codex/config.toml", 'approval_mode = "suggest"'),
        (".codex/config.toml", 'approval_policy = "suggest"'),
        (".claude/settings.json", '{"permissions":{"defaultMode":"ask"}}'),
        (".claude/settings.json", '{"permissions":{"deny":["**/.env"]}}'),
        (".claude/settings.json", '{"permissions":[]}'),
        (".codex/hooks.json", '{"hooks":{"Stop":[{"hooks":[{"type":"command"}]}]}}'),
    ],
)
def test_retired_and_invalid_config_is_actionable(tmp_path, relative, content, capsys):
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(content)
    assert main(["tools", "compatibility", "--target", str(tmp_path), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["errors"] > 0


def test_provenance_is_saved_and_overdue_reviews_reported(tmp_path, monkeypatch):
    write_tool_adapter(tmp_path, "codex")
    path = tmp_path / COMPATIBILITY_RELATIVE
    payload = json.loads(path.read_text())
    assert payload["adapters"]["codex"]["source_urls"]
    assert all(
        m["source_url"] and m["upstream_version"] for m in payload["model_catalog"]["models"]
    )
    payload["adapters"]["codex"]["reviewed_at"] = "2020-01-01"
    path.write_text(json.dumps(payload))
    report = check_compatibility(tmp_path, today=TODAY)
    assert report.error_count == 0
    assert any(f.rule == "review-overdue" for f in report.findings)
    monkeypatch.setattr("coding_scaffold.doctor._system_notes", lambda **kwargs: [])
    assert any("2020-01-01" in note for note in run_doctor(tmp_path).notes)
    assert main(["tools", "compatibility", "--target", str(tmp_path), "--strict"]) == 1


def test_invalid_provenance_is_reported_not_crashed(tmp_path):
    path = tmp_path / COMPATIBILITY_RELATIVE
    path.parent.mkdir(parents=True)
    path.write_text('{"schema_version":1,"adapters":[],"model_catalog":null}')
    assert any(f.rule == "invalid-provenance" for f in check_compatibility(tmp_path).findings)


def test_refresh_preserves_edited_provenance_and_enabled_hooks(tmp_path, scaffold_inputs):
    fixture = scaffold_inputs()
    intake = replace(fixture.intake, tools=["codex", "claude-code"])
    args = (tmp_path, intake, fixture.hardware, fixture.providers, fixture.routing)
    refresh_scaffold(*args)
    path = tmp_path / COMPATIBILITY_RELATIVE
    payload = json.loads(path.read_text())
    payload["team_note"] = "Reviewed by platform"
    path.write_text(json.dumps(payload))
    write_hooks(tmp_path, ["codex", "claude-code"])
    before = (tmp_path / ".claude/settings.json").read_bytes()
    result = refresh_scaffold(*args)
    assert json.loads(path.read_text())["team_note"] == "Reviewed by platform"
    assert path.with_name("compatibility.json.new") in result.staged
    assert (tmp_path / ".claude/settings.json").read_bytes() == before
    assert (tmp_path / ".codex/hooks.json").exists()


def test_checks_are_offline_and_read_only(tmp_path, monkeypatch):
    write_tool_adapter(tmp_path, "codex")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline checks cannot open sockets or execute commands")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert check_compatibility(tmp_path, today=TODAY).error_count == 0
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_legacy_project_reports_missing_snapshot(tmp_path):
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/config.toml").write_text('approval_policy = "on-request"')
    report = check_compatibility(tmp_path, today=TODAY)
    assert report.error_count == 0
    assert any(f.rule == "missing-provenance" for f in report.findings)
