from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import main
from coding_scaffold.permissions import (
    PERMISSIONS_RELATIVE,
    default_permissions,
    write_agent_permissions,
)


def test_default_permissions_has_expected_top_level_keys(tmp_path: Path) -> None:
    payload = default_permissions(tmp_path)
    assert set(payload.keys()) >= {
        "$schema_version",
        "description",
        "filesystem",
        "shell",
        "network",
        "mcp",
    }
    assert payload["network"] == "disabled_by_default"
    assert "remote_servers" in payload["mcp"]
    assert "unapproved_servers" in payload["mcp"]
    assert isinstance(payload["filesystem"]["deny"], list)
    assert ".env" in payload["filesystem"]["deny"]


def test_default_permissions_includes_python_commands_for_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    payload = default_permissions(tmp_path)
    assert "pytest" in payload["shell"]["allowed"]
    assert "ruff" in payload["shell"]["allowed"]


def test_default_permissions_includes_node_commands_for_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    payload = default_permissions(tmp_path)
    assert "npm test" in payload["shell"]["allowed"]


def test_write_agent_permissions_creates_file_first_run(tmp_path: Path) -> None:
    result = write_agent_permissions(tmp_path)
    path = tmp_path / PERMISSIONS_RELATIVE
    assert path.exists()
    assert path in result.files
    assert result.skipped == []
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["network"] == "disabled_by_default"


def test_write_agent_permissions_is_idempotent(tmp_path: Path) -> None:
    write_agent_permissions(tmp_path)
    result = write_agent_permissions(tmp_path)
    assert result.files == []
    assert len(result.skipped) == 1


def test_write_agent_permissions_force_overwrites(tmp_path: Path) -> None:
    path = tmp_path / PERMISSIONS_RELATIVE
    write_agent_permissions(tmp_path)
    path.write_text('{"description":"hand-edited"}', encoding="utf-8")
    result = write_agent_permissions(tmp_path, force=True)
    assert path in result.files
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("network") == "disabled_by_default"


def test_cli_permissions_write_runs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["permissions", "write", "--target", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert (tmp_path / PERMISSIONS_RELATIVE).exists()
    assert "Wrote" in captured.out


def test_cli_permissions_write_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["permissions", "write", "--target", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "files" in payload
    assert len(payload["files"]) == 1
