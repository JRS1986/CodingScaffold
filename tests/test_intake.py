from coding_scaffold.intake import IntakeAnswers, collect_intake


def test_intake_ignores_generated_scaffold_files(tmp_path) -> None:
    generated = tmp_path / ".coding-scaffold"
    generated.mkdir()
    (generated / "note.py").write_text("print('generated')\n")

    answers = collect_intake(tmp_path, IntakeAnswers(), interactive=False)

    assert answers.existing_codebase is False


def test_intake_only_ignores_directories_inside_target(tmp_path) -> None:
    target = tmp_path / ".venv-projects" / "app"
    target.mkdir(parents=True)
    (target / "main.py").write_text("print('real project')\n")

    answers = collect_intake(target, IntakeAnswers(), interactive=False)

    assert answers.language == "python"
    assert answers.existing_codebase is True


def test_intake_language_detection_excludes_scaffold_files(tmp_path) -> None:
    generated = tmp_path / ".coding-scaffold"
    generated.mkdir()
    (generated / "note.py").write_text("print('generated')\n")
    (tmp_path / "main.go").write_text("package main\n")

    answers = collect_intake(tmp_path, IntakeAnswers(), interactive=False)

    assert answers.language == "go"
