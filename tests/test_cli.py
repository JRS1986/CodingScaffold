import io
import json
import sys

from coding_scaffold.cli import build_parser, main
from coding_scaffold.installers import ToolInstallResult


def test_parser_lists_user_facing_commands() -> None:
    help_text = build_parser().format_help()

    visible = [
        "probe",
        "setup",
        "credentials",
        "skill",
        "knowledge",
        "context",
        "team",
        "policy",
        "tools",
        "doctor",
    ]
    for command in visible:
        assert command in help_text
    assert "select-model" not in help_text
    assert "setup-addon" not in help_text
    assert "setup-knowledge" not in help_text
    assert "setup-tool" not in help_text
    assert "compress-context" not in help_text
    assert "context-budget" not in help_text
    assert "==SUPPRESS==" not in help_text
    assert len(visible) <= 10


def test_setup_run_command(tmp_path, capsys) -> None:
    assert main(["setup", "run", "--target", str(tmp_path), "--language", "python", "--non-interactive"]) == 0

    output = capsys.readouterr().out
    assert "Wrote scaffold" in output
    assert (tmp_path / ".coding-scaffold" / "GETTING_STARTED.md").exists()
    version = json.loads((tmp_path / ".coding-scaffold" / "scaffold-version.json").read_text())
    assert ".opencode/agents/reviewer.md" in version["files"]


def test_grouped_context_commands(tmp_path, capsys) -> None:
    main(["knowledge", "create", "--target", str(tmp_path)])
    capsys.readouterr()
    verbose = tmp_path / ".coding-scaffold" / "knowledge" / "verbose.md"
    verbose.write_text(
        "In order to deploy, it is important to please note that we basically simply run the script.\n",
        encoding="utf-8",
    )

    assert main(["context", "budget", "--target", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "knowledge"
    assert main(["context", "compress", "--target", str(tmp_path)]) == 0
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "verbose.caveman.md").exists()


def test_grouped_tools_commands(tmp_path) -> None:
    assert main(["tools", "adapt", "--target", str(tmp_path), "--tool", "opencode"]) == 0
    assert main(["tools", "adapt", "--target", str(tmp_path), "--tool", "claude-code"]) == 0
    assert main(["tools", "adapt", "--target", str(tmp_path), "--tool", "codex"]) == 0
    assert main(["tools", "adapt", "--target", str(tmp_path), "--tool", "hermes"]) == 0
    assert main(["tools", "adapt", "--target", str(tmp_path), "--tool", "pi"]) == 0
    assert main(["tools", "route", "--target", str(tmp_path), "--backend", "routellm"]) == 0
    assert main(["tools", "workflow", "--target", str(tmp_path), "--backend", "open-multi-agent"]) == 0

    assert (tmp_path / "opencode.json").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".coding-scaffold" / "HERMES.md").exists()
    assert (tmp_path / ".coding-scaffold" / "PI.md").exists()
    assert (tmp_path / ".coding-scaffold" / "ROUTELLM.md").exists()
    assert (tmp_path / ".coding-scaffold" / "OPEN_MULTI_AGENT.md").exists()


