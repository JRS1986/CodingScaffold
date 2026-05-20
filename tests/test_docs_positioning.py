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


def test_docs_do_not_claim_raw_chat_ingestion_as_team_wiki() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    faq = (ROOT / "docs" / "docs" / "wiki" / "FAQ.md").read_text(encoding="utf-8")
    knowledge = (ROOT / "docs" / "docs" / "wiki" / "Knowledge-Base.md").read_text(
        encoding="utf-8"
    )

    combined = "\n".join([readme, faq, knowledge])
    assert "not raw chat" in combined
    assert "reviewable distilled proposals" in combined
    for verb in ("summarize", "redact", "deduplicate"):
        assert verb in combined
