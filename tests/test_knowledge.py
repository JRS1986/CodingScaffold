import json

from coding_scaffold.knowledge import inspect_knowledge_status, write_knowledge_base


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
