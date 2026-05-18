import json
import shutil
from pathlib import Path

from coding_scaffold.cli import main


FIXTURES = Path(__file__).parent / "fixtures"


def test_non_interactive_setup_on_sample_repo_is_idempotent(tmp_path, capsys) -> None:
    project = tmp_path / "sample"
    shutil.copytree(FIXTURES / "sample_repo", project)

    assert main(["setup", "run", "--target", str(project), "--language", "python", "--non-interactive"]) == 0
    capsys.readouterr()
    assert main(["setup", "update", "--target", str(project), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert (project / ".coding-scaffold" / "AGENTS.md").exists()
    assert (project / "opencode.json").exists()
    assert payload["staged"] == []
    assert "OPENAI_API_KEY=" in (project / ".coding-scaffold" / ".env.example").read_text(encoding="utf-8")
    assert "sk-" not in (project / ".coding-scaffold" / ".env.example").read_text(encoding="utf-8")