def test_setup_update_preserves_edited_files(tmp_path, capsys) -> None:
    assert main(["setup", "run", "--target", str(tmp_path), "--language", "python", "--non-interactive"]) == 0
    agents = tmp_path / ".coding-scaffold" / "AGENTS.md"
    reviewer = tmp_path / ".opencode" / "agents" / "reviewer.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "\nCustom local note.\n", encoding="utf-8")
    reviewer.write_text(reviewer.read_text(encoding="utf-8") + "\nCustom reviewer note.\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["setup", "update", "--target", str(tmp_path), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["staged"]
    assert agents.read_text(encoding="utf-8").endswith("Custom local note.\n")
    assert reviewer.read_text(encoding="utf-8").endswith("Custom reviewer note.\n")
    assert (tmp_path / ".coding-scaffold" / "AGENTS.md.new").exists()
    assert (tmp_path / ".opencode" / "agents" / "reviewer.md.new").exists()
    assert (tmp_path / ".coding-scaffold" / "scaffold-version.json").exists()


def test_knowledge_status_grouped_command(tmp_path, capsys) -> None:
    main(["knowledge", "create", "--target", str(tmp_path)])
    capsys.readouterr()

    assert main(["knowledge", "status", "--target", str(tmp_path), "--json"]) == 0

    assert "counts" in json.loads(capsys.readouterr().out)


def test_knowledge_distill_grouped_command(tmp_path, capsys) -> None:
    main(["knowledge", "create", "--target", str(tmp_path)])
    raw = tmp_path / ".coding-scaffold" / "knowledge" / "raw" / "meetings" / "pilot.md"
    raw.write_text("# Pilot Notes\n\nUse pytest for checks.\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["knowledge", "distill", "--target", str(tmp_path), "--source", "raw", "--review"]) == 0

    assert "Created 1 knowledge proposal" in capsys.readouterr().out
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "wiki" / "pilot.md.new").exists()


def test_setup_tool_command_grouped(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "coding_scaffold.cli.install_missing_tools",
        lambda tool, interactive, assume_yes=False: [
            ToolInstallResult(tool, "present", "opencode is already installed.")
        ],
    )

    assert main(["setup", "tool", "--tool", "opencode"]) == 0

    assert "opencode: present" in capsys.readouterr().out


def test_setup_addon_command_grouped(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "coding_scaffold.cli.install_missing_addons",
        lambda addon, interactive, assume_yes=False, target=None: [
            ToolInstallResult(addon, "present", "llmfit is already installed.")
        ],
    )

    assert main(["setup", "addon", "--target", str(tmp_path), "--addon", "llmfit"]) == 0

    assert "llmfit: present" in capsys.readouterr().out


def test_setup_knowledge_command_grouped(tmp_path) -> None:
    assert (
        main(
            [
                "setup",
                "knowledge",
                "--target",
                str(tmp_path),
                "--backend",
                "markdown",
                "--shared-remote",
                "https://example.test/team-ai-knowledge.git",
            ]
        )
        == 0
    )

    config = json.loads((tmp_path / ".coding-scaffold" / "knowledge.json").read_text())
    assert config["shared_remote"] == "https://example.test/team-ai-knowledge.git"


def test_hidden_legacy_commands_still_work(tmp_path, capsys) -> None:
    assert main(["context-budget", "--target", str(tmp_path), "--json"]) == 0
    assert main(["tools", "select-model", "--target", str(tmp_path), "--prompt", "Fix this test"]) == 0

    assert "Route: routine" in capsys.readouterr().out


def test_legacy_update_alias_works(tmp_path, capsys) -> None:
    assert main(["setup", "run", "--target", str(tmp_path), "--language", "python", "--non-interactive"]) == 0
    capsys.readouterr()

    assert main(["update", "--target", str(tmp_path)]) == 0

    assert "Updated" in capsys.readouterr().out


def test_hidden_legacy_setup_commands_remain_compatible(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "coding_scaffold.cli.install_missing_tools",
        lambda tool, interactive, assume_yes=False: [
            ToolInstallResult(tool, "present", "opencode is already installed.")
        ],
    )

    assert main(["setup-tool", "--tool", "opencode"]) == 0
    assert main(["setup-knowledge", "--target", str(tmp_path), "--backend", "markdown"]) == 0

    output = capsys.readouterr().out
    assert "opencode: present" in output
    assert (tmp_path / ".coding-scaffold" / "knowledge.json").exists()


def test_probe_json_command(capsys) -> None:
    assert main(["probe", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "hardware" in payload
    assert "providers" in payload


def test_init_non_interactive_command(tmp_path, capsys) -> None:
    assert main(["init", "--target", str(tmp_path), "--language", "python", "--non-interactive"]) == 0

    output = capsys.readouterr().out
    assert "Wrote scaffold" in output
    assert (tmp_path / ".coding-scaffold" / "GETTING_STARTED.md").exists()


def test_credentials_command(tmp_path) -> None:
    assert main(["credentials", "--target", str(tmp_path), "--format", "env"]) == 0

    assert (tmp_path / ".coding-scaffold" / ".env.local").exists()


def test_skill_command(tmp_path) -> None:
    assert main(["skill", "--target", str(tmp_path), "--name", "Release Review"]) == 0

    assert (tmp_path / ".coding-scaffold" / "skills" / "release-review.md").exists()


def test_knowledge_command(tmp_path) -> None:
    assert main(["knowledge", "--target", str(tmp_path), "--shared-remote", "https://example.test/kb.git"]) == 0

    assert (tmp_path / ".coding-scaffold" / "knowledge" / "INDEX.md").exists()


def test_knowledge_status_command(tmp_path, capsys) -> None:
    main(["knowledge", "--target", str(tmp_path)])
    capsys.readouterr()

    assert main(["knowledge-status", "--target", str(tmp_path), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "counts" in payload


def test_context_budget_command(tmp_path, capsys) -> None:
    main(["knowledge", "--target", str(tmp_path)])
    capsys.readouterr()

    assert main(["context-budget", "--target", str(tmp_path), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "knowledge"
    assert "tokens_estimate" in payload


def test_compress_context_command(tmp_path, capsys) -> None:
    main(["knowledge", "--target", str(tmp_path)])
    capsys.readouterr()
    verbose = tmp_path / ".coding-scaffold" / "knowledge" / "verbose.md"
    verbose.write_text(
        "In order to deploy, it is important to please note that we basically simply run the script.\n",
        encoding="utf-8",
    )

    assert main(["compress-context", "--target", str(tmp_path)]) == 0

    assert "compressed context sidecar" in capsys.readouterr().out
    assert (tmp_path / ".coding-scaffold" / "knowledge" / "verbose.caveman.md").exists()


def test_setup_knowledge_command(tmp_path) -> None:
    assert (
        main(
            [
                "setup-knowledge",
                "--target",
                str(tmp_path),
                "--backend",
                "markdown",
                "--shared-remote",
                "https://example.test/team-ai-knowledge.git",
            ]
        )
        == 0
    )

    config = json.loads((tmp_path / ".coding-scaffold" / "knowledge.json").read_text())
    assert config["shared_remote"] == "https://example.test/team-ai-knowledge.git"


def test_init_can_configure_knowledge_during_setup(tmp_path) -> None:
    assert (
        main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--language",
                "python",
                "--non-interactive",
                "--knowledge-backend",
                "obsidian",
                "--knowledge-remote",
                "https://example.test/team-ai-knowledge.git",
            ]
        )
        == 0
    )

    assert (tmp_path / ".coding-scaffold" / "knowledge" / ".obsidian" / "graph.json").exists()
    config = json.loads((tmp_path / ".coding-scaffold" / "knowledge.json").read_text())
    assert config["backend"] == "obsidian"


def test_adapt_route_and_workflow_commands(tmp_path) -> None:
    assert main(["adapt", "--target", str(tmp_path), "--tool", "opencode"]) == 0
    assert main(["adapt", "--target", str(tmp_path), "--tool", "claude-code"]) == 0
    assert main(["adapt", "--target", str(tmp_path), "--tool", "codex"]) == 0
    assert main(["route", "--target", str(tmp_path), "--backend", "routellm"]) == 0
    assert main(["workflow", "--target", str(tmp_path), "--backend", "open-multi-agent"]) == 0

    assert (tmp_path / "opencode.json").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".coding-scaffold" / "ROUTELLM.md").exists()
    assert (tmp_path / ".coding-scaffold" / "OPEN_MULTI_AGENT.md").exists()


def test_policy_command(tmp_path) -> None:
    assert (
        main(
            [
                "policy",
                "--target",
                str(tmp_path),
                "--scope",
                "company",
                "--enable-provider",
                "ollama",
                "--disable-mcp-server",
                "jira",
            ]
        )
        == 0
    )

    assert (tmp_path / ".coding-scaffold" / "policy" / "company.md").exists()
    assert (tmp_path / "opencode.json").exists()


def test_setup_tool_command(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "coding_scaffold.cli.install_missing_tools",
        lambda tool, interactive, assume_yes=False: [
            ToolInstallResult(tool, "present", "opencode is already installed.")
        ],
    )

    assert main(["setup-tool", "--tool", "opencode"]) == 0

    assert "opencode: present" in capsys.readouterr().out


def test_setup_addon_command(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "coding_scaffold.cli.install_missing_addons",
        lambda addon, interactive, assume_yes=False, target=None: [
            ToolInstallResult(addon, "present", "llmfit is already installed.")
        ],
    )

    assert main(["setup-addon", "--target", str(tmp_path), "--addon", "llmfit"]) == 0

    assert "llmfit: present" in capsys.readouterr().out


def test_team_init_and_doctor_commands(tmp_path, capsys) -> None:
    assert main(["team", "init", "--target", str(tmp_path), "--team", "platform-api"]) == 0

    output = capsys.readouterr().out
    assert "team-onboarding.json" in output
    assert main(["team", "doctor", "--target", str(tmp_path)]) == 0
    assert "Team: platform-api" in capsys.readouterr().out


def test_team_init_rejects_connect_flags(tmp_path) -> None:
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        main(["team", "init", "--target", str(tmp_path), "--allow-local"])
    assert excinfo.value.code != 0


def test_team_connect_noninteractive_requires_yes(tmp_path, capsys) -> None:
    manifest = tmp_path / "team-onboarding.json"
    manifest.write_text(json.dumps({"team": "platform-api", "security": {"secrets_allowed": False}}))

    assert main(["team", "connect", "--target", str(tmp_path / "project"), "--manifest", str(manifest)]) == 1

    assert "without --yes" in capsys.readouterr().err


def test_init_accepts_canonical_tool_flag(tmp_path) -> None:
    assert (
        main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--language",
                "python",
                "--tool",
                "manual",
                "--non-interactive",
            ]
        )
        == 0
    )


def test_init_accepts_new_harnesses(tmp_path) -> None:
    assert (
        main(
            [
                "init",
                "--target",
                str(tmp_path / "hermes-project"),
                "--language",
                "python",
                "--tool",
                "hermes",
                "--non-interactive",
            ]
        )
        == 0
    )
    assert (tmp_path / "hermes-project" / ".coding-scaffold" / "HERMES.md").exists()

    assert (
        main(
            [
                "init",
                "--target",
                str(tmp_path / "pi-project"),
                "--language",
                "python",
                "--tool",
                "pi",
                "--non-interactive",
            ]
        )
        == 0
    )
    assert (tmp_path / "pi-project" / ".coding-scaffold" / "PI.md").exists()


def test_init_accepts_legacy_agent_alias(tmp_path) -> None:
    legacy_flag = "--" + "agent"
    assert (
        main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--language",
                "python",
                legacy_flag,
                "manual",
                "--non-interactive",
            ]
        )
        == 0
    )


def test_select_model_with_prompt(tmp_path, capsys) -> None:
    assert main(["select-model", "--target", str(tmp_path), "--prompt", "Review this migration"]) == 0

    output = capsys.readouterr().out
    assert "Route: heavy-lift" in output


def test_select_model_reads_prompt_from_stdin(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("Fix this failing test\n"))

    assert main(["select-model", "--target", str(tmp_path), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["route"] == "routine"


def test_select_model_missing_prompt_returns_error(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", _TtyInput())

    assert main(["select-model", "--target", str(tmp_path)]) == 2

    assert "Provide --prompt" in capsys.readouterr().err


class _TtyInput(io.StringIO):
    def isatty(self) -> bool:
        return True
