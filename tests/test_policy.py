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
    assert "disabled_providers" not in opencode
    assert opencode["mcp"]["jira"]["enabled"] is False
    assert opencode["permission"]["edit"] == "ask"


def test_write_policy_pack_merges_existing_opencode_config(tmp_path) -> None:
    original = {"default_agent": "plan", "instructions": ["AGENTS.md"]}
    (tmp_path / "opencode.json").write_text(
        json.dumps(original),
        encoding="utf-8",
    )

    write_policy_pack(tmp_path, scope="team", disabled_providers=["opencode", "openai"])

    # Original file untouched; merged result is staged for review.
    assert json.loads((tmp_path / "opencode.json").read_text()) == original
    opencode = json.loads((tmp_path / "opencode.json.new").read_text())
    assert opencode["default_agent"] == "plan"
    assert opencode["instructions"] == ["AGENTS.md", ".coding-scaffold/policy/*.md"]
    assert opencode["disabled_providers"] == ["opencode", "openai"]


def test_policy_preserves_user_mcp_servers(tmp_path):
    target = tmp_path
    (target / ".coding-scaffold").mkdir()
    opencode = target / "opencode.json"
    opencode.write_text(
        json.dumps(
            {
                "mcp": {
                    "user-defined-server": {"command": "user-server", "enabled": True},
                },
            }
        ),
        encoding="utf-8",
    )

    write_policy_pack(target, scope="team", disabled_mcp_servers=["bad-server"])

    new_file = target / "opencode.json.new"
    assert new_file.exists(), "policy must stage opencode.json.new when opencode.json exists"
    # Original untouched.
    original = json.loads(opencode.read_text(encoding="utf-8"))
    assert original == {
        "mcp": {"user-defined-server": {"command": "user-server", "enabled": True}}
    }
    # Staged file deep-merges: user's server survives alongside the disabled one.
    staged = json.loads(new_file.read_text(encoding="utf-8"))
    assert staged["mcp"]["user-defined-server"] == {"command": "user-server", "enabled": True}
    assert staged["mcp"]["bad-server"] == {"enabled": False}
