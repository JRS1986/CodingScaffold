import json

from coding_scaffold.team import connect_team, doctor_team, preview_team, sync_team, write_team_manifest


def test_write_team_manifest_creates_non_secret_template(tmp_path) -> None:
    path = write_team_manifest(
        tmp_path,
        team="platform-api",
        knowledge_remote="https://example.test/team-knowledge.git",
        knowledge_backend="obsidian",
    )

    payload = json.loads(path.read_text())
    assert payload["team"] == "platform-api"
    assert payload["knowledge"]["backend"] == "obsidian"
    assert payload["knowledge"]["remote"] == "https://example.test/team-knowledge.git"
    assert payload["security"]["secrets_allowed"] is False


def test_connect_team_imports_shared_assets(tmp_path) -> None:
    sources = tmp_path / "sources"
    knowledge = sources / "knowledge"
    skills = sources / "skills"
    agents = sources / "agents"
    policy = sources / "policy"
    configs = sources / "configs"
    for path in [knowledge, skills, agents, policy, configs]:
        path.mkdir(parents=True)
    (knowledge / "README.md").write_text("# Team Knowledge\n", encoding="utf-8")
    (skills / "release-review.md").write_text("# Release Review\n", encoding="utf-8")
    (agents / "reviewer.md").write_text("# Reviewer\n", encoding="utf-8")
    (policy / "company.md").write_text("# Policy\n", encoding="utf-8")
    (configs / "opencode.json").write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / "team-onboarding.json"
    manifest.write_text(
        json.dumps(
            {
                "team": "platform-api",
                "knowledge": {
                    "backend": "markdown",
                    "path": ".coding-scaffold/knowledge",
                    "remote": str(knowledge),
                },
                "skills": {"remotes": [str(skills)]},
                "agents": {"remotes": [str(agents)]},
                "policy": {"remote": str(policy), "scope": "company"},
                "configs": {"remotes": [str(configs)]},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "project"

    result = connect_team(target, str(manifest))

    assert not result.warnings
    assert (target / ".coding-scaffold" / "knowledge" / "README.md").exists()
    assert (target / ".coding-scaffold" / "skills" / "release-review.md").exists()
    assert (target / ".opencode" / "agents" / "reviewer.md").exists()
    assert (target / ".coding-scaffold" / "policy" / "imported" / "company.md").exists()
    assert (target / ".coding-scaffold" / "configs" / "opencode.json").exists()
    provenance = json.loads((target / ".coding-scaffold" / "team-provenance.json").read_text())
    assert provenance["team"] == "platform-api"
    assert provenance["secrets_allowed"] is False
    assert not list((target / ".coding-scaffold" / "team").rglob(".git"))


def test_doctor_team_reports_missing_manifest(tmp_path) -> None:
    result = doctor_team(tmp_path)

    assert result.actions == []
    assert result.warnings == ["No team manifest found."]


def test_preview_team_writes_no_imports(tmp_path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "release-review.md").write_text("# Release Review\n", encoding="utf-8")
    manifest = tmp_path / "team-onboarding.json"
    manifest.write_text(
        json.dumps(
            {
                "team": "platform-api",
                "skills": {"remotes": [str(skills)]},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )
    target = tmp_path / "project"

    result = preview_team(target, str(manifest))

    assert "Would import skill" in "\n".join(result.actions)
    assert not (target / ".coding-scaffold" / "skills" / "release-review.md").exists()


def test_sync_team_reports_missing_git_for_remote(tmp_path, monkeypatch) -> None:
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "team": "platform-api",
                "knowledge": {"remote": "https://example.test/team-knowledge.git"},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("coding_scaffold.team.shutil.which", lambda name: None)

    result = sync_team(tmp_path)

    assert result.actions == []
    assert "git is required" in result.warnings[0]


def test_yaml_team_manifest_is_rejected(tmp_path) -> None:
    manifest = tmp_path / "team-onboarding.yaml"
    manifest.write_text("team: platform-api\n", encoding="utf-8")

    result = connect_team(tmp_path / "project", str(manifest))

    assert "must be JSON" in result.warnings[0]
