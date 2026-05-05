from coding_scaffold.intake import IntakeAnswers, collect_intake


def test_intake_ignores_generated_scaffold_files(tmp_path) -> None:
    generated = tmp_path / ".coding-scaffold"
    generated.mkdir()
    (generated / "note.py").write_text("print('generated')\n")

    answers = collect_intake(tmp_path, IntakeAnswers(), interactive=False)

    assert answers.language == "python"
    assert answers.existing_codebase is False
