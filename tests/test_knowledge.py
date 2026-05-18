import json

from coding_scaffold.knowledge import distill_knowledge, inspect_knowledge_status, write_knowledge_base


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
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "index.md").exists()


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
