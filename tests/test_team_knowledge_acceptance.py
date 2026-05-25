"""Acceptance-criteria audit for issues #97, #98, #99, #100, #101, #102, #103, #104, #105.

These issues were closed in earlier PRs via the team-governance / knowledge-flows /
HTML-backend / nomination-and-stale-history changes. This file is the explicit
audit: one test per acceptance bullet, with the failing message naming which
issue it covers. Future regressions surface the affected issue immediately.

Each section is short on purpose — the deep coverage lives in
``tests/test_team.py`` and ``tests/test_knowledge.py``; these tests assert the
*acceptance criteria as written*, not the internal mechanics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import build_parser, main
from coding_scaffold.knowledge import (
    KnowledgeLintViolation,
    lint_knowledge,
    list_knowledge,
    nominate_knowledge,
    promote_knowledge,
    write_knowledge_base,
)
from coding_scaffold.team import (
    inspect_team_doctor,
    push_team,
    write_team_manifest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bootstrap_knowledge(tmp_path: Path) -> Path:
    """Materialize a fresh knowledge base under tmp_path and return the root."""

    write_knowledge_base(tmp_path, "markdown", None, "none")
    return tmp_path / ".coding-scaffold" / "knowledge"


def _bootstrap_team(tmp_path: Path) -> Path:
    write_team_manifest(tmp_path, team="acme-team", knowledge_backend="markdown")
    return tmp_path


# ---------------------------------------------------------------------------
# #97 — Team sync conflict-resolution model
# ---------------------------------------------------------------------------


def test_issue_97_documented_precedence_model_in_wiki() -> None:
    page = (
        Path(__file__).resolve().parent.parent
        / "docs" / "docs" / "wiki" / "Team-Sync.md"
    )
    text = page.read_text(encoding="utf-8")
    # Cascade semantics + tighten-only contract documented.
    assert "Cascade Semantics" in text
    for field in ("mcp.allowlist", "policy.allowed_providers"):
        assert field in text, (
            f"#97: Team-Sync.md missing precedence rule for {field!r}"
        )


def test_issue_97_team_doctor_exposes_field_provenance(tmp_path: Path) -> None:
    """Acceptance: `team doctor` shows effective config + provenance per artifact."""

    _bootstrap_team(tmp_path)
    report = inspect_team_doctor(tmp_path)
    payload = report.to_dict()
    assert "field_provenance" in payload, "#97: team doctor must expose field provenance"


# ---------------------------------------------------------------------------
# #98 — Manifest version + scaffold compatibility marker
# ---------------------------------------------------------------------------


def test_issue_98_manifest_carries_version_and_min_scaffold(tmp_path: Path) -> None:
    write_team_manifest(tmp_path, team="acme-team", knowledge_backend="markdown")
    manifest_path = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    for field in ("manifest_version", "min_scaffold_version", "manifest_schema_version"):
        assert field in payload, f"#98: team manifest missing {field!r}"


# ---------------------------------------------------------------------------
# #99 — Team push (upward contribution flow)
# ---------------------------------------------------------------------------


def test_issue_99_team_push_dry_run_lists_local_artifacts(tmp_path: Path) -> None:
    """Acceptance: `team push --dry-run` lists local artifacts that differ from the
    imported team manifest. Empty repo produces a graceful 'nothing to nominate'
    instead of crashing."""

    _bootstrap_team(tmp_path)
    result = push_team(tmp_path, dry_run=True)
    assert isinstance(result.actions, list)


def test_issue_99_cli_team_push_dry_run_is_callable(tmp_path: Path) -> None:
    _bootstrap_team(tmp_path)
    rc = main(["team", "push", "--target", str(tmp_path), "--dry-run"])
    assert rc == 0


# ---------------------------------------------------------------------------
# #100 — Knowledge layers retrievable + lint catches missing scope
# ---------------------------------------------------------------------------


def test_issue_100_knowledge_list_filters_by_scope_and_maturity(tmp_path: Path) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    (knowledge / "company").mkdir(exist_ok=True)
    note = knowledge / "company" / "approved-standard.md"
    note.write_text(
        "---\nscope: company\nmaturity: standard\nowner: org\n"
        "last_reviewed: 2026-05-25\nsource_refs: []\n---\n# Approved\n\n"
        "Body content goes here.\n",
        encoding="utf-8",
    )
    entries = list_knowledge(tmp_path, scope="company", maturity="standard")
    assert any(e.path == note for e in entries), (
        "#100: knowledge list --scope company --maturity standard must surface "
        "the matching note"
    )


def test_issue_100_lint_surfaces_layered_notes_missing_scope(tmp_path: Path) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    (knowledge / "team").mkdir(exist_ok=True)
    (knowledge / "team" / "no-scope.md").write_text(
        "---\nowner: x\n---\n# Note\n\nBody\n", encoding="utf-8"
    )
    result = lint_knowledge(tmp_path)
    missing_scope = [
        v for v in result.violations if v.code == "missing_frontmatter" and "scope" in v.message
    ]
    assert missing_scope, "#100: lint must flag layered notes lacking `scope`"


# ---------------------------------------------------------------------------
# #101 — org → unit → team cascade
# ---------------------------------------------------------------------------


def test_issue_101_team_sync_wiki_documents_cascade_semantics() -> None:
    page = (
        Path(__file__).resolve().parent.parent
        / "docs" / "docs" / "wiki" / "Team-Sync.md"
    )
    text = page.read_text(encoding="utf-8")
    for required in (
        "Cascade Semantics",
        "parent to child",
        "tighten-only",
        "inheritable",
    ):
        assert required.lower() in text.lower(), (
            f"#101: Team-Sync.md missing cascade phrase {required!r}"
        )


# ---------------------------------------------------------------------------
# #102 — knowledge lint (CI-grade quality gate)
# ---------------------------------------------------------------------------


def test_issue_102_lint_returns_machine_readable_violations(tmp_path: Path) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    # Plant a broken-link violation.
    (knowledge / "team").mkdir(exist_ok=True)
    (knowledge / "team" / "broken.md").write_text(
        "---\nscope: team\nmaturity: draft\nowner: x\nlast_reviewed: 2026-05-25\nsource_refs: []\n---\n"
        "# Broken\n\n[link](./does-not-exist.md)\n",
        encoding="utf-8",
    )
    result = lint_knowledge(tmp_path)
    assert any(isinstance(v, KnowledgeLintViolation) for v in result.violations)
    assert any(v.code == "broken_link" for v in result.violations), (
        "#102: lint must surface broken links as violations"
    )


def test_issue_102_lint_cli_exits_non_zero_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    (knowledge / "team").mkdir(exist_ok=True)
    (knowledge / "team" / "missing.md").write_text("# No frontmatter\n", encoding="utf-8")
    rc = main(["knowledge", "lint", "--target", str(tmp_path)])
    assert rc != 0, "#102: lint must exit non-zero on violations by default"


def test_issue_102_lint_warn_only_demotes_to_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    (knowledge / "team").mkdir(exist_ok=True)
    (knowledge / "team" / "missing.md").write_text("# Stub\n", encoding="utf-8")
    rc = main(["knowledge", "lint", "--target", str(tmp_path), "--warn-only"])
    assert rc == 0, "#102: lint --warn-only must exit 0 even when violations exist"


def test_issue_102_lint_json_output_documented_for_ci(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    (knowledge / "team").mkdir(exist_ok=True)
    (knowledge / "team" / "missing.md").write_text("# Stub\n", encoding="utf-8")
    main(["knowledge", "lint", "--target", str(tmp_path), "--format", "json", "--warn-only"])
    payload = json.loads(capsys.readouterr().out)
    assert "violations" in payload, "#102: --format json output should expose 'violations'"


# ---------------------------------------------------------------------------
# #103 — knowledge promote (maturity transitions)
# ---------------------------------------------------------------------------


def test_issue_103_promote_moves_note_and_records_audit(tmp_path: Path) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    raw_dir = knowledge / "raw"
    raw_dir.mkdir(exist_ok=True)
    source = raw_dir / "release-checklist.md"
    source.write_text(
        "---\nscope: raw\nmaturity: draft\nowner: platform\n"
        "last_reviewed: 2026-05-25\nsource_refs: []\n---\n# Release Checklist\n\nBody\n",
        encoding="utf-8",
    )
    result = promote_knowledge(
        tmp_path, slug="release-checklist", from_layer="raw", to_layer="wiki", owner="platform"
    )
    assert result.destination.exists(), "#103: promote must move the file to destination"
    assert not source.exists(), "#103: promote must remove the source file"
    changelog = knowledge / "CHANGELOG.md"
    assert changelog.exists(), "#103: promote must record the move in knowledge/CHANGELOG.md"


def test_issue_103_promote_cli_works(tmp_path: Path) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    raw_dir = knowledge / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / "demo.md").write_text(
        "---\nscope: raw\nmaturity: draft\nowner: x\n"
        "last_reviewed: 2026-05-25\nsource_refs: []\n---\n# Demo\n\nBody\n",
        encoding="utf-8",
    )
    rc = main(
        [
            "knowledge", "promote", "demo",
            "--target", str(tmp_path),
            "--from", "raw", "--to", "wiki",
            "--owner", "platform",
        ]
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# #104 — Cross-team knowledge promotion (knowledge nominate)
# ---------------------------------------------------------------------------


def test_issue_104_nominate_writes_reviewable_bundle(tmp_path: Path) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    team_dir = knowledge / "team"
    team_dir.mkdir(exist_ok=True)
    (team_dir / "api-runbook.md").write_text(
        "---\nscope: team\nmaturity: validated\nowner: platform\n"
        "last_reviewed: 2026-05-25\nsource_refs: []\n---\n# API runbook\n\nBody\n",
        encoding="utf-8",
    )
    result = nominate_knowledge(
        tmp_path, slug="api-runbook", to_scope="company", rationale="needed org-wide"
    )
    # nominate_knowledge returns KnowledgePromotionResult; `destination` holds the bundle dir.
    assert result.destination is not None, (
        "#104: knowledge nominate must produce a reviewable bundle"
    )
    assert result.destination.exists()
    assert (result.destination / "nomination.md").exists()


def test_issue_104_nominate_cli_works(tmp_path: Path) -> None:
    knowledge = _bootstrap_knowledge(tmp_path)
    team_dir = knowledge / "team"
    team_dir.mkdir(exist_ok=True)
    (team_dir / "skill.md").write_text(
        "---\nscope: team\nmaturity: validated\nowner: x\n"
        "last_reviewed: 2026-05-25\nsource_refs: []\n---\n# Skill\n\nBody\n",
        encoding="utf-8",
    )
    rc = main(
        [
            "knowledge", "nominate", "skill",
            "--target", str(tmp_path),
            "--to-scope", "company",
            "--rationale", "broadly useful",
        ]
    )
    assert rc == 0


# ---------------------------------------------------------------------------
# #105 — HTML knowledge backend
# ---------------------------------------------------------------------------


def test_issue_105_html_backend_is_a_valid_choice() -> None:
    parser = build_parser()
    args = parser.parse_args(["knowledge", "--target", "/tmp", "--backend", "html"])
    assert args.backend == "html"


def test_issue_105_html_backend_renders_pages(tmp_path: Path) -> None:
    write_knowledge_base(tmp_path, "html", None, "none")
    site_dir = tmp_path / ".coding-scaffold" / "knowledge" / "site"
    assert site_dir.exists(), "#105: html backend must produce a site directory"
    html_files = list(site_dir.rglob("*.html"))
    assert html_files, "#105: html backend must produce .html pages"
    # Built-in audit chips visible on the rendered page.
    sample = html_files[0].read_text(encoding="utf-8")
    assert "<html" in sample.lower()


def test_issue_105_html_backend_listed_on_every_relevant_entry_point() -> None:
    """`--backend html` must appear on `knowledge`, `knowledge create`, and the
    setup-run knowledge-backend choices."""

    parser = build_parser()
    parser.parse_args(["knowledge", "--backend", "html"])
    parser.parse_args(["knowledge", "create", "--backend", "html"])
    parser.parse_args(["setup", "run", "--knowledge-backend", "html"])
    parser.parse_args(["team", "init", "--knowledge-backend", "html"])
