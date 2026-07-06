from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_answers_why_use_scaffold_before_quick_start() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    why_index = text.index("## Why Use This If Agents Already Install In One Command?")
    start_index = text.index("## 30-Second Start")
    assert why_index < start_index
    assert "Adaptive project setup" in text
    assert "A shared knowledge base" in text
    assert "A repeatable team workflow" in text


def test_readme_tool_adapters_section_stays_slim() -> None:
    """The wiki compatibility matrix is the single source of truth; the README keeps
    only the short support-depth summary table and a link. Guard against the README
    re-growing a second full matrix or per-tool setup walkthroughs."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    # The full capability matrix lives only in docs/docs/wiki/Tool-Adapters.md.
    assert "| Capability |" not in text

    section = text.split("## Coding Tool Adapters", 1)[1].split("\n## ", 1)[0]
    assert section.count("| Tool | Support depth |") == 1
    assert "docs/docs/wiki/Tool-Adapters.md#compatibility-matrix" in section
    # Per-tool command walkthroughs belong in the wiki, not the README section.
    assert "tools adapt" not in section
    assert len(section.splitlines()) < 40


def test_docs_do_not_claim_raw_chat_ingestion_as_team_wiki() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    faq = (ROOT / "docs" / "docs" / "wiki" / "FAQ.md").read_text(encoding="utf-8")
    knowledge = (ROOT / "docs" / "docs" / "wiki" / "Knowledge-Base.md").read_text(
        encoding="utf-8"
    )

    combined = "\n".join([readme, faq, knowledge])
    assert "not raw chat" in combined
    assert "reviewable distilled proposals" in combined
    assert "knowledge nudge" in combined.lower()
    assert "CodingScaffold does not call a model itself" in combined
    for verb in ("summarize", "redact", "deduplicate"):
        assert verb in combined
