"""Per-agentic-change session traces.

A session trace is a single Markdown file under `.coding-scaffold/sessions/` that captures the
human-reviewable record of one agent session: task, plan, files inspected/changed, commands run,
test results, risks, follow-ups, and any reusable knowledge.

This module deliberately stays close to plain template generation. Parsing agent transcripts is
out of scope for v1 — `session summarize` only reads the structured fields that the human (or
the agent itself) filled into the template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from .file_ops import write_text


SESSIONS_DIR = Path(".coding-scaffold") / "sessions"
DEFAULT_SLUG = "agentic-change"


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
