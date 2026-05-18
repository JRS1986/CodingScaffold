import coding_scaffold.intake as intake_module
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


def test_detect_language_skips_vendored_dirs(tmp_path) -> None:
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    for index in range(10):
        (node_modules / f"pkg-{index}.js").write_text("module.exports = {}\n")
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hi')\n")

    answers = collect_intake(tmp_path, IntakeAnswers(), interactive=False)

    assert answers.language == "python"


def test_detect_language_respects_depth_cap(tmp_path) -> None:
    # Shallow file at depth 1 (counts).
    (tmp_path / "main.go").write_text("package main\n")
    # Deeply nested .py file beyond _MAX_WALK_DEPTH should not be counted.
    deep = tmp_path
    for level in range(intake_module._MAX_WALK_DEPTH + 2):
        deep = deep / f"level{level}"
    deep.mkdir(parents=True)
    (deep / "deep.py").write_text("print('too deep')\n")

    answers = collect_intake(tmp_path, IntakeAnswers(), interactive=False)

    assert answers.language == "go"


def test_collect_intake_skips_detection_when_language_provided(tmp_path, monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("should not walk")

    monkeypatch.setattr(intake_module.os, "walk", _boom)

    answers = collect_intake(
        tmp_path,
        IntakeAnswers(language="python", existing_codebase=False),
        interactive=False,
    )

    assert answers.language == "python"
    assert answers.existing_codebase is False
