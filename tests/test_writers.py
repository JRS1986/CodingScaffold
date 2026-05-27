import json

from coding_scaffold.writers import write_scaffold


def test_write_scaffold_creates_expected_files(tmp_path, scaffold_inputs) -> None:
    fixture = scaffold_inputs(tool=None)
    manifest = write_scaffold(
        tmp_path,
        fixture.intake,
        fixture.hardware,
        fixture.providers,
        fixture.routing,
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
    assert "tools" in project
    assert "tool" not in project, "singular `tool` key must not be written to project.json"
    assert "agent" not in project
    version = json.loads((tmp_path / ".coding-scaffold" / "scaffold-version.json").read_text())
    assert ".coding-scaffold/AGENTS.md" in version["files"]


def test_generated_getting_started_uses_global_cli_install(tmp_path, scaffold_inputs) -> None:
    fixture = scaffold_inputs(tool=None)
    write_scaffold(
        tmp_path,
        fixture.intake,
        fixture.hardware,
        fixture.providers,
        fixture.routing,
    )

    text = (tmp_path / ".coding-scaffold" / "GETTING_STARTED.md").read_text(encoding="utf-8")
    assert "uv tool install git+https://github.com/JRS1986/CodingScaffold.git" in text
    assert "pipx install git+https://github.com/JRS1986/CodingScaffold.git" in text
    assert "source .venv/bin/activate" not in text
    assert "should not need" in text
    assert "activate a virtual environment" in text


def test_providers_json_redacts_azure_endpoint(tmp_path, monkeypatch, scaffold_inputs) -> None:
    from coding_scaffold.providers import detect_providers

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://contoso.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "internal-gpt")
    fixture = scaffold_inputs(tool=None)

    write_scaffold(
        tmp_path,
        fixture.intake,
        fixture.hardware,
        detect_providers(),
        fixture.routing,
    )

    providers_json = (tmp_path / ".coding-scaffold" / "providers.json").read_text(encoding="utf-8")
    assert "contoso.openai.azure.com" not in providers_json
    assert "internal-gpt" not in providers_json


def test_routellm_yaml_quotes_model_names_with_special_chars(routing_plan_factory) -> None:
    from coding_scaffold.writers import _routellm_yaml

    plan = routing_plan_factory(
        weak_model="weird: 'value with # hash'",
        strong_model="qwen2.5-coder:7b-instruct",
        route_threshold=0.1,
    )

    output = _routellm_yaml(plan)
    assert "\"weird: 'value with # hash'\"" in output
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
