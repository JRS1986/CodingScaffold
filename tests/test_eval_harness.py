from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.eval_harness import (
    EVAL_CONFIG_RELATIVE,
    EVAL_REPORT_RELATIVE,
    load_eval_report,
    run_eval,
    write_eval_config,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_write_eval_config_first_run(tmp_path: Path) -> None:
    outcome = write_eval_config(tmp_path)
    assert outcome["created"] is True
    assert (tmp_path / EVAL_CONFIG_RELATIVE).exists()


def test_write_eval_config_is_idempotent(tmp_path: Path) -> None:
    write_eval_config(tmp_path)
    outcome = write_eval_config(tmp_path)
    assert outcome["skipped"] is True


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def test_run_eval_against_empty_project_fails_everything_except_skipped(tmp_path: Path) -> None:
    report = run_eval(tmp_path)
    assert report.total_count > 0
    # Empty project: very few checks pass. MCP check should pass-by-skip (no MCP detected).
    mcp_check = next(c for c in report.checks if c.name == "mcp_policy_exists_if_mcp_detected")
    assert mcp_check.passed is True
    # Build/test/lint/policy/agent-instructions/PR-template all fail.
    assert any(not c.passed and c.name == "build_command_detected" for c in report.checks)
    assert any(not c.passed and c.name == "agent_instructions_exist" for c in report.checks)


def test_run_eval_test_signal_fails_without_any_context_files(tmp_path: Path) -> None:
    """Regression: an empty repo previously falsely-passed the test-command check because
    the linter only fires `missing-build-test-commands` when context files exist. The check
    now scans directly for verifier tokens and reports the empty case honestly."""

    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    report = run_eval(tmp_path)
    test_check = next(c for c in report.checks if c.name == "test_command_detected")
    assert test_check.passed is False
    assert "no agent-context files" in test_check.message.lower()


def test_run_eval_test_signal_passes_when_pytest_named_in_agents_md(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "# Agents\n- Run `pytest -q` after every change.\n",
        encoding="utf-8",
    )
    report = run_eval(tmp_path)
    test_check = next(c for c in report.checks if c.name == "test_command_detected")
    assert test_check.passed is True
    assert "pytest" in test_check.message.lower()


def test_run_eval_test_signal_fails_when_context_files_omit_verifier(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    # AGENTS.md exists but doesn't mention any recognizable test command.
    (tmp_path / "AGENTS.md").write_text(
        "# Agents\n- Be helpful.\n- Be precise.\n",
        encoding="utf-8",
    )
    report = run_eval(tmp_path)
    test_check = next(c for c in report.checks if c.name == "test_command_detected")
    assert test_check.passed is False
    assert "none mentioned" in test_check.message.lower()


def test_run_eval_passes_basics_on_well_configured_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "demo"

[tool.ruff]
line-length = 100
""", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "# Agents\n- Run `pytest -q` after each change.\n- Lint with `ruff check`.\n",
        encoding="utf-8",
    )
    # Write the artifacts the eval checks for via their authoring helpers.
    from coding_scaffold.permissions import write_agent_permissions
    from coding_scaffold.pr_template import write_pr_template
    from coding_scaffold.session import init_session

    write_agent_permissions(tmp_path)
    write_pr_template(tmp_path)
    init_session(tmp_path, task="bootstrap")
    # Provide a minimal policy dir so the policy check passes.
    policy_dir = tmp_path / ".coding-scaffold" / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "team.md").write_text("# Team policy\n", encoding="utf-8")

    report = run_eval(tmp_path)

    passing = {c.name for c in report.checks if c.passed}
    expected_passing = {
        "build_command_detected",
        "test_command_detected",
        "lint_command_detected",
        "agent_instructions_exist",
        "policy_exists",
        "denied_files_configured",
        "pr_template_exists",
        "mcp_policy_exists_if_mcp_detected",
        "session_trace_template_exists",
        "context_lint_clean",
    }
    missing = expected_passing - passing
    assert not missing, f"Expected these checks to pass but they didn't: {sorted(missing)}"


def test_run_eval_mcp_check_fails_when_mcp_detected_without_policy(tmp_path: Path) -> None:
    (tmp_path / "opencode.json").write_text(
        '{"mcp": {"x": {"command": "npx", "args": ["-y", "@scope/x@1.0.0"]}}}',
        encoding="utf-8",
    )
    report = run_eval(tmp_path)
    mcp_check = next(c for c in report.checks if c.name == "mcp_policy_exists_if_mcp_detected")
    assert mcp_check.passed is False


def test_run_eval_writes_report_file(tmp_path: Path) -> None:
    run_eval(tmp_path)
    assert (tmp_path / EVAL_REPORT_RELATIVE).exists()


def test_load_eval_report_returns_none_when_no_report(tmp_path: Path) -> None:
    assert load_eval_report(tmp_path) is None


def test_load_eval_report_reads_previous_run(tmp_path: Path) -> None:
    written = run_eval(tmp_path)
    cached = load_eval_report(tmp_path)
    assert cached is not None
    assert cached.total_count == written.total_count


def test_run_eval_score_is_zero_to_one(tmp_path: Path) -> None:
    report = run_eval(tmp_path)
    assert 0.0 <= report.score <= 1.0


def test_run_eval_disabled_check_is_excluded(tmp_path: Path) -> None:
    write_eval_config(tmp_path)
    config_path = tmp_path / EVAL_CONFIG_RELATIVE
    payload = json.loads(config_path.read_text())
    payload["checks"]["build_command_detected"] = False
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    report = run_eval(tmp_path)
    assert all(c.name != "build_command_detected" for c in report.checks)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_eval_init_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["eval", "init", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "eval config" in captured.out.lower()


def test_cli_eval_run_returns_nonzero_when_checks_fail(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["eval", "run", "--target", str(tmp_path)])
    capsys.readouterr()
    # Empty project will fail several checks; expect non-zero.
    assert rc == 1


def test_cli_eval_run_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["eval", "run", "--target", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "checks" in payload
    assert "score" in payload
    assert "passed" in payload


def test_cli_eval_report_cached_requires_existing_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["eval", "report", "--target", str(tmp_path), "--cached"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "cached" in captured.err.lower()


def test_cli_eval_report_cached_works_after_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["eval", "run", "--target", str(tmp_path)])
    capsys.readouterr()
    rc = main(["eval", "report", "--target", str(tmp_path), "--cached"])
    captured = capsys.readouterr()
    # Some checks will fail in an empty project, so rc may be 1.
    assert rc in (0, 1)
    assert "eval report" in captured.out.lower()
