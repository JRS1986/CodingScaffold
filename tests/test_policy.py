import json

from coding_scaffold.policy import write_policy_pack


def test_write_policy_pack_creates_opencode_policy(tmp_path) -> None:
    result = write_policy_pack(
        tmp_path,
        scope="company",
        enabled_providers=["ollama", "azure-ai"],
        disabled_mcp_servers=["jira"],
    )

    names = {path.name for path in result.files}
    assert "policy.json" in names
    assert "opencode-policy.json" in names
    assert "opencode.json" in names

    opencode = json.loads((tmp_path / "opencode.json").read_text())
    assert opencode["share"] == "disabled"
    assert opencode["enabled_providers"] == ["ollama", "azure-ai"]
    assert opencode["disabled_providers"] == ["opencode"]
    assert opencode["mcp"]["jira"]["enabled"] is False
    assert opencode["permission"]["edit"] == "ask"


def test_write_policy_pack_merges_existing_opencode_config(tmp_path) -> None:
    (tmp_path / "opencode.json").write_text(
        json.dumps({"default_agent": "plan", "instructions": ["AGENTS.md"]}),
        encoding="utf-8",
    )

    write_policy_pack(tmp_path, scope="team", disabled_providers=["opencode", "openai"])

    opencode = json.loads((tmp_path / "opencode.json").read_text())
    assert opencode["default_agent"] == "plan"
    assert opencode["instructions"] == ["AGENTS.md", ".coding-scaffold/policy/*.md"]
    assert opencode["disabled_providers"] == ["opencode", "openai"]
