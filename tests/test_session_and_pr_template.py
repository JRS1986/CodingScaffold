from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.pr_template import PR_TEMPLATE_RELATIVE, write_pr_template
from coding_scaffold.session import init_session, summarize_session


# ---------------------------------------------------------------------------
# session init / summarize
# ---------------------------------------------------------------------------


def test_session_init_writes_template_under_sessions_dir(tmp_path: Path) -> None:
    result = init_session(tmp_path, task="Demo task", when=date(2026, 5, 18))
    assert result.created is True
    expected = tmp_path / ".coding-scaffold" / "sessions" / "2026-05-18-agentic-change.md"
    assert result.path == expected
    contents = expected.read_text(encoding="utf-8")
    assert "Demo task" in contents
    assert "## Task" in contents
    assert "## Commands Run" in contents


def test_session_init_appends_counter_on_collision(tmp_path: Path) -> None:
    first = init_session(tmp_path, when=date(2026, 5, 18))
    second = init_session(tmp_path, when=date(2026, 5, 18))
    third = init_session(tmp_path, when=date(2026, 5, 18))
    assert first.path.name == "2026-05-18-agentic-change.md"
    assert second.path.name == "2026-05-18-agentic-change-2.md"
    assert third.path.name == "2026-05-18-agentic-change-3.md"
    # All three files actually exist and contain different paths.
    assert {first.path, second.path, third.path} == {
        first.path,
        second.path,
        third.path,
    }


def test_session_init_respects_custom_slug(tmp_path: Path) -> None:
    result = init_session(tmp_path, slug="hotfix-Login Bug!", when=date(2026, 5, 18))
    assert result.path.name == "2026-05-18-hotfix-login-bug.md"


def test_session_init_empty_slug_falls_back_to_default(tmp_path: Path) -> None:
    result = init_session(tmp_path, slug="   ", when=date(2026, 5, 18))
    assert result.path.name == "2026-05-18-agentic-change.md"


def test_summarize_unfilled_session_returns_zero_counts(tmp_path: Path) -> None:
    session = init_session(tmp_path, when=date(2026, 5, 18))
    summary = summarize_session(session.path)
    assert summary.task is None
    assert summary.files_inspected == 0
    assert summary.files_changed == 0
    assert summary.commands_run == 0
    assert summary.tests_passed is None
    assert summary.tests_failed is None
    assert summary.risks == 0
    assert summary.follow_ups == 0
    assert summary.knowledge_to_promote == 0
    assert summary.warnings == []


def test_summarize_filled_session_counts_bullets(tmp_path: Path) -> None:
    session = init_session(tmp_path, task="Refactor X", when=date(2026, 5, 18))
    filled = """# Session Trace — 2026-05-18

## Task

Refactor X

## Plan

- Explore current state
- Sketch the change
- Verify

## Files Inspected

- src/foo.py
- src/bar.py

## Files Changed

- src/foo.py: extract helper

## Commands Run

- pytest -q
- ruff check

## Test Result

- Passed: 167
- Failed: 0
- Skipped: 1

## Risks

- Touches the migration path

## Follow-up Recommendations

- Add integration test
- Document the new helper

## Reusable Knowledge Discovered

- Skill: extract-helper-from-fn
"""
    session.path.write_text(filled, encoding="utf-8")
    summary = summarize_session(session.path)
    assert summary.task == "Refactor X"
    assert summary.files_inspected == 2
    assert summary.files_changed == 1
    assert summary.commands_run == 2
    assert summary.tests_passed == 167
    assert summary.tests_failed == 0
    assert summary.risks == 1
    assert summary.follow_ups == 2
    assert summary.knowledge_to_promote == 1


def test_summarize_handles_missing_file(tmp_path: Path) -> None:
    summary = summarize_session(tmp_path / "does-not-exist.md")
    assert summary.warnings != []
    assert summary.files_inspected == 0


def test_cli_session_init_prints_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["session", "init", "--target", str(tmp_path), "--task", "Demo"])
    captured = capsys.readouterr()
    assert rc == 0
    assert ".coding-scaffold/sessions/" in captured.out


def test_cli_session_init_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["session", "init", "--target", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] is True
    assert payload["path"].endswith(".md")


def test_cli_session_summarize_reads_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = init_session(tmp_path, task="Fix Y", when=date(2026, 5, 18))
    rc = main(["session", "summarize", str(session.path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Session:" in captured.out
    assert "Fix Y" in captured.out


def test_cli_session_summarize_missing_file_warns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["session", "summarize", str(tmp_path / "missing.md")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "Warning" in captured.err


# ---------------------------------------------------------------------------
# pr-template init
# ---------------------------------------------------------------------------


def test_write_pr_template_creates_file_first_run(tmp_path: Path) -> None:
    result = write_pr_template(tmp_path)
    expected = tmp_path / PR_TEMPLATE_RELATIVE
    assert expected.exists()
    assert expected in result.files
    assert result.skipped == []
    content = expected.read_text(encoding="utf-8")
    assert "## Agentic coding disclosure" in content
    assert "Agent / tool used" in content


def test_write_pr_template_does_not_overwrite(tmp_path: Path) -> None:
    target = tmp_path / PR_TEMPLATE_RELATIVE
    target.parent.mkdir(parents=True)
    target.write_text("# Custom\n", encoding="utf-8")
    result = write_pr_template(tmp_path)
    assert result.files == []
    assert target in result.skipped
    assert target.read_text(encoding="utf-8") == "# Custom\n"


def test_cli_pr_template_init_writes_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["pr-template", "init", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Wrote" in captured.out
    assert (tmp_path / PR_TEMPLATE_RELATIVE).exists()


def test_cli_pr_template_init_idempotent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["pr-template", "init", "--target", str(tmp_path)])
    capsys.readouterr()
    rc = main(["pr-template", "init", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Skipped" in captured.out


def test_cli_pr_template_init_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["pr-template", "init", "--target", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "files" in payload
    assert len(payload["files"]) == 1
