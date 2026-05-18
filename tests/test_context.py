from coding_scaffold.context import compress_context, inspect_context_budget


def test_context_budget_warns_when_knowledge_exceeds_limit(tmp_path) -> None:
    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "large.md").write_text("alpha " * 120, encoding="utf-8")

    budget = inspect_context_budget(tmp_path, max_tokens=10, context_window=100, max_ratio=0.4)

    assert budget.tokens_estimate > 10
    assert budget.warnings
    assert "Compress context" in budget.recommendation


def test_context_budget_can_inspect_team_assets(tmp_path) -> None:
    skills = tmp_path / ".coding-scaffold" / "skills"
    skills.mkdir(parents=True)
    (skills / "review.md").write_text("# Review\nCheck tests.\n", encoding="utf-8")

    budget = inspect_context_budget(tmp_path, source="team")

    assert budget.file_count == 1
    assert budget.files[0].path == ".coding-scaffold/skills/review.md"


def test_compress_team_source_skips_policy_by_default(tmp_path) -> None:
    policy = tmp_path / ".coding-scaffold" / "policy"
    skills = tmp_path / ".coding-scaffold" / "skills"
    policy.mkdir(parents=True)
    skills.mkdir(parents=True)
    (policy / "company.md").write_text(
        "# Policy\n\nPlease note that the exact security policy should stay canonical. " * 10,
        encoding="utf-8",
    )
    (skills / "review.md").write_text(
        "# Review Skill\n\nPlease note that this long reusable skill can be compressed. " * 10,
        encoding="utf-8",
    )

    result = compress_context(tmp_path, source="team")

    assert skills / "review.caveman.md" in result.files
    assert not (policy / "company.caveman.md").exists()


def test_compress_context_writes_sidecars_without_overwriting(tmp_path) -> None:
    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    source = knowledge / "decision.md"
    source.write_text(
        "# Decision\n\n"
        "Please note that in order to optimize the very noisy context, "
        "the team should keep the important numbers 42 and 100000.\n",
        encoding="utf-8",
    )

    result = compress_context(tmp_path)
    second = compress_context(tmp_path)

    sidecar = knowledge / "decision.caveman.md"
    assert result.files == [sidecar]
    assert sidecar.exists()
    assert "42" in sidecar.read_text(encoding="utf-8")
    assert second.skipped == [sidecar]


def test_compress_context_preserves_frontmatter(tmp_path) -> None:
    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    frontmatter = "---\ntitle: An important note\ntags: [the-architecture]\n---\n"
    (knowledge / "note.md").write_text(
        frontmatter + "\nPlease note that the body can be compressed.\n",
        encoding="utf-8",
    )

    result = compress_context(tmp_path)

    compressed = result.files[0].read_text(encoding="utf-8")
    assert compressed.startswith(frontmatter)


def test_compress_context_drops_empty_list_items(tmp_path) -> None:
    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "note.md").write_text(
        "- basically simply\n- Very clearly important\n",
        encoding="utf-8",
    )

    result = compress_context(tmp_path)

    assert result.files[0].read_text(encoding="utf-8") == "- important\n"


def test_context_budget_does_not_double_count_sidecars(tmp_path) -> None:
    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "note.md").write_text(
        "Please note that in order to keep this context useful, the team keeps 42 facts. " * 20,
        encoding="utf-8",
    )

    before = inspect_context_budget(tmp_path)
    compress_context(tmp_path)
    after_original = inspect_context_budget(tmp_path)
    after_compressed = inspect_context_budget(tmp_path, prefer="compressed")
    after_both = inspect_context_budget(tmp_path, prefer="both")

    assert after_original.tokens_estimate == before.tokens_estimate
    assert after_compressed.tokens_estimate < before.tokens_estimate
    assert after_both.tokens_estimate > before.tokens_estimate


def test_compress_context_can_use_cloned_caveman_engine(tmp_path) -> None:
    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    tool = tmp_path / ".coding-scaffold" / "tools" / "caveman-compression"
    knowledge.mkdir(parents=True)
    tool.mkdir(parents=True)
    (knowledge / "note.txt").write_text("Verbose local note.\n", encoding="utf-8")
    (tool / "caveman_compress_nlp.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "output = Path(sys.argv[sys.argv.index('-o') + 1])\n"
        "output.write_text('Cave.\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )

    result = compress_context(tmp_path, engine="caveman")

    assert not result.warnings
    assert result.files[0].read_text(encoding="utf-8") == "Cave.\n"


def test_compress_preserves_inline_code_identifiers(tmp_path):
    from coding_scaffold.context import compress_context

    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    note = knowledge / "note.md"
    note.write_text(
        "Use `the-prod-route` to basically deploy.\n"
        "See [the docs](./the-docs) for clearly important details.\n",
        encoding="utf-8",
    )

    result = compress_context(tmp_path, source="knowledge")

    assert not result.warnings, result.warnings
    compressed = (knowledge / "note.caveman.md").read_text(encoding="utf-8")
    assert "`the-prod-route`" in compressed, compressed
    assert "[the docs](./the-docs)" in compressed, compressed
