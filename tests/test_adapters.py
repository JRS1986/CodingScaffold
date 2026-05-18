import json

from coding_scaffold.adapters import write_route_backend, write_tool_adapter, write_workflow_backend


def test_write_opencode_adapter_creates_native_files(tmp_path) -> None:
    scaffold = tmp_path / ".coding-scaffold"
    scaffold.mkdir()
    (scaffold / "routing.json").write_text(
        json.dumps({"weak_model": "qwen-small", "strong_model": "qwen-large"})
    )

    result = write_tool_adapter(tmp_path, "opencode")

    names = {path.name for path in result.files}
    assert "opencode.json" in names
    assert "reviewer.md" in names
    assert "first-session.md" in names
    assert "agentic-change.md" in names
    assert "recheck-route.md" in names
    assert (tmp_path / ".opencode" / "agents" / "reviewer.md").exists()


def test_write_hermes_adapter_creates_project_guidance(tmp_path) -> None:
    result = write_tool_adapter(tmp_path, "hermes")

    names = {path.name for path in result.files}
    assert "HERMES.md" in names
    assert "hermes setup" in (tmp_path / ".coding-scaffold" / "HERMES.md").read_text()


def test_write_pi_adapter_creates_project_guidance(tmp_path) -> None:
    result = write_tool_adapter(tmp_path, "pi")

    names = {path.name for path in result.files}
    assert "PI.md" in names
    assert "@earendil-works/pi-coding-agent" in (tmp_path / ".coding-scaffold" / "PI.md").read_text()


def test_write_routellm_backend_creates_docs_and_config(tmp_path) -> None:
    result = write_route_backend(tmp_path, "routellm")

    names = {path.name for path in result.files}
    assert "ROUTELLM.md" in names
    assert "routellm.config.yaml" in names


def test_write_open_multi_agent_backend_creates_docs_config_and_example(tmp_path) -> None:
    result = write_workflow_backend(tmp_path, "open-multi-agent")

    names = {path.name for path in result.files}
    assert "OPEN_MULTI_AGENT.md" in names
    assert "open-multi-agent.team.json" in names
    assert "team-coding-workflow.ts" in names
    team_config = json.loads((tmp_path / ".coding-scaffold" / "open-multi-agent.team.json").read_text())
    assert team_config["backend"] == "open-multi-agent"
    assert (tmp_path / "examples" / "open-multi-agent" / "team-coding-workflow.ts").exists()
