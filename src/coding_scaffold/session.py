"""Per-agentic-change session traces.

A session trace is a single Markdown file under `.coding-scaffold/sessions/` that captures the
human-reviewable record of one agent session: task, plan, files inspected/changed, commands run,
test results, risks, follow-ups, and any reusable knowledge.

This module deliberately stays close to plain template generation. Parsing agent transcripts is
out of scope for v1 — `session summarize` only reads the structured fields that the human (or
the agent itself) filled into the template.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from .file_ops import write_text


SESSIONS_DIR = Path(".coding-scaffold") / "sessions"
DEFAULT_SLUG = "agentic-change"

# Timeouts for git subprocess calls. The scaffold never auto-pushes; these are read-or-write
# operations against the local repo only.
_GIT_TIMEOUT = 60


@dataclass(frozen=True)
class SessionInitResult:
    path: Path
    created: bool

    def to_dict(self) -> dict[str, object]:
        return {"path": str(self.path), "created": self.created}


@dataclass(frozen=True)
class SessionSummary:
    """Deterministic summary of a session trace file.

    Counts checkbox state, lists files-changed entries, and surfaces the task line. Does not
    attempt to interpret free-form prose.
    """

    path: str
    task: str | None
    files_inspected: int
    files_changed: int
    commands_run: int
    tests_passed: int | None
    tests_failed: int | None
    follow_ups: int
    risks: int
    knowledge_to_promote: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "task": self.task,
            "files_inspected": self.files_inspected,
            "files_changed": self.files_changed,
            "commands_run": self.commands_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "follow_ups": self.follow_ups,
            "risks": self.risks,
            "knowledge_to_promote": self.knowledge_to_promote,
            "warnings": list(self.warnings),
        }


def init_session(
    target: Path,
    *,
    slug: str | None = None,
    task: str | None = None,
    when: date | None = None,
) -> SessionInitResult:
    """Create a new session-trace Markdown file.

    Files are named `YYYY-MM-DD-<slug>.md`. If a file with that name already exists, a numeric
    suffix is appended (`-2`, `-3`, ...). The original file is never overwritten.
    """

    root = target.expanduser().resolve()
    sessions_dir = root / SESSIONS_DIR
    sessions_dir.mkdir(parents=True, exist_ok=True)

    today = when or datetime.now(UTC).date()
    base_slug = _safe_slug(slug or DEFAULT_SLUG)
    candidate = sessions_dir / f"{today.isoformat()}-{base_slug}.md"
    index = 2
    while candidate.exists():
        candidate = sessions_dir / f"{today.isoformat()}-{base_slug}-{index}.md"
        index += 1

    content = _session_template(task=task, when=today)
    write_text(candidate, content, overwrite=False)
    return SessionInitResult(path=candidate, created=True)


def summarize_session(path: Path) -> SessionSummary:
    """Read a session trace file and return a deterministic summary."""

    full = path.expanduser().resolve()
    warnings: list[str] = []
    try:
        text = full.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return SessionSummary(
            path=str(full),
            task=None,
            files_inspected=0,
            files_changed=0,
            commands_run=0,
            tests_passed=None,
            tests_failed=None,
            follow_ups=0,
            risks=0,
            knowledge_to_promote=0,
            warnings=[f"Could not read session file: {exc}"],
        )

    sections = _split_sections(text)
    task = _extract_task(text)

    tests_passed, tests_failed = _extract_test_results(sections.get("test result", "")
                                                      or sections.get("tests run", ""))

    return SessionSummary(
        path=str(full),
        task=task,
        files_inspected=_count_bullet_lines(sections.get("files inspected", "")),
        files_changed=_count_bullet_lines(sections.get("files changed", "")),
        commands_run=_count_bullet_lines(sections.get("commands run", "")),
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        follow_ups=_count_bullet_lines(sections.get("follow-up recommendations", "")
                                       or sections.get("follow ups", "")),
        risks=_count_bullet_lines(sections.get("risks", "")),
        knowledge_to_promote=_count_bullet_lines(sections.get("reusable knowledge discovered", "")
                                                  or sections.get("knowledge to promote", "")),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


def _session_template(task: str | None, when: date) -> str:
    task_line = task or "<one-line description of the task>"
    return f"""<!--
