import json

from coding_scaffold.knowledge import write_knowledge_base


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
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "decisions" / "0001-decision-template.md").exists()


def test_write_mempalace_knowledge_base_adds_optional_index_guide(tmp_path) -> None:
    result = write_knowledge_base(tmp_path, backend="mempalace", adapter=None)

    names = {path.name for path in result.files}
    assert "mempalace.md" in names
    assert "capture-knowledge.md" not in names


def test_write_knowledge_base_preserves_existing_notes(tmp_path) -> None:
    index = tmp_path / ".coding-scaffold" / "knowledge" / "INDEX.md"
    index.parent.mkdir(parents=True)
    index.write_text("# Human Notes\n", encoding="utf-8")

    result = write_knowledge_base(tmp_path)

    assert index in result.skipped
    assert index.read_text(encoding="utf-8") == "# Human Notes\n"
