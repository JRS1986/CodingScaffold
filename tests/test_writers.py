import json

from coding_scaffold.hardware import HardwareProfile
from coding_scaffold.intake import IntakeAnswers
from coding_scaffold.providers import Provider
from coding_scaffold.router import RoutingPlan
from coding_scaffold.writers import write_scaffold


def test_write_scaffold_creates_expected_files(tmp_path) -> None:
    manifest = write_scaffold(
        tmp_path,
        IntakeAnswers(language="python", project_target="CLI", existing_codebase=True, privacy="local-first"),
        HardwareProfile("linux", False, 8, 32, None, None, True, ["ollama"]),
        [Provider("ollama", "local", True, "CLI found", "http://127.0.0.1:11434/v1")],
        RoutingPlan(
            "local-first-router",
            "qwen2.5-coder:14b-instruct",
            "qwen2.5-coder:32b-instruct",
            0.1,
            "http://127.0.0.1:11434/v1",
            None,
            ["route locally"],
        ),
    )

    names = {path.name for path in manifest.files}
    assert "project.json" in names
    assert "AGENTS.md" in names
    assert "theme.json" in names
    assert "GETTING_STARTED.md" in names
    assert "SKILLS.md" in names
    assert "THEME.md" in names
    assert "CREDENTIALS.md" in names
    assert "TOOLS.md" in names
    assert ".env.example" in names
    assert "credentials.example.json" in names
    assert "ORCHESTRATION.md" in names
    assert "orchestration.json" in names
    assert "README.md" in {path.name for path in manifest.files if "skills" in path.parts}
    project = json.loads((tmp_path / ".coding-scaffold" / "project.json").read_text())
    assert project["language"] == "python"