Session trace generated by `coding-scaffold session init`. Edit this file as you work — or have
the agent edit it. The structured fields below are read by `coding-scaffold session summarize`.

Sections beginning with `##` are parsed by name; bullet-list items under each section are
counted. Free-form prose between sections is preserved.
-->

# Session Trace — {when.isoformat()}

## Task

{task_line}

## Plan

<!-- 2-5 bullets: what the agent intends to do, in order. -->

-

## Files Inspected

<!-- Bulleted list of files the agent read but did not modify. -->

-

## Files Changed

<!-- Bulleted list of files the agent wrote to. Include intent in one line each. -->

-

## Commands Run

<!-- Exact commands, one per bullet. Include exit codes if non-zero. -->

-

## Test Result

<!-- Summarize. Examples:
- Passed: 167
- Failed: 0
- Skipped: 1
-->

- Passed:
- Failed:
- Skipped:

## Risks

<!-- Anything the change touches that a reviewer should look at carefully. -->

-

## Follow-up Recommendations

<!-- Things deliberately not done in this session. -->

-

## Reusable Knowledge Discovered

<!-- If a skill, decision, or wiki page should be promoted from this session, name it here.
Once promoted, link the promoted file from this bullet. -->

-
"""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _safe_slug(slug: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", slug.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-").lower()
    return cleaned or DEFAULT_SLUG


def _split_sections(text: str) -> dict[str, str]:
    """Return a dict from lowercased section heading -> body text."""

    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current_heading is not None:
                sections[current_heading.lower()] = "\n".join(current_lines).strip()
            current_heading = match.group(1)
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections[current_heading.lower()] = "\n".join(current_lines).strip()
    return sections


def _extract_task(text: str) -> str | None:
    sections = _split_sections(text)
    task_body = sections.get("task", "")
    for raw_line in task_body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("<!--") or line.startswith("-->"):
            continue
        if line.startswith("<") and line.endswith(">"):
            # Untouched placeholder like "<one-line description of the task>".
            continue
        return line
    return None


def _count_bullet_lines(section_body: str) -> int:
    count = 0
    in_comment = False
    for raw_line in section_body.splitlines():
        stripped = raw_line.strip()
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            continue
        if stripped.startswith("<!--") and "-->" not in stripped:
            in_comment = True
            continue
        if not stripped.startswith("-"):
            continue
        # Drop the leading "- " and check whether the bullet has any actual content.
        body = stripped.lstrip("-").strip()
        # Skip empty bullets, HTML-comment fragments, and bullet placeholders.
        if not body or body.startswith("<!--") or body.startswith("-->"):
            continue
        count += 1
    return count


def _extract_test_results(section_body: str) -> tuple[int | None, int | None]:
    """Parse `- Passed: N` / `- Failed: N` style lines if present.

    Lines inside HTML comments (`<!-- ... -->`) are skipped so example blocks in the generated
    template don't pollute the result.
    """

    passed: int | None = None
    failed: int | None = None
    in_comment = False
    for raw_line in section_body.splitlines():
        stripped = raw_line.strip()
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            continue
        if stripped.startswith("<!--") and "-->" not in stripped:
            in_comment = True
            continue
        # Single-line comments are simply ignored.
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue
        line = stripped.lstrip("-").strip()
        match = re.match(r"^(passed|failed)\s*:\s*(\d+)\b", line, flags=re.IGNORECASE)
        if not match:
            continue
        value = int(match.group(2))
        if match.group(1).lower() == "passed":
            passed = value
        else:
            failed = value
    return passed, failed


# ---------------------------------------------------------------------------
# Worktree / checkpoint mode (Priority 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionStartResult:
    """Outcome of `session start`."""

    trace_path: Path
    state_path: Path
    branch: str
    start_commit: str
    worktree_path: Path | None
    repo_path: Path
    created: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "trace_path": str(self.trace_path),
            "state_path": str(self.state_path),
            "branch": self.branch,
            "start_commit": self.start_commit,
            "worktree_path": str(self.worktree_path) if self.worktree_path else None,
            "repo_path": str(self.repo_path),
            "created": self.created,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SessionCheckpointResult:
    state_path: Path
    commit: str | None
    message: str
    files_changed: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "state_path": str(self.state_path),
            "commit": self.commit,
            "message": self.message,
            "files_changed": self.files_changed,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SessionDiffResult:
    state_path: Path
    start_commit: str | None
    head_commit: str | None
    files_changed: list[str]
    diff_summary: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "state_path": str(self.state_path),
            "start_commit": self.start_commit,
            "head_commit": self.head_commit,
            "files_changed": list(self.files_changed),
            "diff_summary": self.diff_summary,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SessionRollbackResult:
    state_path: Path
    confirmed: bool
    mode: str  # "preview" | "soft" | "hard"
    start_commit: str | None
    files_at_risk: list[str]
    rolled_back: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "state_path": str(self.state_path),
            "confirmed": self.confirmed,
            "mode": self.mode,
            "start_commit": self.start_commit,
            "files_at_risk": list(self.files_at_risk),
            "rolled_back": self.rolled_back,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SessionStatusResult:
    """Overall picture of an in-progress worktree session."""

    state_path: Path
    branch: str | None
    start_commit: str | None
    head_commit: str | None
    worktree_path: Path | None
    checkpoint_count: int
    files_changed: int
    status: str  # "in-progress" | "rolled-back" | "finished" | "unknown"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "state_path": str(self.state_path),
            "branch": self.branch,
            "start_commit": self.start_commit,
            "head_commit": self.head_commit,
            "worktree_path": str(self.worktree_path) if self.worktree_path else None,
            "checkpoint_count": self.checkpoint_count,
            "files_changed": self.files_changed,
            "status": self.status,
            "warnings": list(self.warnings),
        }


def start_session(
    target: Path,
    *,
    slug: str | None = None,
    task: str | None = None,
    worktree: bool = False,
    when: date | None = None,
) -> SessionStartResult:
    """Begin a reversible agentic session.

    Creates (or guides creation of) a new Git branch. When ``worktree=True`` also creates a
    Git worktree at ``<repo>/../<repo-name>-<slug>`` so the work is physically isolated from
    the main working tree. Writes a session-trace Markdown file plus a sibling state JSON
    file recording the branch name and the commit the session started from.

    Refuses to operate if `git` is not on PATH; refuses to operate if the project is not a
    Git repository.
    """

    root = target.expanduser().resolve()
    warnings: list[str] = []
    if shutil.which("git") is None:
        raise RuntimeError(
            "git is required for `session start`. Install git or use `session init` for a "
            "trace-only workflow."
        )
    if not _is_git_repo(root):
        raise RuntimeError(
            f"{root} is not a Git repository. Run `git init` first or pass --target."
        )

    today = when or datetime.now(UTC).date()
    base_slug = _safe_slug(slug or DEFAULT_SLUG)
    branch = f"agentic/{today.isoformat()}-{base_slug}"
    # Ensure branch is unique by appending a counter if needed.
    branch = _unique_branch(root, branch)

    pre_commit = _git_head_commit(root)

    worktree_path: Path | None = None
    sessions_root = root
    if worktree:
        worktree_path = root.parent / f"{root.name}-{base_slug}-{today.isoformat()}"
        counter = 2
        while worktree_path.exists():
            worktree_path = root.parent / f"{root.name}-{base_slug}-{today.isoformat()}-{counter}"
            counter += 1
        _run_git(root, ["worktree", "add", "-b", branch, str(worktree_path), pre_commit])
        sessions_root = worktree_path
    else:
        _run_git(root, ["checkout", "-b", branch])

    # Write the trace file inside the (possibly new) worktree.
    sessions_dir = sessions_root / SESSIONS_DIR
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Make sure the per-session state file is not tracked by git — it changes on every
    # checkpoint and would otherwise pollute checkpoint commits.
    gitignore = sessions_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*.state.json\n", encoding="utf-8")

    trace_path = sessions_dir / f"{today.isoformat()}-{base_slug}.md"
    counter = 2
    while trace_path.exists():
        trace_path = sessions_dir / f"{today.isoformat()}-{base_slug}-{counter}.md"
        counter += 1
    write_text(trace_path, _session_template(task=task, when=today), overwrite=False)

    # Commit the trace file (and the per-session .gitignore) so the baseline is clean.
    _run_git(sessions_root, ["add", str(trace_path), str(gitignore)])
    _run_git(sessions_root, ["commit", "-m", f"session start: {base_slug}"])
    start_commit = _git_head_commit(sessions_root)

    state_path = trace_path.with_suffix(".state.json")
    state = {
        "$schema_version": 1,
        "branch": branch,
        "start_commit": start_commit,
        "repo_path": str(root),
        "worktree_path": str(worktree_path) if worktree_path else None,
        "trace_path": str(trace_path),
        "checkpoints": [],
        "status": "in-progress",
    }
    state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return SessionStartResult(
        trace_path=trace_path,
        state_path=state_path,
        branch=branch,
        start_commit=start_commit,
        worktree_path=worktree_path,
        repo_path=root,
        created=True,
        warnings=warnings,
    )


def checkpoint_session(
    target: Path,
    *,
    message: str | None = None,
) -> SessionCheckpointResult:
    """Record a checkpoint: `git add -A` + `git commit -m <message>` + update state JSON.

    Resolves the active session from the most recent state file under
    `.coding-scaffold/sessions/`. Skipped (returns warning) when there's nothing to commit.
    """

    root = target.expanduser().resolve()
    state_path = _find_active_state(root)
    if state_path is None:
        raise RuntimeError(
            "No active session state file found under .coding-scaffold/sessions/. Run "
            "`coding-scaffold session start` first."
        )
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    work_root = _resolve_work_root(state, root)

    # Stage all changes within the worktree/repo, then commit.
    files_changed = _git_status_files(work_root)
    if not files_changed:
        return SessionCheckpointResult(
            state_path=state_path,
            commit=None,
            message=message or "",
            files_changed=0,
            warnings=["No changes to checkpoint."],
        )
    _run_git(work_root, ["add", "-A"])
    commit_message = message or f"checkpoint: {datetime.now(UTC).isoformat(timespec='seconds')}"
    _run_git(work_root, ["commit", "-m", commit_message])
    commit_sha = _git_head_commit(work_root)

    checkpoints = state.get("checkpoints", [])
    if not isinstance(checkpoints, list):
        checkpoints = []
    checkpoints.append({
        "commit": commit_sha,
        "message": commit_message,
        "when": datetime.now(UTC).isoformat(timespec="seconds"),
        "files_changed": len(files_changed),
    })
    state["checkpoints"] = checkpoints
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return SessionCheckpointResult(
        state_path=state_path,
        commit=commit_sha,
        message=commit_message,
        files_changed=len(files_changed),
    )


def diff_session(target: Path) -> SessionDiffResult:
    """Show the diff between the session's start commit and the current HEAD."""

    root = target.expanduser().resolve()
    state_path = _find_active_state(root)
    if state_path is None:
        raise RuntimeError("No active session state file found.")
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    work_root = _resolve_work_root(state, root)
    start_commit = state.get("start_commit")
    head_commit = _git_head_commit(work_root)
    files = _git_diff_files(work_root, start_commit or "HEAD")
    summary = _git_diff_stat(work_root, start_commit or "HEAD")
    return SessionDiffResult(
        state_path=state_path,
        start_commit=start_commit,
        head_commit=head_commit,
        files_changed=files,
        diff_summary=summary,
    )


