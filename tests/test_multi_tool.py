"""End-to-end coverage for multi-tool intake (spec §9.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import main


def test_setup_run_two_tools_writes_both_adapter_sets(tmp_path: Path) -> None:
    """One setup run with --tool codex --tool claude-code produces both
    AGENTS.md (codex) and CLAUDE.md (claude-code)."""

    rc = main([
        "setup", "run",
        "--target", str(tmp_path),
        "--tool", "codex",
        "--tool", "claude-code",
        "--non-interactive",
    ])
    assert rc == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    # routing.json carries the tools list, not a singular tool.
    routing = json.loads((tmp_path / ".coding-scaffold" / "routing.json").read_text())
    assert routing["tools"] == ["codex", "claude-code"]
    assert "tool" not in routing


def test_tools_adapt_with_comma_separated_tool_writes_both(tmp_path: Path) -> None:
    # Bootstrap routing.json first by running setup with one tool.
    main(["setup", "run", "--target", str(tmp_path), "--tool", "codex", "--non-interactive"])
    # Then `tools adapt` with comma-separated value.
    rc = main([
        "tools", "adapt",
        "--target", str(tmp_path),
        "--tool", "codex,claude-code",
    ])
    assert rc == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()


def test_tools_adapt_is_idempotent_on_rerun(tmp_path: Path) -> None:
    main(["setup", "run", "--target", str(tmp_path), "--tool", "codex,claude-code", "--non-interactive"])
    # Re-running should skip every file (no new writes), report skipped count.
    rc = main(["tools", "adapt", "--target", str(tmp_path), "--tool", "codex,claude-code"])
    assert rc == 0


def test_pilot_json_multi_tool_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main([
        "pilot", "--target", str(tmp_path),
        "--tool", "codex,claude-code", "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tools"] == ["codex", "claude-code"]
    assert "tool" not in payload
    tools_env = payload["environment"]["tools"]
    assert len(tools_env) == 2
    assert {entry["name"] for entry in tools_env} == {"codex", "claude-code"}


def test_both_alias_still_works_with_deprecation_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Reset the once-per-process deprecation latch so this test sees the warning.
    from coding_scaffold.intake import reset_deprecation_state
    reset_deprecation_state()

    rc = main([
        "setup", "run",
        "--target", str(tmp_path),
        "--tool", "both",
        "--non-interactive",
    ])
    assert rc == 0
    err = capsys.readouterr().err
    assert "deprecated" in err.lower()
    assert "0.7.0" in err
    routing = json.loads((tmp_path / ".coding-scaffold" / "routing.json").read_text())
    assert routing["tools"] == ["opencode", "openclaude"]


def test_manual_plus_real_tool_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main([
        "setup", "run",
        "--target", str(tmp_path),
        "--tool", "manual",
        "--tool", "codex",
        "--non-interactive",
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "manual" in err.lower()
    assert "next:" in err
    assert "see:" in err


def test_legacy_project_json_with_singular_tool_still_updates(tmp_path: Path) -> None:
    """A `project.json` written by 0.5.x (with `tool` instead of `tools`)
    must be readable by `setup update`."""

    # Bootstrap modern, then mutate the file back to legacy shape.
    main(["setup", "run", "--target", str(tmp_path), "--tool", "codex", "--non-interactive"])
    project_json = tmp_path / ".coding-scaffold" / "project.json"
    payload = json.loads(project_json.read_text())
    del payload["tools"]
    payload["tool"] = "codex"
    project_json.write_text(json.dumps(payload))
    # setup update should silently back-fill and run.
    rc = main(["setup", "update", "--target", str(tmp_path)])
    assert rc == 0
    # The legacy file was "user-edited" (hash mismatch), so the updater stages
    # the modernised version as project.json.new rather than overwriting.
    # Either the original file was overwritten with `tools`, or a .new sidecar
    # carrying the modernised shape was created.
    new_file = project_json.with_suffix(".json.new")
    if new_file.exists():
        # Staged path: the .new file must carry the canonical `tools` key.
        new_payload = json.loads(new_file.read_text())
    else:
        # Direct overwrite path: original file was updated in place.
        new_payload = json.loads(project_json.read_text())
    assert "tools" in new_payload
    assert new_payload["tools"] == ["codex"]


def test_install_tools_loops_over_every_selected_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: --install-tools must install EVERY tool in --tool, not just
    the first one. The pilot recipe promises this in spec §7.1 line 231."""

    from coding_scaffold import installers
    install_calls: list[str] = []

    class _FakeResult:
        def __init__(self, tool: str) -> None:
            self.tool = tool
            self.status = "installed"
            self.message = "fake"

    def fake_install_missing_tools(selection: str, *, interactive: bool, assume_yes: bool):
        install_calls.append(selection)
        return [_FakeResult(selection)]

    monkeypatch.setattr(installers, "install_missing_tools", fake_install_missing_tools)
    # The CLI imports the symbol directly, so patch the import site too.
    from coding_scaffold import cli as cli_module
    monkeypatch.setattr(cli_module, "install_missing_tools", fake_install_missing_tools)

    rc = main([
        "setup", "run",
        "--target", str(tmp_path),
        "--tool", "codex",
        "--tool", "claude-code",
        "--install-tools",
        "--non-interactive",
    ])
    assert rc == 0
    # Both tools were offered for install — not just codex.
    assert install_calls == ["codex", "claude-code"], (
        f"--install-tools should loop over every selected tool, got {install_calls}"
    )
