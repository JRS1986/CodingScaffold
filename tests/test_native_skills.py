from __future__ import annotations

import json

import pytest

from coding_scaffold.adapters import write_tool_adapter
from coding_scaffold.cli import main
from coding_scaffold.errors import CliError
from coding_scaffold.file_ops import sha256_bytes
from coding_scaffold.skill_metadata import validate_skill_metadata
from coding_scaffold.skills import (
    SKILL_LOCATIONS,
    approve_skill,
    export_skill,
    lint_skills,
    new_skill,
)


def test_generated_codex_skills_are_inspected(tmp_path):
    write_tool_adapter(tmp_path, "codex")
    report = lint_skills(tmp_path)
    assert len(report.skills_scanned) == 2
    assert report.error_count == 0
    assert not any(f.rule.startswith("missing-") for f in report.findings)
    path = tmp_path / ".agents/skills/first-session/SKILL.md"
    path.write_text("---\nname: wrong-name\ndescription: Test.\n---\n")
    assert any(f.rule == "invalid-frontmatter" for f in lint_skills(tmp_path).findings)


@pytest.mark.parametrize("location", list(SKILL_LOCATIONS))
def test_native_skill_cli_lifecycle(tmp_path, location, capsys):
    assert (
        main(
            [
                "skills",
                "new",
                "demo",
                "--target",
                str(tmp_path),
                "--location",
                location,
                "--owner",
                "team",
            ]
        )
        == 0
    )
    assert (
        main(["skills", "approve", "demo", "--target", str(tmp_path), "--location", location]) == 0
    )
    assert (
        main(["skills", "export", "demo", "--target", str(tmp_path), "--location", location]) == 0
    )
    assert (tmp_path / "demo.tar.gz").exists()
    assert lint_skills(tmp_path).error_count == 0


@pytest.mark.parametrize("change", ["edit", "add", "delete", "rename", "executable", "reference"])
def test_full_package_approval_detects_changes(tmp_path, change):
    path = new_skill(tmp_path, "demo", owner="team").path
    helper = path / "scripts/helper.py"
    helper.write_text("print('before')\n")
    reference = path / "README.md"
    approve_skill(tmp_path, "demo")
    assert not any(f.rule == "checksum-drift" for f in lint_skills(tmp_path).findings)
    if change == "edit":
        helper.write_text("print('after')\n")
    elif change == "add":
        (path / "scripts/new.py").write_text("pass\n")
    elif change == "delete":
        helper.unlink()
    elif change == "rename":
        helper.rename(path / "scripts/renamed.py")
    elif change == "executable":
        helper.chmod(helper.stat().st_mode ^ 0o100)
    else:
        reference.write_text("Changed supporting instructions.\n")
    assert any(f.rule == "checksum-drift" for f in lint_skills(tmp_path).findings)
    approve_skill(tmp_path, "demo")
    assert not any(f.rule == "checksum-drift" for f in lint_skills(tmp_path).findings)


def test_legacy_checksum_requires_review_and_can_be_migrated(tmp_path):
    path = new_skill(tmp_path, "demo", owner="team").path
    digest = sha256_bytes(
        (path / "SKILL.md").read_bytes() + b"\0" + (path / "manifest.json").read_bytes()
    )
    (path / "CHECKSUM").write_text(digest)
    report = lint_skills(tmp_path)
    assert any(f.rule == "legacy-checksum" for f in report.findings)
    assert not any(f.rule == "checksum-drift" for f in report.findings)
    assert approve_skill(tmp_path, "demo")["checksum"].startswith("v2:")
    assert not any(f.rule == "legacy-checksum" for f in lint_skills(tmp_path).findings)


def test_native_skills_do_not_require_scaffold_manifest(tmp_path):
    path = tmp_path / ".claude/skills/demo"
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("---\nname: demo\ndescription: Run the demo.\n---\n# Demo\n")
    assert lint_skills(tmp_path).findings == []
    assert approve_skill(tmp_path, "demo", location="claude")["approved"]