def rollback_session(
    target: Path,
    *,
    confirm: bool = False,
    hard: bool = False,
) -> SessionRollbackResult:
    """Restore the session's working tree to its start commit.

    Two modes:
    - Without ``confirm``: preview only. Lists the files that would be touched and exits.
    - With ``confirm`` and not ``hard``: soft reset (``git reset --soft <start_commit>``).
      Preserves your changes as staged so nothing is lost.
    - With ``confirm`` and ``hard``: hard reset (``git reset --hard <start_commit>``).
      Discards uncommitted changes. Both flags are required to opt into destructive behavior.
    """

    root = target.expanduser().resolve()
    state_path = _find_active_state(root)
    if state_path is None:
        raise RuntimeError("No active session state file found.")
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    work_root = _resolve_work_root(state, root)
    start_commit = state.get("start_commit")
    if not start_commit:
        raise RuntimeError("Session state has no start_commit recorded.")

    files = _git_diff_files(work_root, start_commit)
    if not confirm:
        return SessionRollbackResult(
            state_path=state_path,
            confirmed=False,
            mode="preview",
            start_commit=start_commit,
            files_at_risk=files,
            rolled_back=False,
            warnings=[
                "Preview only. Re-run with --confirm to soft-reset (preserves uncommitted "
                "changes as staged). Add --hard to discard them."
            ],
        )

    if hard:
        _run_git(work_root, ["reset", "--hard", start_commit])
        mode = "hard"
    else:
        _run_git(work_root, ["reset", "--soft", start_commit])
        mode = "soft"

    state["status"] = "rolled-back"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return SessionRollbackResult(
        state_path=state_path,
        confirmed=True,
        mode=mode,
        start_commit=start_commit,
        files_at_risk=files,
        rolled_back=True,
    )


