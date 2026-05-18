from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.context_lint import (
    DEFAULT_CONTEXT_PATHS,
    LintFinding,
    explain_context,
    lint_context,
)


def _write(target: Path, rel: str, contents: str) -> Path:
    full = target / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(contents, encoding="utf-8")
    return full


def test_lint_returns_no_findings_for_empty_project(tmp_path: Path) -> None:
    report = lint_context(tmp_path)
    assert report.findings == []
    assert report.scanned_files == []
    # Default path list reports every missing file as skipped.
    assert set(report.skipped_files) == set(DEFAULT_CONTEXT_PATHS)


def test_lint_flags_vague_rule_without_verifier(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "AGENTS.md",
        """# Agents
- Always write clean code.
- Run `pytest` after each change.
""",
    )
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    severities = [f.rule for f in report.findings]
    assert "vague-rule" in severities
    # The pytest line is a verifier, so it must NOT itself be flagged as vague.
    vague_lines = [f.line for f in report.findings if f.rule == "vague-rule"]
    assert vague_lines == [2]


def test_lint_does_not_flag_vague_when_same_line_names_verifier(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "AGENTS.md",
        """# Agents
- Keep the test suite clean and green by running `pytest -q` after every change.
""",
    )
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    assert not any(f.rule == "vague-rule" for f in report.findings)


def test_lint_flags_dangerous_recommendations(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "CLAUDE.md",
        """# Claude
- Use `chmod 777` so the agent can write everywhere.
- Push with `git push --force` when stuck.
- Verified with pytest.
""",
    )
    report = lint_context(tmp_path, paths=["CLAUDE.md"])
    rules = sorted(f.rule for f in report.findings)
    assert "dangerous-recommendation" in rules
    # There are two dangerous lines; severity must be error.
    assert all(
        f.severity == "error"
        for f in report.findings
        if f.rule == "dangerous-recommendation"
    )
    assert sum(1 for f in report.findings if f.rule == "dangerous-recommendation") == 2


def test_lint_detects_duplicate_rule_across_files(tmp_path: Path) -> None:
    body = "- Run `pytest` after each change to verify.\n"
    _write(tmp_path, "AGENTS.md", "# A\n" + body)
    _write(tmp_path, "CLAUDE.md", "# B\n" + body)
    report = lint_context(tmp_path, paths=["AGENTS.md", "CLAUDE.md"])
    dup_findings = [f for f in report.findings if f.rule == "duplicate-rule"]
    assert len(dup_findings) == 1
    assert "AGENTS.md" in dup_findings[0].message
    assert "CLAUDE.md" in dup_findings[0].message


def test_lint_detects_contradiction(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "AGENTS.md",
        """# A
- Always run the tests before pushing (use pytest).
- Skip the tests on hotfix branches.
""",
    )
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    contradictions = [f for f in report.findings if f.rule.startswith("contradictory-rule:")]
    assert len(contradictions) == 1
    assert contradictions[0].severity == "error"


def test_lint_flags_missing_build_test_commands_for_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    _write(
        tmp_path,
        "AGENTS.md",
        "# Agents\n- Be helpful and respectful.\n",
    )
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    rules = [f.rule for f in report.findings]
    assert "missing-build-test-commands" in rules


