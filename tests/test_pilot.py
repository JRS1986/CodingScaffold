"""Coverage for `coding-scaffold pilot` (issue #93).

Pilot is read-only — never writes files, never installs. These tests assert that
invariant and exercise the recipe shape on a fresh repo + happy-path environment
checks (tool present, tool missing, credentials present, credentials missing).
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

import coding_scaffold.pilot as pilot_module
from coding_scaffold.cli import build_parser, main
from coding_scaffold.pilot import (
    SUPPORTED_TOOLS,
    format_pilot_text,
    run_pilot,
)


# ---------------------------------------------------------------------------
# Read-only invariant
# ---------------------------------------------------------------------------


def test_pilot_writes_no_files_under_target(tmp_path: Path) -> None:
    run_pilot(tmp_path, tool="opencode")
    assert list(tmp_path.iterdir()) == []


def test_pilot_does_not_call_install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If pilot ever calls into installers, the import shim below should not be needed.
    Sanity check: monkeypatch a tripwire and assert it never fires."""

    sentinel = {"called": False}

    def tripwire(*args, **kwargs):
        sentinel["called"] = True
        raise AssertionError("pilot must never install anything")

    # The installers module is imported lazily inside the agent paths; patch the
    # standard install entry points to fire the tripwire if pilot ever touches them.
    monkeypatch.setattr(
        "coding_scaffold.installers.install_missing_tools", tripwire, raising=False
    )
    monkeypatch.setattr(
        "coding_scaffold.installers.install_missing_addons", tripwire, raising=False
    )

    run_pilot(tmp_path, tool="opencode")
    assert sentinel["called"] is False


# ---------------------------------------------------------------------------
# Recipe shape on a fresh repo
# ---------------------------------------------------------------------------


def test_pilot_prints_setup_then_pr_template_then_agent(tmp_path: Path) -> None:
    report = run_pilot(tmp_path, tool="opencode")
    assert len(report.steps) == 3
    assert "setup run" in report.steps[0]
    assert "pr-template init" in report.steps[1]
    assert "opencode" in report.steps[2]


def test_pilot_recipe_is_parseable_by_the_cli(tmp_path: Path) -> None:
    report = run_pilot(tmp_path, tool="opencode")
    parser = build_parser()
    # The setup-run step (with its many flags) must round-trip through the parser.
    parser.parse_args(shlex.split(report.steps[0])[1:])
    # Same for pr-template.
    parser.parse_args(shlex.split(report.steps[1])[1:])


def test_pilot_supports_every_known_tool(tmp_path: Path) -> None:
    for tool in SUPPORTED_TOOLS:
        report = run_pilot(tmp_path, tool=tool)
        assert report.tools == [tool]
        assert any(tool in step for step in report.steps)


def test_pilot_rejects_unknown_tool(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        run_pilot(tmp_path, tool="not-a-real-tool")


# ---------------------------------------------------------------------------
# Environment probe
# ---------------------------------------------------------------------------


def _fake_which(present: set[str]):
    def fake(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in present else None

    return fake


def test_environment_ok_when_everything_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        pilot_module.shutil, "which", _fake_which({"git", "ollama", "opencode"})
    )
    report = run_pilot(tmp_path, tool="opencode")
    assert report.environment["git"] is True
    assert report.environment_ok is True


def test_environment_not_ok_when_tool_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pilot_module.shutil, "which", _fake_which({"git", "ollama"}))
    report = run_pilot(tmp_path, tool="opencode")
    assert report.environment_ok is False


def test_environment_not_ok_when_no_creds_and_no_local_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pilot_module.shutil, "which", _fake_which({"git", "opencode"}))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    report = run_pilot(tmp_path, tool="opencode")
    assert report.environment_ok is False
    assert any("credentials" in w.lower() for w in report.warnings)


def test_environment_credentials_in_env_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        pilot_module.shutil, "which", _fake_which({"git", "opencode"})
    )
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    report = run_pilot(tmp_path, tool="opencode")
    assert "OPENAI_API_KEY" in report.environment["credentials_in_env"]


def test_pilot_missing_tool_includes_install_flag_in_recipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pilot_module.shutil, "which", _fake_which({"git", "ollama"}))
    report = run_pilot(tmp_path, tool="opencode")
    assert "--install-tools" in report.steps[0]


# ---------------------------------------------------------------------------
# Text output + CLI surface
# ---------------------------------------------------------------------------


def test_format_pilot_text_includes_numbered_steps(tmp_path: Path) -> None:
    text = format_pilot_text(run_pilot(tmp_path, tool="opencode"))
    assert "1. " in text
    assert "2. " in text
    assert "3. " in text


def test_format_pilot_text_includes_environment_section(tmp_path: Path) -> None:
    text = format_pilot_text(run_pilot(tmp_path, tool="opencode"))
    assert "Environment check" in text


