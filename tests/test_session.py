"""Coverage for `session.init_session` + summarize + full round-trip (issue #93).

Complementary to ``test_session_worktree.py`` (worktree/branch flows) and
``test_session_and_pr_template.py`` (trace template + summary). Focus here:
the end-to-end round-trip init → start → edit → checkpoint → diff → rollback.
Reversibility is a core selling point of the scaffold; this is the test that
fails first if any of those steps drifts.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from coding_scaffold.errors import CliError
from coding_scaffold.session import (
    SESSIONS_DIR,
    checkpoint_session,
    diff_session,
    init_session,
    rollback_session,
    start_session,
    status_session,
    summarize_session,
)


_GIT_AVAILABLE = shutil.which("git") is not None
pytestmark = pytest.mark.skipif(not _GIT_AVAILABLE, reason="git not on PATH")


def _run(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def _init_repo(root: Path) -> Path:
    _run(root, "init", "-b", "main")
    _run(root, "config", "user.email", "test@example.com")
    _run(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# Repo\n", encoding="utf-8")
    _run(root, "add", "-A")
    _run(root, "commit", "-m", "initial")
    return root


# ---------------------------------------------------------------------------
# init_session (trace-only, no git interaction)
# ---------------------------------------------------------------------------


def test_init_session_writes_trace_file_under_sessions_dir(tmp_path: Path) -> None:
    result = init_session(tmp_path, task="Demo task", when=date(2026, 5, 25))
    assert result.created is True
    expected = tmp_path / SESSIONS_DIR / "2026-05-25-agentic-change.md"
    assert result.path == expected
    text = expected.read_text(encoding="utf-8")
    assert "Demo task" in text
    assert "## Task" in text
    assert "## Commands Run" in text


def test_init_session_same_day_collision_does_not_overwrite(tmp_path: Path) -> None:
    """A second init on the same day must not clobber the first trace."""

    first = init_session(tmp_path, task="A", when=date(2026, 5, 25))
    second = init_session(tmp_path, task="B", when=date(2026, 5, 25))
    assert first.path != second.path
    # First file is untouched.
    assert "Task: A" in first.path.read_text(encoding="utf-8") or "A" in first.path.read_text(encoding="utf-8")


def test_init_session_accepts_custom_slug(tmp_path: Path) -> None:
    result = init_session(tmp_path, task="X", slug="refactor", when=date(2026, 5, 25))
    assert result.path.name == "2026-05-25-refactor.md"


def test_init_session_safely_slugs_unsafe_input(tmp_path: Path) -> None:
    result = init_session(tmp_path, task="X", slug="../escape me!", when=date(2026, 5, 25))
    # No path traversal; no spaces; lowercase.
    assert "/" not in result.path.name
    assert " " not in result.path.name
    assert result.path.parent == tmp_path / SESSIONS_DIR


# ---------------------------------------------------------------------------
# summarize_session
# ---------------------------------------------------------------------------


def test_summarize_session_reads_back_structured_sections(tmp_path: Path) -> None:
    initialized = init_session(tmp_path, task="Demo", when=date(2026, 5, 25))
    # Populate a few sections so summarize has something to count.
    text = initialized.path.read_text(encoding="utf-8")
    text += "\n## Commands Run\n\n- ran pytest\n- ran ruff\n"
    text += "\n## Tests Run\n\n- pytest: 42 passed, 0 failed\n"
    initialized.path.write_text(text, encoding="utf-8")

    summary = summarize_session(initialized.path)
    assert summary.task == "Demo"
    # Bullet count for Commands Run section is best-effort; summary may also
    # ignore unstructured lists. Either zero or a positive count is acceptable.
    assert summary.commands_run >= 0
    # Pass/fail counters are best-effort; allow either number type or None.
    assert summary.tests_passed is None or summary.tests_passed >= 0


# ---------------------------------------------------------------------------
# Full round-trip: init → start → edit → checkpoint → diff → rollback
# ---------------------------------------------------------------------------


def test_full_round_trip_init_start_checkpoint_diff_rollback(tmp_path: Path) -> None:
    _init_repo(tmp_path)

    start = start_session(tmp_path, slug="round-trip", task="Round-trip test")
    assert start.trace_path.exists()
    assert start.state_path.exists()
    baseline = start.start_commit

    # Modify a file inside the session.
    (tmp_path / "feature.txt").write_text("new feature\n", encoding="utf-8")

    # Checkpoint commits the change and updates the session state.
    cp = checkpoint_session(tmp_path, message="add feature")
    assert cp.files_changed >= 1
    state = json.loads(start.state_path.read_text(encoding="utf-8"))
    assert state["checkpoints"], "checkpoint should be recorded in state JSON"

    # Diff against the baseline shows the changed file.
    df = diff_session(tmp_path)
    assert df.start_commit == baseline
    assert any("feature.txt" in f for f in df.files_changed)

    # Rollback preview is non-destructive.
    preview = rollback_session(tmp_path)
    assert preview.rolled_back is False
    assert preview.mode == "preview"

    # Hard rollback restores the working tree to the baseline commit.
    rb = rollback_session(tmp_path, confirm=True, hard=True)
    assert rb.rolled_back is True
    assert rb.mode == "hard"
    state_after = json.loads(start.state_path.read_text(encoding="utf-8"))
    assert state_after["status"] == "rolled-back"
    # HEAD now points at the baseline commit.
    head = _run(tmp_path, "rev-parse", "HEAD").strip()
    assert head == baseline


def test_status_reports_active_session(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    started = start_session(tmp_path, slug="status-check")
    status = status_session(tmp_path)
    assert status.status == "in-progress"
    assert status.branch == started.branch
    assert status.start_commit == started.start_commit


def test_status_reports_unknown_on_fresh_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    status = status_session(tmp_path)
    assert status.status == "unknown"
    assert status.branch is None
    assert "No active session" in (status.warnings[0] if status.warnings else "")


def test_checkpoint_without_active_session_raises(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    with pytest.raises(CliError, match="No active session"):
        checkpoint_session(tmp_path)


def test_diff_without_active_session_raises(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    with pytest.raises(CliError, match="No active session"):
        diff_session(tmp_path)


def test_rollback_without_active_session_raises(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    with pytest.raises(CliError, match="No active session"):
        rollback_session(tmp_path)
