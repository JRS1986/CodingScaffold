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
    assert "knowledge-propose.md" in names
    assert "recheck-route.md" in names
    assert (tmp_path / ".opencode" / "agents" / "reviewer.md").exists()
    knowledge_propose = (tmp_path / ".opencode" / "commands" / "knowledge-propose.md").read_text()
    assert "configured model" in knowledge_propose
    assert "Do not write raw chat transcripts" in knowledge_propose


def test_write_claude_code_adapter_creates_native_files(tmp_path) -> None:
    scaffold = tmp_path / ".coding-scaffold"
    scaffold.mkdir()
    (scaffold / "routing.json").write_text(
        json.dumps({"weak_model": "claude-routine", "strong_model": "claude-heavy"})
    )

    result = write_tool_adapter(tmp_path, "claude-code")

    names = {path.name for path in result.files}
    assert "CLAUDE.md" in names
    assert "settings.json" in names
    assert "first-session.md" in names
    assert "agentic-change.md" in names
    assert "knowledge-propose.md" in names
    assert "reviewer.md" in names
    assert "claude-heavy" in (tmp_path / ".claude" / "agents" / "reviewer.md").read_text()
    assert "Knowledge Nudge" in (tmp_path / "CLAUDE.md").read_text()
    assert "defaultMode" in (tmp_path / ".claude" / "settings.json").read_text()


def test_write_codex_adapter_creates_native_files(tmp_path) -> None:
    result = write_tool_adapter(tmp_path, "codex")

    names = {path.name for path in result.files}
    assert "AGENTS.md" in names
    assert "config.toml" in names
    assert "README.md" in names
    assert "first-session.md" in names
    assert "knowledge-propose.md" in names
    assert "approval_mode" in (tmp_path / ".codex" / "config.toml").read_text()
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "does not replace Codex" in agents
    assert "Knowledge Nudge" in agents


def test_write_new_adapters_preserve_existing_files(tmp_path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Human Codex Notes\n", encoding="utf-8")

    result = write_tool_adapter(tmp_path, "codex")

    assert agents in result.skipped
    assert agents.read_text(encoding="utf-8") == "# Human Codex Notes\n"


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


def test_routellm_yaml_quotes_model_names_with_special_chars() -> None:
    from coding_scaffold.adapters import _routellm_yaml

    output = _routellm_yaml(
        {
            "weak_model": "weird: 'value with # hash'",
            "strong_model": "qwen2.5-coder:7b-instruct",
        }
    )

    assert '"weird: \'value with # hash\'"' in output
    assert '"qwen2.5-coder:7b-instruct"' in output

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return
    parsed = yaml.safe_load(output)
    assert parsed["weak_model"] == "weird: 'value with # hash'"
    assert parsed["strong_model"] == "qwen2.5-coder:7b-instruct"


def test_write_open_multi_agent_backend_creates_docs_config_and_example(tmp_path) -> None:
    result = write_workflow_backend(tmp_path, "open-multi-agent")

    names = {path.name for path in result.files}
    assert "OPEN_MULTI_AGENT.md" in names
    assert "open-multi-agent.team.json" in names
    assert "team-coding-workflow.ts" in names
    team_config = json.loads((tmp_path / ".coding-scaffold" / "open-multi-agent.team.json").read_text())
    assert team_config["backend"] == "open-multi-agent"
    assert (tmp_path / "examples" / "open-multi-agent" / "team-coding-workflow.ts").exists()
