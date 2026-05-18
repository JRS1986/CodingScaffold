from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.session import (
    checkpoint_session,
    diff_session,
    rollback_session,
    start_session,
    status_session,
)


_GIT_AVAILABLE = shutil.which("git") is not None


def _run(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def _init_repo(tmp_path: Path) -> Path:
    _run(tmp_path, "init", "-b", "main")
    _run(tmp_path, "config", "user.email", "test@example.com")
    _run(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _run(tmp_path, "add", "-A")
    _run(tmp_path, "commit", "-m", "initial")
    return tmp_path


pytestmark = pytest.mark.skipif(not _GIT_AVAILABLE, reason="git not on PATH")


def test_start_session_creates_branch_trace_and_state(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    result = start_session(tmp_path, slug="demo", task="Refactor X")
    assert result.created
    assert result.trace_path.exists()
    assert result.state_path.exists()
    # State JSON is well-formed and references the start commit.
    state = json.loads(result.state_path.read_text(encoding="utf-8"))
    assert state["start_commit"] == result.start_commit
    assert state["branch"] == result.branch
    assert state["status"] == "in-progress"
    # We're on the new branch.
    head_branch = _run(tmp_path, "rev-parse", "--abbrev-ref", "HEAD").strip()
    assert head_branch == result.branch
    # Worktree was not requested.
    assert result.worktree_path is None


def test_start_session_with_worktree_creates_sibling_dir(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    result = start_session(repo, slug="hotfix", worktree=True)
    assert result.worktree_path is not None
    assert result.worktree_path.exists()
    # Trace file lives inside the worktree.
    assert result.trace_path.is_relative_to(result.worktree_path)


def test_start_session_refuses_non_repo(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not a Git repository"):
        start_session(tmp_path)


def test_checkpoint_records_commit(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    start = start_session(tmp_path, slug="demo")
    # Make a change.
    (tmp_path / "new-file.txt").write_text("hi", encoding="utf-8")
    result = checkpoint_session(tmp_path, message="add new-file")
    assert result.commit is not None
    assert result.files_changed >= 1
    # State JSON was updated.
    state = json.loads(start.state_path.read_text(encoding="utf-8"))
    assert len(state["checkpoints"]) == 1
    assert state["checkpoints"][0]["commit"] == result.commit


def test_checkpoint_with_no_changes_warns(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    result = checkpoint_session(tmp_path)
    assert result.commit is None
    assert result.warnings
    assert "no changes" in result.warnings[0].lower()


def test_diff_reports_files_after_change(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    (tmp_path / "new.txt").write_text("hello", encoding="utf-8")
    result = diff_session(tmp_path)
    assert "new.txt" in result.files_changed


def test_rollback_preview_does_not_modify(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    (tmp_path / "new.txt").write_text("hello", encoding="utf-8")
    # Commit so it's part of HEAD vs start.
    checkpoint_session(tmp_path, message="add")
    result = rollback_session(tmp_path)
    assert result.confirmed is False
    assert result.mode == "preview"
    assert result.rolled_back is False
    # File still exists.
    assert (tmp_path / "new.txt").exists()


def test_rollback_soft_preserves_changes_unstaged(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    (tmp_path / "new.txt").write_text("hello", encoding="utf-8")
    checkpoint_session(tmp_path, message="add")
    result = rollback_session(tmp_path, confirm=True, hard=False)
    assert result.rolled_back is True
    assert result.mode == "soft"
    # File still exists on disk (soft reset preserves the working tree).
    assert (tmp_path / "new.txt").exists()


def test_rollback_hard_resets(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    (tmp_path / "new.txt").write_text("hello", encoding="utf-8")
    checkpoint_session(tmp_path, message="add")
    rollback_session(tmp_path, confirm=True, hard=True)
    # Hard reset blows the change away.
    assert not (tmp_path / "new.txt").exists()


def test_status_after_start_reports_in_progress(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    result = status_session(tmp_path)
    assert result.status == "in-progress"
    assert result.branch is not None


def test_cli_session_start_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _init_repo(tmp_path)
    rc = main(["session", "start", "--target", str(tmp_path), "--slug", "demo", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["created"] is True
    assert "branch" in payload


def test_cli_session_diff_after_checkpoint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    (tmp_path / "x.txt").write_text("hi", encoding="utf-8")
    checkpoint_session(tmp_path, message="add x")
    capsys.readouterr()
    rc = main(["session", "diff", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "x.txt" in captured.out


def test_cli_session_rollback_preview_safe(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _init_repo(tmp_path)
    start_session(tmp_path, slug="demo")
    (tmp_path / "x.txt").write_text("hi", encoding="utf-8")
    checkpoint_session(tmp_path, message="add x")
    capsys.readouterr()
    rc = main(["session", "rollback", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Preview" in captured.out
    assert (tmp_path / "x.txt").exists()
