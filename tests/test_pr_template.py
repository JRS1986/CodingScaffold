"""Coverage for `pr_template.write_pr_template` (issue #93).

Asserts the generated PR template lands in the right place, contains the disclosure
sections the reviewer template promises, and is idempotent — running twice doesn't
clobber a user-edited file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.pr_template import (
    PR_TEMPLATE_RELATIVE,
    PrTemplateResult,
    write_pr_template,
)


def test_writes_file_at_expected_relative_path(tmp_path: Path) -> None:
    result = write_pr_template(tmp_path)
    assert result.files == [tmp_path / PR_TEMPLATE_RELATIVE]
    assert (tmp_path / PR_TEMPLATE_RELATIVE).exists()


def test_generated_template_contains_required_sections(tmp_path: Path) -> None:
    write_pr_template(tmp_path)
    content = (tmp_path / PR_TEMPLATE_RELATIVE).read_text(encoding="utf-8")
    for heading in (
        "## Agentic coding disclosure",
        "## What changed",
        "## Risk surface",
        "## Review focus",
    ):
        assert heading in content, f"missing required section: {heading}"


def test_generated_template_names_disclosure_fields(tmp_path: Path) -> None:
    write_pr_template(tmp_path)
    content = (tmp_path / PR_TEMPLATE_RELATIVE).read_text(encoding="utf-8")
    for field in (
        "Agent / tool used",
        "Model / provider",
        "Files changed",
        "Commands run",
        "Tests run",
        "Tests not run and why",
        "External tools or MCP servers used",
        "Human review focus",
    ):
        assert field in content, f"PR template missing field: {field!r}"


def test_re_run_is_idempotent_and_does_not_overwrite_user_edits(tmp_path: Path) -> None:
    write_pr_template(tmp_path)
    user_text = "# I edited this template manually\n"
    (tmp_path / PR_TEMPLATE_RELATIVE).write_text(user_text, encoding="utf-8")

    second = write_pr_template(tmp_path)

    assert second.files == []
    assert second.skipped == [tmp_path / PR_TEMPLATE_RELATIVE]
    # User edit preserved.
    assert (tmp_path / PR_TEMPLATE_RELATIVE).read_text(encoding="utf-8") == user_text


def test_result_to_dict_is_json_serializable(tmp_path: Path) -> None:
    result = write_pr_template(tmp_path)
    payload = result.to_dict()
    json.dumps(payload)
    assert isinstance(payload["files"], list)
    assert isinstance(payload["skipped"], list)


def test_pr_template_relative_path_under_github_directory() -> None:
    parts = PR_TEMPLATE_RELATIVE.parts
    assert parts[0] == ".github"
    assert parts[1] == "PULL_REQUEST_TEMPLATE"
    assert parts[-1].endswith(".md")


def test_result_dataclass_is_a_frozen_pr_template_result(tmp_path: Path) -> None:
    result = write_pr_template(tmp_path)
    assert isinstance(result, PrTemplateResult)
    with pytest.raises(Exception):
        # frozen dataclass — mutation should fail
        result.files = []  # type: ignore[misc]


def test_cli_pr_template_init_writes_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["pr-template", "init", "--target", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / PR_TEMPLATE_RELATIVE).exists()
    out = capsys.readouterr().out
    assert "agentic-change" in out or "PR template" in out
