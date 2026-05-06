import io
import json
import sys

from coding_scaffold.cli import build_parser, main


def test_parser_lists_user_facing_commands() -> None:
    help_text = build_parser().format_help()

    assert "select-model" in help_text
    assert "knowledge" in help_text
    assert "policy" in help_text
    assert "workflow" in help_text


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


def test_adapt_route_and_workflow_commands(tmp_path) -> None:
    assert main(["adapt", "--target", str(tmp_path), "--tool", "opencode"]) == 0
    assert main(["route", "--target", str(tmp_path), "--backend", "routellm"]) == 0
    assert main(["workflow", "--target", str(tmp_path), "--backend", "open-multi-agent"]) == 0

    assert (tmp_path / "opencode.json").exists()
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
