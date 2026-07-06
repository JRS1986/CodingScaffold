from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from coding_scaffold.errors import CliError
from coding_scaffold.cli import main
from coding_scaffold.memory import (
    MEMORY_DIR,
    audit_memory,
    capture_memory,
    expire_memory,
    list_memory_entries,
    promote_memory,
    review_memory,
    write_memory_config,
)


def test_capture_writes_markdown_with_frontmatter(tmp_path: Path) -> None:
    result = capture_memory(
        tmp_path,
        class_="project_fact",
        content="We use uv for Python dependency management.",
        owner="@platform",
        source="pyproject.toml",
    )
    path = result.entry.path
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "class: project_fact" in text
    assert "owner: @platform" in text
    assert "We use uv for Python dependency management." in text


def test_capture_refuses_secret_class(tmp_path: Path) -> None:
    with pytest.raises(CliError, match="never stored"):
        capture_memory(tmp_path, class_="secret", content="anything")


def test_capture_refuses_personal_data_without_flag(tmp_path: Path) -> None:
    with pytest.raises(CliError, match="restricted"):
        capture_memory(tmp_path, class_="personal_data", content="Jane Doe lives in Berlin.")


def test_capture_accepts_personal_data_with_flag(tmp_path: Path) -> None:
    result = capture_memory(
        tmp_path,
        class_="personal_data",
        content="Jane Doe owns this service.",
        allow_personal=True,
        owner="@me",
    )
    assert result.entry.class_ == "personal_data"


def test_capture_refuses_content_that_looks_like_secret(tmp_path: Path) -> None:
    # Token-shaped string matches the heuristic.
    with pytest.raises(CliError, match="looks like a secret"):
        capture_memory(
            tmp_path,
            class_="project_fact",
            content="API token: ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAA1234",
            owner="@me",
        )


def test_session_lesson_gets_default_expiry(tmp_path: Path) -> None:
    result = capture_memory(
        tmp_path,
        class_="session_lesson",
        content="Yarn doesn't work here; use npm.",
        owner="@me",
    )
    assert result.entry.expires is not None


def test_review_lists_entries_and_flags_unowned(tmp_path: Path) -> None:
    capture_memory(tmp_path, class_="project_fact", content="Owned fact.", owner="@me")
    capture_memory(tmp_path, class_="project_fact", content="Unowned fact.", owner=None)
    report = review_memory(tmp_path)
    assert len(report.entries) == 2
    assert len(report.flagged["unowned"]) == 1


def test_review_flags_expired_entries(tmp_path: Path) -> None:
    past = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    capture_memory(
        tmp_path,
        class_="session_lesson",
        content="Old lesson.",
        owner="@me",
        expires=past,
    )
    report = review_memory(tmp_path)
    assert len(report.flagged["expired"]) == 1


def test_promote_creates_new_entry_and_marks_source(tmp_path: Path) -> None:
    captured = capture_memory(
        tmp_path,
        class_="session_lesson",
        content="Use --allow-local for file:// remotes.",
        owner="@me",
    )
    result = promote_memory(
        tmp_path,
        entry_id=captured.entry.id,
        new_class="team_preference",
        new_owner="@platform",
    )
    assert result.new_entry is not None
    assert result.new_entry.class_ == "team_preference"
    # Source file is updated with status: promoted.
    text = captured.entry.path.read_text(encoding="utf-8")
    assert "status: promoted" in text


def test_promote_refuses_secret_class(tmp_path: Path) -> None:
    captured = capture_memory(
        tmp_path,
        class_="project_fact",
        content="Note about config.",
        owner="@me",
    )
    with pytest.raises(CliError, match="Cannot promote"):
        promote_memory(tmp_path, entry_id=captured.entry.id, new_class="secret")


def test_expire_moves_past_entries_into_expired_dir(tmp_path: Path) -> None:
    past = (datetime.now(UTC).date() - timedelta(days=2)).isoformat()
    captured = capture_memory(
        tmp_path,
        class_="session_lesson",
        content="A stale lesson.",
        owner="@me",
        expires=past,
    )
    result = expire_memory(tmp_path)
    assert captured.entry.id in result.expired_entries
    # Original file is gone.
    assert not captured.entry.path.exists()
    # Moved into _expired/.
    moved_path = Path(result.moved_to[captured.entry.id])
    assert moved_path.exists()
    assert "_expired" in str(moved_path)


def test_audit_flags_secret_in_existing_entry(tmp_path: Path) -> None:
    # Bypass capture (which would refuse) by writing a raw entry that has the secret in body.
    memory_dir = tmp_path / MEMORY_DIR / "project_fact"
    memory_dir.mkdir(parents=True)
    rogue = memory_dir / "2026-05-18-rogue.md"
    rogue.write_text("""---
id: 2026-05-18-rogue
class: project_fact
owner: @me
created: 2026-05-18
expires:
source:
status: active
---

We accidentally pasted ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAA1234 here.
""", encoding="utf-8")
    report = audit_memory(tmp_path)
    secret_findings = [f for f in report.findings if f.rule == "looks-like-secret"]
    assert secret_findings, "Expected at least one looks-like-secret finding."
    assert secret_findings[0].severity == "error"


def test_audit_flags_pii_as_warning(tmp_path: Path) -> None:
    memory_dir = tmp_path / MEMORY_DIR / "project_fact"
    memory_dir.mkdir(parents=True)
    rogue = memory_dir / "2026-05-18-contact.md"
    rogue.write_text("""---
id: 2026-05-18-contact
class: project_fact
owner: @me
created: 2026-05-18
expires:
source:
status: active
---

The owner emails jane.doe@example.com on rotation.
""", encoding="utf-8")
    report = audit_memory(tmp_path)
    pii = [f for f in report.findings if f.rule == "looks-like-pii"]
    assert pii
    assert pii[0].severity == "warning"


def test_list_entries_returns_empty_for_no_memory_dir(tmp_path: Path) -> None:
    assert list_memory_entries(tmp_path) == []


def test_write_memory_config_creates_file(tmp_path: Path) -> None:
    outcome = write_memory_config(tmp_path)
    assert outcome["created"] is True


def test_write_memory_config_is_idempotent(tmp_path: Path) -> None:
    write_memory_config(tmp_path)
    outcome = write_memory_config(tmp_path)
    assert outcome["skipped"] is True


def test_cli_memory_capture_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main([
        "memory", "capture",
        "--target", str(tmp_path),
        "--class", "project_fact",
        "--content", "We pin uv for reproducibility.",
        "--owner", "@me",
        "--json",
    ])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["created"] is True
    assert payload["entry"]["class"] == "project_fact"


def test_cli_memory_capture_refuses_secret(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main([
        "memory", "capture",
        "--target", str(tmp_path),
        "--class", "secret",
        "--content", "x",
    ])
    assert rc == 1
    assert "never stored" in capsys.readouterr().err.lower()


def test_cli_memory_review_runs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    capture_memory(tmp_path, class_="project_fact", content="Fact.", owner="@me")
    capsys.readouterr()
    rc = main(["memory", "review", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "memory review" in captured.out.lower()


def test_cli_memory_audit_returns_nonzero_on_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    memory_dir = tmp_path / MEMORY_DIR / "project_fact"
    memory_dir.mkdir(parents=True)
    rogue = memory_dir / "2026-05-18-rogue.md"
    rogue.write_text("""---
id: 2026-05-18-rogue
class: project_fact
owner: @me
created: 2026-05-18
status: active
---

Pasted ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAA1234.
""", encoding="utf-8")
    rc = main(["memory", "audit", "--target", str(tmp_path)])
    capsys.readouterr()
    assert rc == 1
