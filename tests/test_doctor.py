"""Coverage for `coding-scaffold doctor` (issue #93).

Golden output tests on three repo states:
- fresh: no scaffold artifacts at all
- partial: AGENTS.md + .coding-scaffold present
- fully set up: every artifact in the registry exists
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.doctor import (
    ADVANCED_FOR_NOW,
    DoctorReport,
    format_doctor_text,
    run_doctor,
)


# ---------------------------------------------------------------------------
# Fresh repo
# ---------------------------------------------------------------------------


def test_fresh_repo_recommends_pilot_first(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)
    first = report.next_steps[0]
    assert "pilot" in first


def test_fresh_repo_marks_every_artifact_absent(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)
    assert all(not present for present in report.artifacts.values())


def test_fresh_repo_returns_at_most_three_recommendations(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)
    assert 1 <= len(report.next_steps) <= 3


# ---------------------------------------------------------------------------
# Partial repo
# ---------------------------------------------------------------------------


def _seed_partial(root: Path) -> None:
    """AGENTS.md + .coding-scaffold/ present; PR template absent."""

    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / ".coding-scaffold").mkdir()


def test_partial_repo_no_longer_recommends_pilot_first(tmp_path: Path) -> None:
    _seed_partial(tmp_path)
    report = run_doctor(tmp_path)
    assert not any(step.startswith("coding-scaffold pilot") for step in report.next_steps)


def test_partial_repo_recommends_pr_template_when_missing(tmp_path: Path) -> None:
    _seed_partial(tmp_path)
    report = run_doctor(tmp_path)
    assert any("pr-template init" in step for step in report.next_steps)


# ---------------------------------------------------------------------------
# Fully-set-up repo
# ---------------------------------------------------------------------------


def _seed_full(root: Path) -> None:
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    pr_dir = root / ".github" / "PULL_REQUEST_TEMPLATE"
    pr_dir.mkdir(parents=True)
    (pr_dir / "agentic-change.md").write_text("# PR\n", encoding="utf-8")
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir()
    (scaffold / "eval-config.json").write_text("{}", encoding="utf-8")
    (scaffold / "knowledge").mkdir()
    (scaffold / "sessions").mkdir()
    (scaffold / "policy").mkdir()
    (scaffold / "skills").mkdir()
    (scaffold / "memory").mkdir()
    (scaffold / "agent-permissions.json").write_text("{}", encoding="utf-8")
    (scaffold / "mcp-policy.json").write_text("{}", encoding="utf-8")


def test_fully_set_up_repo_recommends_session_or_eval(tmp_path: Path) -> None:
    _seed_full(tmp_path)
    report = run_doctor(tmp_path)
    assert any(
        ("session init" in step) or ("eval run" in step) for step in report.next_steps
    )


def test_fully_set_up_repo_does_not_recommend_setup_run(tmp_path: Path) -> None:
    _seed_full(tmp_path)
    report = run_doctor(tmp_path)
    assert not any("setup run" in step for step in report.next_steps), (
        f"unexpected setup-run recommendation: {report.next_steps}"
    )


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------


def test_format_doctor_text_is_deterministic(tmp_path: Path) -> None:
    """Same inputs -> same string. Required for golden snapshot tests."""

    report = run_doctor(tmp_path)
    assert format_doctor_text(report) == format_doctor_text(report)


def test_format_doctor_text_uses_x_and_blank_marks(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("x", encoding="utf-8")
    text = format_doctor_text(run_doctor(tmp_path))
    assert "[x] AGENTS.md" in text
    assert "[ ] CLAUDE.md" in text


def test_format_doctor_text_includes_ignore_for_now_list(tmp_path: Path) -> None:
    text = format_doctor_text(run_doctor(tmp_path))
    for advanced in ADVANCED_FOR_NOW:
        assert advanced in text


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_cli_doctor_json_matches_to_dict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["doctor", "--target", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    direct = run_doctor(tmp_path).to_dict()
    # The CLI's JSON output is the canonical to_dict shape.
    assert payload == direct


def test_doctor_report_to_dict_is_serializable(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)
    payload = report.to_dict()
    json.dumps(payload)  # must not raise


def test_doctor_report_dataclass_round_trip(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)
    assert isinstance(report, DoctorReport)
    assert isinstance(report.artifacts, dict)
    assert isinstance(report.next_steps, list)
    assert isinstance(report.notes, list)