def test_lint_no_missing_command_when_pytest_mentioned(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    _write(tmp_path, "AGENTS.md", "# A\n- Run `pytest -q` after every change.\n")
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    assert not any(f.rule == "missing-build-test-commands" for f in report.findings)


def test_lint_flags_excessive_length(tmp_path: Path) -> None:
    body = "- Run `pytest` to verify.\n" + ("Filler line that adds context budget. " * 600 + "\n")
    _write(tmp_path, "AGENTS.md", body)
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    assert any(f.rule == "excessive-length" for f in report.findings)


def test_lint_flags_tooling_conflict_yarn_vs_npm_lockfile(tmp_path: Path) -> None:
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    _write(
        tmp_path,
        "AGENTS.md",
        "# A\n- Use yarn for everything.\n- Run `npm test` after changes.\n",
    )
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    assert any(f.rule == "tooling-conflict" for f in report.findings)


def test_lint_flags_advanced_concepts_without_basics(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "AGENTS.md",
        "# A\n- Configure your MCP servers and multi-agent orchestration.\n",
    )
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    assert any(f.rule == "beginner-hostile" for f in report.findings)


def test_lint_no_beginner_hostile_when_basics_present(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "AGENTS.md",
        """# A
- Run `pytest` first.
- MCP servers can be configured later, see docs.
""",
    )
    report = lint_context(tmp_path, paths=["AGENTS.md"])
    assert not any(f.rule == "beginner-hostile" for f in report.findings)


def test_lint_findings_are_sorted_deterministically(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "AGENTS.md",
        """# A
- Use `chmod 777` to fix permissions.
- Be professional in commit messages.
- Run `pytest -q` before merging.
""",
    )
    report1 = lint_context(tmp_path, paths=["AGENTS.md"])
    report2 = lint_context(tmp_path, paths=["AGENTS.md"])
    assert [f.to_dict() for f in report1.findings] == [f.to_dict() for f in report2.findings]
    # Errors precede warnings.
    severities = [f.severity for f in report1.findings]
    if "error" in severities and "warning" in severities:
        assert severities.index("error") < severities.index("warning")


def test_explain_context_summarizes_files(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    _write(tmp_path, "AGENTS.md", "# A\n- Run `pytest` to verify.\n- Configure MCP later.\n")
    payload = explain_context(tmp_path, paths=["AGENTS.md"])
    assert payload["project_type"] == "pyproject.toml"
    assert payload["totals"]["files"] == 1
    entry = payload["files"][0]
    assert entry["file"] == "AGENTS.md"
    assert "pytest" in entry["verification_tokens"]
    assert "mcp" in entry["mentions_advanced_concepts"]


def test_cli_context_lint_exits_nonzero_on_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "AGENTS.md", "- Use `chmod 777` everywhere.\n- Verified with pytest.\n")
    rc = main(["context", "lint", "--target", str(tmp_path), "--path", "AGENTS.md"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "ERROR" in captured.out
    assert "chmod 777" in captured.out.lower() or "chmod 777" in captured.err.lower()


def test_cli_context_lint_exits_zero_when_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "AGENTS.md",
        "# A\n- Run `pytest -q` after every change.\n",
    )
    rc = main(["context", "lint", "--target", str(tmp_path), "--path", "AGENTS.md"])
    assert rc == 0


def test_cli_context_lint_json_output_is_machine_readable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path, "AGENTS.md", "- Use `chmod 777`.\n- pytest is run by CI.\n")
    main(["context", "lint", "--target", str(tmp_path), "--path", "AGENTS.md", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "findings" in payload
    assert payload["counts"]["error"] >= 1


def test_cli_context_explain_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "AGENTS.md", "- Run `pytest` to verify.\n")
    rc = main(["context", "explain", "--target", str(tmp_path), "--path", "AGENTS.md"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "AGENTS.md" in captured.out


def test_lint_finding_round_trips_through_dict() -> None:
    finding = LintFinding(
        severity="warning",
        rule="vague-rule",
        file="AGENTS.md",
        line=12,
        message="x",
        suggested_fix="y",
    )
    payload = finding.to_dict()
    assert payload == {
        "severity": "warning",
        "rule": "vague-rule",
        "file": "AGENTS.md",
        "line": 12,
        "message": "x",
        "suggested_fix": "y",
    }


def test_default_paths_constant_includes_canonical_targets() -> None:
    assert "AGENTS.md" in DEFAULT_CONTEXT_PATHS
    assert "CLAUDE.md" in DEFAULT_CONTEXT_PATHS
    assert "llms.txt" in DEFAULT_CONTEXT_PATHS


@pytest.mark.parametrize("when", [date(2026, 5, 18)])
def test_default_lint_is_stable_across_runs(tmp_path: Path, when: date) -> None:
    # Sanity: linting an empty repo twice produces identical reports (no time-based fields).
    _ = when  # parametrize is purely for keeping the test name searchable.
    first = lint_context(tmp_path).to_dict()
    second = lint_context(tmp_path).to_dict()
    assert first == second
