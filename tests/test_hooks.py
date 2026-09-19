from __future__ import annotations

import io
import json
import socket
import subprocess

import pytest

from coding_scaffold.cli import main
from coding_scaffold.errors import CliError
from coding_scaffold.hooks import HOOK_COMMAND, HOOK_REPORT_RELATIVE, run_hook, write_hooks


def test_hooks_opt_in_merges_without_replacing_user_settings(tmp_path):
    path = tmp_path / ".claude/settings.json"
    path.parent.mkdir()
    user_hook = {"matcher": "startup", "hooks": [{"type": "command", "command": "echo custom"}]}
    settings = {"permissions": {"deny": ["Read(**/.env)"]}, "hooks": {"SessionStart": [user_hook]}}
    path.write_text(json.dumps(settings))
    result = write_hooks(tmp_path, ["claude-code", "codex"])
    saved = json.loads(path.read_text())
    assert saved["permissions"] == settings["permissions"]
    assert saved["hooks"]["SessionStart"][0] == user_hook
    before = path.read_bytes()
    assert len(result["files"]) == 2
    assert write_hooks(tmp_path, ["claude-code", "codex"])["files"] == []
    assert path.read_bytes() == before


def test_existing_customized_handler_is_preserved(tmp_path):
    write_hooks(tmp_path, ["codex"])
    path = tmp_path / ".codex/hooks.json"
    payload = json.loads(path.read_text())
    payload["hooks"]["Stop"][0]["hooks"][0]["timeout"] = 30
    path.write_text(json.dumps(payload))
    assert write_hooks(tmp_path, ["codex"])["files"] == []
    assert json.loads(path.read_text())["hooks"]["Stop"][0]["hooks"][0]["timeout"] == 30


def test_invalid_existing_config_prevents_partial_install(tmp_path):
    (tmp_path / ".claude").mkdir()
    path = tmp_path / ".claude/settings.json"
    path.write_text("{bad")
    with pytest.raises(CliError, match="Cannot merge"):
        write_hooks(tmp_path, ["codex", "claude-code"])
    assert not (tmp_path / ".codex/hooks.json").exists()
    assert path.read_text() == "{bad"


def test_hook_runs_do_not_execute_commands_or_store_sensitive_payload(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Hooks must not execute commands or open sockets")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    payload = {
        "hook_event_name": "SessionStart",
        "cwd": str(tmp_path),
        "last_assistant_message": "SECRET_CHAT",
        "tool_input": {"command": "SECRET_COMMAND"},
    }
    assert run_hook(payload)["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert list(tmp_path.iterdir()) == []
    payload["hook_event_name"] = "Stop"
    assert run_hook(payload) == {}
    report = (tmp_path / HOOK_REPORT_RELATIVE).read_text()
    assert "SECRET" not in report
    assert json.loads(report)["project_tests_run"] is False


def test_stop_errors_continue_once_and_report_remains_failed(tmp_path):
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/config.toml").write_text('approval_mode = "suggest"')
    payload = {"hook_event_name": "Stop", "cwd": str(tmp_path)}
    assert run_hook(payload)["decision"] == "block"
    result = run_hook({**payload, "stop_hook_active": True})
    assert "decision" not in result
    assert "limited to one" in result["systemMessage"]
    report = json.loads((tmp_path / HOOK_REPORT_RELATIVE).read_text())
    assert report["checks"]["compatibility_errors"] == 1


def test_hook_uses_worktree_root_from_nested_cwd(tmp_path):
    (tmp_path / ".git").write_text("gitdir: /not-read")
    nested = tmp_path / "src/nested"
    nested.mkdir(parents=True)
    run_hook({"hook_event_name": "Stop", "cwd": str(nested)})
    assert (tmp_path / HOOK_REPORT_RELATIVE).exists()
    assert not (nested / ".coding-scaffold").exists()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"hook_event_name": "Stop", "cwd": "."},
        {"hook_event_name": "PostToolUse", "cwd": "/"},
    ],
)
def test_invalid_event_payload_is_rejected(payload):
    with pytest.raises(CliError):
        run_hook(payload)


def test_hook_cli_outputs_only_native_json(tmp_path, monkeypatch, capsys):
    assert main(["tools", "hooks", "--target", str(tmp_path), "--tool", "codex", "--json"]) == 0
    assert HOOK_COMMAND in (tmp_path / ".codex/hooks.json").read_text()
    capsys.readouterr()
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"hook_event_name": "Stop", "cwd": str(tmp_path)}))
    )
    assert main(["tools", "hook-run"]) == 0
    assert json.loads(capsys.readouterr().out) == {}


@pytest.mark.parametrize(
    "payload",
    [
        {"hook_event_name": []},
        {"hook_event_name": "Stop", "cwd": "/", "stop_hook_active": "false"},
    ],
)
def test_malformed_event_fields_raise_actionable_errors(payload):
    with pytest.raises(CliError):
        run_hook(payload)


def test_oversized_hook_payload_is_rejected_without_echo(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("SECRET" * 180_000))
    assert main(["tools", "hook-run"]) == 1
    assert "SECRET" not in capsys.readouterr().err
