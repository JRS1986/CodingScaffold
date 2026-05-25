import json
from datetime import date

from coding_scaffold.knowledge import (
    distill_knowledge,
    inspect_knowledge_status,
    lint_knowledge,
    list_knowledge,
    nominate_knowledge,
    promote_knowledge,
    write_knowledge_base,
)


def test_write_markdown_knowledge_base_creates_linked_files(tmp_path) -> None:
    result = write_knowledge_base(
        tmp_path,
        backend="markdown",
        shared_remote="https://github.com/acme/team-knowledge.git",
        adapter="opencode",
    )

    names = {path.name for path in result.files}
    assert "KNOWLEDGE.md" in names
    assert "knowledge.json" in names
    assert "INDEX.md" in names
    assert "capture-knowledge.md" in names
    config = json.loads((tmp_path / ".coding-scaffold" / "knowledge.json").read_text())
    assert config["backend"] == "markdown"
    assert config["shared_remote"] == "https://github.com/acme/team-knowledge.git"
    assert config["layers"]["company"] == ".coding-scaffold/knowledge/company"
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "decisions" / "0001-decision-template.md").exists()
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "sharing" / "README.md").exists()
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "company" / "README.md").exists()
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "raw" / "meetings" / "README.md").exists()
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "wiki" / "architecture.md").exists()
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "INDEX.md").exists()


def test_write_mempalace_knowledge_base_adds_optional_index_guide(tmp_path) -> None:
    result = write_knowledge_base(tmp_path, backend="mempalace", adapter=None)

    names = {path.name for path in result.files}
    assert "mempalace.md" in names
    assert "capture-knowledge.md" not in names


def test_write_obsidian_knowledge_base_adds_vault_files(tmp_path) -> None:
    result = write_knowledge_base(tmp_path, backend="obsidian", adapter=None)

    names = {path.name for path in result.files}
    assert "00 Start Here.md" in names
    assert "Decision.md" in names
    assert "app.json" in names
    config = json.loads((tmp_path / ".coding-scaffold" / "knowledge.json").read_text())
    assert config["backend"] == "obsidian"
    assert config["obsidian"]["vault_path"] == ".coding-scaffold/knowledge"
    assert (tmp_path / ".coding-scaffold" / "knowledge" / ".obsidian" / "graph.json").exists()


def test_write_foam_knowledge_base_adds_workspace_files(tmp_path) -> None:
    result = write_knowledge_base(tmp_path, backend="foam", adapter=None)

    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    # Foam-specific files were emitted.
    assert (knowledge / "FOAM.md").exists()
    assert (knowledge / ".vscode" / "extensions.json").exists()
    assert (knowledge / ".vscode" / "settings.json").exists()
    assert (knowledge / ".foam" / "templates" / "decision.md").exists()
    assert (knowledge / ".foam" / "templates" / "skill.md").exists()
    assert (knowledge / ".foam" / "templates" / "agent.md").exists()

    # The standard knowledge tree still gets built alongside the Foam workspace.
    assert (knowledge / "INDEX.md").exists()
    assert (knowledge / "wiki" / "architecture.md").exists()
    assert (knowledge / "decisions" / "0001-decision-template.md").exists()

    # Generated VS Code extensions file recommends the Foam extension.
    extensions = json.loads((knowledge / ".vscode" / "extensions.json").read_text())
    assert "foam.foam-vscode" in extensions["recommendations"]

    # knowledge.json records the Foam configuration.
    config = json.loads((tmp_path / ".coding-scaffold" / "knowledge.json").read_text())
    assert config["backend"] == "foam"
    assert config["foam"]["workspace_path"] == ".coding-scaffold/knowledge"
    assert config["foam"]["extension"] == "foam.foam-vscode"

    # Obsidian-specific files are NOT emitted in foam mode.
    names = {path.name for path in result.files}
    assert "00 Start Here.md" not in names
    assert "app.json" not in names