def status_session(target: Path) -> SessionStatusResult:
    """Overall picture of the active session — branch, baseline, checkpoints, diff size."""

    root = target.expanduser().resolve()
    state_path = _find_active_state(root)
    if state_path is None:
        return SessionStatusResult(
            state_path=root / SESSIONS_DIR,
            branch=None,
            start_commit=None,
            head_commit=None,
            worktree_path=None,
            checkpoint_count=0,
            files_changed=0,
            status="unknown",
            warnings=["No active session state file found."],
        )
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    work_root = _resolve_work_root(state, root)
    start_commit = state.get("start_commit")
    head_commit = None
    files_changed = 0
    warnings: list[str] = []
    try:
        head_commit = _git_head_commit(work_root)
        if start_commit:
            files_changed = len(_git_diff_files(work_root, start_commit))
    except RuntimeError as exc:
        warnings.append(str(exc))
    worktree_str = state.get("worktree_path")
    return SessionStatusResult(
        state_path=state_path,
        branch=state.get("branch"),
        start_commit=start_commit,
        head_commit=head_commit,
        worktree_path=Path(worktree_str) if worktree_str else None,
        checkpoint_count=len(state.get("checkpoints", [])),
        files_changed=files_changed,
        status=state.get("status", "in-progress"),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Git helpers (small, locally scoped)
# ---------------------------------------------------------------------------


def _is_git_repo(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _git_head_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git rev-parse failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _run_git(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _git_status_files(root: Path) -> list[str]:
    """Return the list of files with uncommitted changes (porcelain output)."""

    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if result.returncode != 0:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        # Porcelain format: "XY filename"; first three chars are status, rest is path.
        files.append(line[3:].strip())
    return files


def _git_diff_files(root: Path, base: str) -> list[str]:
    """Files changed between ``base`` and the working tree, including untracked files."""

    tracked = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", base],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    untracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    files: set[str] = set()
    if tracked.returncode == 0:
        for line in tracked.stdout.splitlines():
            if line.strip():
                files.add(line.strip())
    if untracked.returncode == 0:
        for line in untracked.stdout.splitlines():
            if line.strip():
                files.add(line.strip())
    return sorted(files)


def _git_diff_stat(root: Path, base: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--stat", base],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.rstrip()


def _unique_branch(root: Path, branch: str) -> str:
    candidate = branch
    counter = 2
    while _branch_exists(root, candidate):
        candidate = f"{branch}-{counter}"
        counter += 1
    return candidate


def _branch_exists(root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    return result.returncode == 0


def _find_active_state(root: Path) -> Path | None:
    """Find the most recent in-progress state file under .coding-scaffold/sessions/.

    Search order: the current --target's sessions dir first, then any sibling worktree
    directory that's referenced by a recorded state file.
    """

    sessions_dir = root / SESSIONS_DIR
    candidates: list[Path] = []
    if sessions_dir.exists():
        candidates.extend(sessions_dir.glob("*.state.json"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    # Prefer in-progress states.
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("status") == "in-progress":
            return path
    # Fall back to the most recent one regardless of status.
    return candidates[0]


def _resolve_work_root(state: dict[str, object], default: Path) -> Path:
    """Pick the directory git commands should run in: the worktree if any, else the repo."""

    worktree = state.get("worktree_path")
    if isinstance(worktree, str) and worktree:
        candidate = Path(worktree).expanduser()
        if candidate.exists():
            return candidate
    repo = state.get("repo_path")
    if isinstance(repo, str) and repo:
        candidate = Path(repo).expanduser()
        if candidate.exists():
            return candidate
    return default
