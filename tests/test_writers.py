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
            None,
            ["route locally"],
            {"selection_mode": "recommend"},
        ),
    )

    names = {path.name for path in manifest.files}
    assert "project.json" in names
    assert "AGENTS.md" in names
    assert "GETTING_STARTED.md" in names
    assert "SKILLS.md" in names
    assert "CREDENTIALS.md" in names
    assert "MODEL_SELECTION.md" in names
    assert "model-selection.json" in names
    assert "TOOLS.md" in names
    assert ".env.example" in names
    assert "credentials.example.json" in names
    assert "ORCHESTRATION.md" in names
    assert "orchestration.json" in names
    assert "FIRST_SESSION.md" in names
    assert "scaffold-version.json" in names
    assert "README.md" in {path.name for path in manifest.files if "skills" in path.parts}
    opencode = json.loads((tmp_path / ".coding-scaffold" / "opencode.json").read_text())
    assert "nativeAdapter" in opencode
    project = json.loads((tmp_path / ".coding-scaffold" / "project.json").read_text())
    assert project["language"] == "python"
    assert "tool" in project
    assert "agent" not in project
    version = json.loads((tmp_path / ".coding-scaffold" / "scaffold-version.json").read_text())
    assert ".coding-scaffold/AGENTS.md" in version["files"]


def test_providers_json_redacts_azure_endpoint(tmp_path, monkeypatch) -> None:
    from coding_scaffold.providers import detect_providers

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://contoso.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "internal-gpt")

    write_scaffold(
        tmp_path,
        IntakeAnswers(language="python", project_target="CLI", existing_codebase=True, privacy="local-first"),
        HardwareProfile("linux", False, 8, 32, None, None, True, ["ollama"]),
        detect_providers(),
        RoutingPlan(
            "local-first-router",
            "qwen2.5-coder:14b-instruct",
            "qwen2.5-coder:32b-instruct",
            0.1,
            "http://127.0.0.1:11434/v1",
            None,
            None,
            ["route locally"],
            {"selection_mode": "recommend"},
        ),
    )

    providers_json = (tmp_path / ".coding-scaffold" / "providers.json").read_text(encoding="utf-8")
    assert "contoso.openai.azure.com" not in providers_json
    assert "internal-gpt" not in providers_json


def test_routellm_yaml_quotes_model_names_with_special_chars() -> None:
    from coding_scaffold.writers import _routellm_yaml

    plan = RoutingPlan(
        strategy="local-first-router",
        weak_model="weird: 'value with # hash'",
        strong_model="qwen2.5-coder:7b-instruct",
        route_threshold=0.1,
        local_endpoint="http://127.0.0.1:11434/v1",
        cloud_provider=None,
        cloud_model_family=None,
        route_rules=["route locally"],
        model_policy={"selection_mode": "recommend"},
    )

    output = _routellm_yaml(plan)
    assert '"weird: \'value with # hash\'"' in output
    assert '"qwen2.5-coder:7b-instruct"' in output
    assert '"http://127.0.0.1:11434/v1"' in output

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return
    parsed = yaml.safe_load(output)
    assert parsed["weak_model"] == "weird: 'value with # hash'"
    assert parsed["strong_model"] == "qwen2.5-coder:7b-instruct"
    assert parsed["providers"]["local"]["base_url"] == "http://127.0.0.1:11434/v1"