def test_write_knowledge_base_preserves_existing_notes(tmp_path) -> None:
    index = tmp_path / ".coding-scaffold" / "knowledge" / "INDEX.md"
    index.parent.mkdir(parents=True)
    index.write_text("# Human Notes\n", encoding="utf-8")

    result = write_knowledge_base(tmp_path)

    assert index in result.skipped
    assert index.read_text(encoding="utf-8") == "# Human Notes\n"


def test_inspect_knowledge_status_counts_scope_and_maturity(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "testing.md"
    note.write_text(
        "---\nscope: team\nmaturity: validated\n---\n# Testing\n",
        encoding="utf-8",
    )

    status = inspect_knowledge_status(tmp_path)

    assert status.counts["team"]["validated"] == 1


def test_knowledge_status_reports_curated_metadata_warnings(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    page = tmp_path / ".coding-scaffold" / "knowledge" / "wiki" / "testing.md"
    page.write_text("---\nscope: team\nmaturity: draft\n---\n# Testing\n", encoding="utf-8")

    status = inspect_knowledge_status(tmp_path)

    assert status.curated_files >= 1
    assert any("owner" in warning for warning in status.warnings)
    assert any("last_reviewed" in warning for warning in status.warnings)
    assert any("source_refs" in warning for warning in status.warnings)


def test_knowledge_status_reports_stale_curated_pages(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    page = tmp_path / ".coding-scaffold" / "knowledge" / "wiki" / "testing.md"
    page.write_text(
        "---\nscope: team\nmaturity: draft\nowner: qa\nlast_reviewed: 2020-01-01\nsource_refs: []\n---\n# Testing\n",
        encoding="utf-8",
    )

    status = inspect_knowledge_status(tmp_path)

    assert any("more than 180 days" in warning for warning in status.warnings)


def test_distill_knowledge_writes_review_proposal(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    raw = tmp_path / ".coding-scaffold" / "knowledge" / "raw" / "code-notes" / "pytest.md"
    raw.write_text("# Pytest\n\nRun `pytest` before merging.\n", encoding="utf-8")

    result = distill_knowledge(tmp_path, "raw", review=True)

    proposal = tmp_path / ".coding-scaffold" / "knowledge" / "wiki" / "pytest.md.new"
    assert proposal in result.created
    assert proposal.exists()
    assert "raw/code-notes/pytest.md" in proposal.read_text(encoding="utf-8")
    assert not (tmp_path / ".coding-scaffold" / "knowledge" / "wiki" / "pytest.md").exists()


def test_distill_knowledge_reports_missing_source(tmp_path) -> None:
    result = distill_knowledge(tmp_path, "raw", review=True)

    assert result.warnings
    assert not result.created


def test_frontmatter_preserves_colons_in_list_values(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "tagged.md"
    note.write_text(
        '---\nscope: team\nmaturity: draft\ntags: ["a:b", c]\n---\n# Tagged\n',
        encoding="utf-8",
    )

    from coding_scaffold.knowledge import _frontmatter

    parsed, warning = _frontmatter(note)
    assert warning is None
    assert parsed["scope"] == "team"
    assert "a:b" in parsed["tags"]
    assert "c" in parsed["tags"]


def test_frontmatter_preserves_quoted_colon_in_scalar_value(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "owned.md"
    note.write_text(
        '---\nscope: team\nmaturity: draft\nowner: "team:platform"\n---\n# Owned\n',
        encoding="utf-8",
    )

    from coding_scaffold.knowledge import _frontmatter

    parsed, warning = _frontmatter(note)
    assert warning is None
    assert parsed["owner"] == "team:platform"


def test_frontmatter_handles_utf8_bom(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "bom.md"
    note.write_bytes(b"\xef\xbb\xbf---\nscope: team\nmaturity: validated\n---\nbody\n")

    from coding_scaffold.knowledge import _frontmatter

    parsed, warning = _frontmatter(note)
    assert warning is None
    assert parsed["scope"] == "team"
    assert parsed["maturity"] == "validated"


def test_frontmatter_handles_bom_via_status_inspection(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "bom-status.md"
    note.write_bytes(b"\xef\xbb\xbf---\nscope: team\nmaturity: validated\n---\nbody\n")

    status = inspect_knowledge_status(tmp_path)

    assert status.counts["team"]["validated"] >= 1


def test_frontmatter_skips_non_utf8_file_gracefully(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "latin1.md"
    note.write_bytes(b"---\nscope: caf\xe9\n---\nbody\n")

    from coding_scaffold.knowledge import _frontmatter

    parsed, warning = _frontmatter(note)
    assert parsed == {}
    assert warning is not None
    assert "latin1.md" in warning

    # And it must not bubble up through the status check.
    status = inspect_knowledge_status(tmp_path)
    assert any("latin1.md" in w for w in status.warnings)


def test_knowledge_list_filters_scope_and_maturity(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "company" / "security.md"
    note.write_text(
        "---\nscope: company\nmaturity: standard\nowner: sec\nlast_reviewed: "
        f"{date.today().isoformat()}\nsource_refs: []\n---\n# Security\n\nUse approved tools.\n",
        encoding="utf-8",
    )

    entries = list_knowledge(tmp_path, scope="company", maturity="standard")

    assert [entry.path for entry in entries] == [note]


def test_knowledge_lint_reports_layered_notes_missing_scope(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "company" / "security.md"
    note.write_text("---\nmaturity: standard\n---\n# Security\n\nUse approved tools.\n", encoding="utf-8")

    result = lint_knowledge(tmp_path, scope="company")

    assert any(
        violation.code == "missing_frontmatter" and "scope" in violation.message
        for violation in result.violations
    )


def test_knowledge_lint_reports_broken_link_and_orphan(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    (tmp_path / ".coding-scaffold" / "knowledge" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "runbook.md"
    note.write_text(
        "---\nscope: team\nmaturity: draft\nowner: ops\nlast_reviewed: "
        f"{date.today().isoformat()}\nsource_refs: []\n---\n# Runbook\n\nSee [missing](missing.md).\n",
        encoding="utf-8",
    )

    result = lint_knowledge(tmp_path, scope="team")

    codes = {violation.code for violation in result.violations}
    assert "broken_link" in codes
    assert "orphan" in codes


def test_knowledge_promote_moves_raw_note_and_records_audit(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    raw = tmp_path / ".coding-scaffold" / "knowledge" / "raw" / "release.md"
    raw.write_text("# Release\n\nRun checks before release.\n", encoding="utf-8")

    result = promote_knowledge(tmp_path, "release", from_layer="raw", to_layer="wiki", owner="platform")

    destination = tmp_path / ".coding-scaffold" / "knowledge" / "wiki" / "release.md"
    assert not result.warnings
    assert destination.exists()
    assert not raw.exists()
    text = destination.read_text(encoding="utf-8")
    assert "owner: platform" in text
    assert "last_reviewed:" in text
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "CHANGELOG.md").exists()
    assert "wiki/release.md" in (tmp_path / ".coding-scaffold" / "knowledge" / "INDEX.md").read_text(
        encoding="utf-8"
    )


def test_knowledge_nominate_writes_reviewable_bundle(tmp_path) -> None:
    write_knowledge_base(tmp_path)
    note = tmp_path / ".coding-scaffold" / "knowledge" / "team" / "debug.md"
    note.write_text(
        "---\nscope: team\nmaturity: validated\nowner: platform\nlast_reviewed: "
        f"{date.today().isoformat()}\nsource_refs: []\n---\n# Debug\n\nUse the debug playbook.\n",
        encoding="utf-8",
    )

    result = nominate_knowledge(tmp_path, "debug", to_scope="company", rationale="Useful broadly.")

    assert not result.warnings
    assert result.destination is not None
    assert (result.destination / "debug.md").exists()
    assert (result.destination / "nomination.md").exists()
