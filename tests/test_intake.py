from coding_scaffold.intake import IntakeAnswers, _iter_project_files, collect_intake


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


def test_iter_project_files_prunes_ignored_directories(tmp_path) -> None:
    ignored = tmp_path / "node_modules" / "package" / "nested"
    ignored.mkdir(parents=True)
    for index in range(25):
        (ignored / f"ignored-{index}.js").write_text("console.log('skip')\n")
    (tmp_path / "src.py").write_text("print('keep')\n")

    files = list(_iter_project_files(tmp_path))

    assert files == [tmp_path / "src.py"]
