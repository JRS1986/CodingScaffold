from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

import coding_scaffold.pilot as pilot_module
from coding_scaffold.cli import build_parser, main
from coding_scaffold.doctor import run_doctor
from coding_scaffold.pilot import SUPPORTED_TOOLS, run_pilot


# ---------------------------------------------------------------------------
# Top-level help groups
# ---------------------------------------------------------------------------


def test_top_level_help_includes_journey_groups() -> None:
    text = build_parser().format_help()
    assert "START HERE" in text
    assert "10-MINUTE PILOT" in text
    assert "DAILY WORKFLOW" in text
    assert "ADVANCED / GOVERNANCE" in text


def test_top_level_help_lists_canonical_entry_points() -> None:
    text = build_parser().format_help()
    # The three new-user commands are all named explicitly.
    assert "coding-scaffold doctor" in text
    assert "coding-scaffold pilot" in text
    assert "coding-scaffold setup run" in text


def test_top_level_help_still_lists_every_visible_command() -> None:
    # Backwards compatibility: existing commands must still be reachable from --help.
    text = build_parser().format_help()
    for command in (
        "probe", "setup", "credentials", "knowledge", "context", "session", "memory",
        "pr-template", "mcp", "skills", "eval", "permissions", "team", "policy",
        "tools", "doctor", "pilot",
    ):
        assert command in text, f"command {command!r} missing from top-level help"


def test_hidden_aliases_still_parse() -> None:
    # `init` and `wizard` are hidden compat aliases; argparse should still accept them.
    parser = build_parser()
    args = parser.parse_args(["init", "--target", "/tmp"])
    assert args.command == "init"
    args = parser.parse_args(["wizard", "--target", "/tmp"])
    assert args.command == "wizard"


# ---------------------------------------------------------------------------
# doctor as accessibility hub
# ---------------------------------------------------------------------------


def test_doctor_on_empty_repo_recommends_pilot_or_setup(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)
    assert report.artifacts["AGENTS.md"] is False
    assert report.artifacts[".coding-scaffold/"] is False
    # The first recommendation should mention `pilot` so new users land there.
    assert any("pilot" in step for step in report.next_steps)
    assert any("setup run" in step for step in report.next_steps)
    # Advanced surfaces are explicitly named as ignorable.
    assert "policy" in report.ignore_for_now
    assert "mcp" in report.ignore_for_now


def test_doctor_recognizes_scaffolded_repo(tmp_path: Path) -> None:
    # Plant AGENTS.md + PR template so doctor sees a partially-set-up repo.
    (tmp_path / "AGENTS.md").write_text(
        "# Agents\n- Run `pytest -q` after every change.\n", encoding="utf-8"
    )
    pr_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
    pr_dir.mkdir(parents=True)
    (pr_dir / "agentic-change.md").write_text("# Agentic change\n", encoding="utf-8")
    scaffold_dir = tmp_path / ".coding-scaffold"
    scaffold_dir.mkdir()

    report = run_doctor(tmp_path)
    assert report.artifacts["AGENTS.md"] is True
    assert report.artifacts["pr_template"] is True
    assert report.artifacts[".coding-scaffold/"] is True
    # `pilot` is not the first recommendation when basics already exist.
    assert not any(step.startswith("coding-scaffold pilot") for step in report.next_steps)
    # The recommendations should still be 1-3, never empty.
    assert 1 <= len(report.next_steps) <= 3


def test_doctor_recommends_session_when_basics_present(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "# Agents\n- Run `pytest -q`.\n", encoding="utf-8"
    )
    pr_dir = tmp_path / ".github" / "PULL_REQUEST_TEMPLATE"
    pr_dir.mkdir(parents=True)
    (pr_dir / "agentic-change.md").write_text("# Agentic\n", encoding="utf-8")
    report = run_doctor(tmp_path)
    assert any("session init" in step for step in report.next_steps)


def test_doctor_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["doctor", "--target", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert "artifacts" in payload
    assert "next_steps" in payload
    assert "ignore_for_now" in payload


def test_doctor_cli_text_output_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["doctor", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "CodingScaffold doctor" in captured.out
    assert captured.out.count("CodingScaffold doctor") == 1
    assert "Recommended next steps:" in captured.out
    assert "Ignore for now" in captured.out


def test_doctor_cli_verbose_includes_legacy_snapshot(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["doctor", "--target", str(tmp_path), "--verbose"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.count("CodingScaffold doctor") == 2
    assert "Python package is runnable" in captured.out


# ---------------------------------------------------------------------------
# pilot
# ---------------------------------------------------------------------------


def test_pilot_prints_three_step_recipe(tmp_path: Path) -> None:
    report = run_pilot(tmp_path, tool="opencode")
    # Three numbered steps in the recipe.
    assert len(report.steps) == 3
    setup_step = report.steps[0]
    assert "setup run" in setup_step
    assert "--tool opencode" in setup_step
    assert "--mode beginner" in setup_step
    assert "pr-template init" in report.steps[1]


def test_pilot_does_not_attempt_to_install_anything(tmp_path: Path) -> None:
    # The pilot is read-only: even when the tool is missing, the printed recipe asks the
    # USER to run `setup run --install-tools`. The pilot itself never writes files or installs.
    run_pilot(tmp_path, tool="opencode")
    # No files are written to the target directory.
    assert not list(tmp_path.iterdir())


def test_pilot_missing_tool_recipe_uses_valid_setup_run_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_which(name: str) -> str | None:
        if name in {"git", "ollama"}:
            return f"/usr/bin/{name}"
        return None

    monkeypatch.setattr(pilot_module.shutil, "which", fake_which)

    report = run_pilot(tmp_path, tool="opencode")
    setup_step = report.steps[0]
    assert "--install-tools" in setup_step
    assert "--install " not in f"{setup_step} "
    # Regression guard: the printed recipe should be parseable by the real CLI parser.
    build_parser().parse_args(shlex.split(setup_step)[1:])


def test_pilot_environment_not_ok_when_selected_tool_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_which(name: str) -> str | None:
        if name in {"git", "ollama"}:
            return f"/usr/bin/{name}"
        return None

    monkeypatch.setattr(pilot_module.shutil, "which", fake_which)

    report = run_pilot(tmp_path, tool="opencode")
    assert report.environment["git"] is True
    assert report.environment["local_runtime_cli"] == ["ollama"]
    tool_info = report.environment["tool"]
    assert isinstance(tool_info, dict)
    assert tool_info["installed"] is False
    assert report.environment_ok is False


def test_pilot_rejects_unknown_tool(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        run_pilot(tmp_path, tool="not-a-tool")


def test_pilot_supports_every_known_tool(tmp_path: Path) -> None:
    for tool in SUPPORTED_TOOLS:
        report = run_pilot(tmp_path, tool=tool)
        assert report.tool == tool
        assert any(tool in step for step in report.steps), (
            f"recipe for tool {tool!r} should mention the tool name"
        )


def test_pilot_cli_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["pilot", "--target", str(tmp_path), "--tool", "claude-code", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["tool"] == "claude-code"
    assert "steps" in payload
    assert "ignore_for_now" in payload


def test_pilot_cli_text_output_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["pilot", "--target", str(tmp_path), "--tool", "opencode"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "10-minute happy path" in captured.out
    assert "Run these next" in captured.out


def test_pilot_cli_rejects_unknown_tool_via_argparse(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # argparse's choices= rejects the bad value before the handler runs.
    with pytest.raises(SystemExit):
        main(["pilot", "--target", str(tmp_path), "--tool", "not-a-tool"])