def test_duplicate_names_are_distinguished_and_internal_aliases_deduplicated(tmp_path):
    first = new_skill(tmp_path, "demo", owner="team", location="agents").path
    new_skill(tmp_path, "demo", owner="team", location="opencode")
    (tmp_path / ".claude/skills").mkdir(parents=True)
    (tmp_path / ".claude/skills/demo").symlink_to(first, target_is_directory=True)
    assert lint_skills(tmp_path).skills_scanned == [".agents/skills/demo", ".opencode/skills/demo"]


def test_package_links_cannot_hide_changed_helpers(tmp_path):
    path = new_skill(tmp_path, "demo").path
    external = tmp_path / "outside.py"
    external.write_text("pass\n")
    (path / "scripts/helper.py").symlink_to(external)
    assert lint_skills(tmp_path).error_count > 0
    with pytest.raises(CliError, match="link"):
        approve_skill(tmp_path, "demo")
    with pytest.raises(CliError, match="link"):
        export_skill(tmp_path, "demo")
    assert not (tmp_path / "demo.tar.gz").exists()


def test_external_skill_directory_is_not_read(tmp_path):
    project = tmp_path / "project"
    (project / ".agents/skills").mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    (project / ".agents/skills/demo").symlink_to(external, target_is_directory=True)
    assert lint_skills(project).error_count == 1
    with pytest.raises(CliError, match="leaves"):
        new_skill(project, "demo", location="agents")


@pytest.mark.parametrize("name", [".", ".."])
def test_traversal_skill_names_rejected(tmp_path, name):
    with pytest.raises(CliError):
        new_skill(tmp_path, name)
    assert not (tmp_path / ".coding-scaffold").exists()


@pytest.mark.parametrize(
    "description",
    [
        "Run a demo.",
        '"Run a demo: with a colon."',
        "'Use the team''s demo.'",
        ">-\n  Run a demo\n  when asked.",
        "|\n  Run a demo.\n  Check its output.",
    ],
)
def test_required_frontmatter_scalar_forms(description):
    text = f"---\nname: demo\ndescription: {description}\nmetadata:\n  owner: team\n---\n"
    assert validate_skill_metadata(text, "demo") == []


@pytest.mark.parametrize(
    "frontmatter",
    [
        "name: demo",
        "name: wrong\ndescription: Demo",
        "name: demo\ndescription: []",
        "name: demo\ndescription: null",
        "name: demo\ndescription: Demo\nname: demo",
        "name: demo\ndescription: " + "x" * 1025,
    ],
)
def test_invalid_required_frontmatter(frontmatter):
    assert validate_skill_metadata(f"---\n{frontmatter}\n---\n", "demo")


def test_export_inside_package_is_rejected(tmp_path):
    path = new_skill(tmp_path, "demo").path
    with pytest.raises(CliError, match="inside"):
        export_skill(tmp_path, "demo", output=path / "self.tar.gz")


def test_native_lint_json_identifies_source(tmp_path, capsys):
    new_skill(tmp_path, "demo", owner="team", location="agents")
    assert main(["skills", "lint", "--target", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["skills_scanned"] == [".agents/skills/demo"]


@pytest.mark.parametrize(
    "description", ['"Example: demo." # comment', "'Example: demo.' # comment"]
)
def test_quoted_frontmatter_allows_yaml_comments(description):
    assert (
        validate_skill_metadata(f"---\nname: demo\ndescription: {description}\n---\n", "demo") == []
    )


def test_slug_normalization_is_shared_by_create_approve_and_export(tmp_path):
    name = "Demo_Release.v2"
    result = new_skill(tmp_path, name, owner="team")
    assert result.skill == "demo-release-v2"
    assert approve_skill(tmp_path, name)["approved"]
    assert export_skill(tmp_path, name)["exported"]
    assert lint_skills(tmp_path).error_count == 0


def test_existing_pre_standard_names_remain_addressable(tmp_path):
    result = new_skill(tmp_path, "demo", owner="team")
    legacy = result.path.with_name("demo_v1")
    result.path.rename(legacy)
    assert approve_skill(tmp_path, "demo_v1")["approved"]
    assert export_skill(tmp_path, "demo_v1")["exported"]
    assert new_skill(tmp_path, "demo_v1").path == legacy