def test_cli_pilot_json_round_trips(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["pilot", "--target", str(tmp_path), "--tool", "claude-code", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tools"] == ["claude-code"]
    assert isinstance(payload["steps"], list)


# ---------------------------------------------------------------------------
# Multi-tool new tests
# ---------------------------------------------------------------------------


def test_pilot_accepts_multi_tool_list(tmp_path: Path) -> None:
    from coding_scaffold.pilot import run_pilot
    report = run_pilot(tmp_path, tools=["codex", "claude-code"])
    assert report.tools == ["codex", "claude-code"]
    # Setup step is shared with the multi-tool flag
    assert any("--tool codex,claude-code" in step for step in report.steps)
    # Exactly one agent step per selected tool — structural guarantee from
    # the plan, not just "some binary name appears somewhere."
    agent_steps = [s for s in report.steps if "/first-session" in s]
    assert len(agent_steps) == 2, (
        f"expected one agent step per tool (2 total), got {len(agent_steps)}: "
        f"{agent_steps}"
    )


def test_pilot_environment_ok_requires_all_tools_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AND across selected tools — if any is missing, environment_ok is False."""
    import coding_scaffold.pilot as pilot_module
    monkeypatch.setattr(
        pilot_module.shutil, "which",
        lambda name: f"/usr/bin/{name}" if name in {"git", "codex", "ollama"} else None,
    )
    from coding_scaffold.pilot import run_pilot
    report = run_pilot(tmp_path, tools=["codex", "claude-code"])
    assert report.environment_ok is False
    per_tool = report.environment["tools"]
    by_name = {entry["name"]: entry["installed"] for entry in per_tool}
    assert by_name["codex"] is True
    assert by_name["claude-code"] is False


def test_pilot_json_emits_tools_list_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json
    from coding_scaffold.cli import main
    rc = main(["pilot", "--target", str(tmp_path), "--tool", "codex", "--tool", "claude-code", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tools"] == ["codex", "claude-code"]
    assert "tool" not in payload, "pilot JSON must not carry singular tool"
    assert "tool" not in payload["environment"], "environment must not carry singular tool"
    assert len(payload["environment"]["tools"]) == 2


def test_pilot_text_multi_tool_has_tools_header_and_shared_setup(tmp_path: Path) -> None:
    from coding_scaffold.pilot import format_pilot_text, run_pilot
    text = format_pilot_text(run_pilot(tmp_path, tools=["codex", "claude-code"]))
    assert "Tools: codex, claude-code" in text
    assert "Run these once" in text
    assert "Then start a session" in text


def test_pilot_single_tool_text_format_unchanged(tmp_path: Path) -> None:
    """Golden: single-tool pilot text is bit-for-bit identical to pre-multi-tool.

    Specifically asserts the exact substrings the spec promised remain stable:
    - singular `Tool:` header (not the multi-tool `Tools:` list)
    - `Run these next (in order):` (not the multi-tool `Run these once`)
    - per-tool `installed: True/False` (Python bool — not the implementer's
      `yes/no` regression that slipped through code review)
    - three numbered steps (not the per-binary tail block)
    """

    from coding_scaffold.pilot import format_pilot_text, run_pilot
    text = format_pilot_text(run_pilot(tmp_path, tool="opencode"))
    # Header is the historic singular `Tool:` line.
    assert "\nTool: opencode\n" in text
    # Multi-tool-specific headers must be absent for single-tool case.
    assert "Tools: " not in text
    assert "Then start a session with whichever tool" not in text
    assert "Run these once" not in text
    # Historic next-step header preserved.
    assert "Run these next (in order):" in text
    # `installed:` line renders Python bool, not the implementer's `yes/no`
    # regression. Either True or False must be present (depending on env).
    assert "installed: True" in text or "installed: False" in text
    assert "installed: yes" not in text and "installed: no" not in text
    # The original three-step numbering must still be present.
    assert "  1. " in text and "  2. " in text and "  3. " in text


def test_pilot_back_compat_tool_kwarg_still_works(tmp_path: Path) -> None:
    """Existing in-process Python callers pass tool= (singular string)."""
    from coding_scaffold.pilot import run_pilot
    report = run_pilot(tmp_path, tool="claude-code")
    assert report.tools == ["claude-code"]


def test_pilot_persona_plus_multi_tool_does_not_mislabel_persona_commands(
    tmp_path: Path,
) -> None:
    """Regression: when persona overrides the recipe with focus commands AND
    the user passes multiple tools, format_pilot_text must NOT slice the
    persona steps into 'shared setup' + 'per-tool agent lines'. The persona
    commands are a flat 3-step recipe; rendering them as a multi-tool layout
    would label scaffold commands as agent invocations — actively wrong.
    Found in code review of Bundle 6.
    """

    from coding_scaffold.pilot import format_pilot_text, run_pilot

    report = run_pilot(tmp_path, tools=["codex", "claude-code"], persona="security")
    text = format_pilot_text(report)
    # Multi-tool agent-tail header must NOT appear when persona overrides the recipe.
    assert "Then start a session with whichever tool" not in text
    # Persona-override commands render under the flat "Run these next" header.
    assert "Run these next (in order):" in text
    # Header still shows both tools (informational).
    assert "Tools: codex, claude-code" in text
