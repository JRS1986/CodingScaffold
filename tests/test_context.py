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
