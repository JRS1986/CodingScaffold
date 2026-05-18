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

    result = connect_team(target, str(manifest), allow_local=True)

    assert not result.warnings
    # Knowledge lands under team/sources/knowledge/, never user-owned knowledge/.
    knowledge_sources = target / ".coding-scaffold" / "team" / "sources" / "knowledge"
    knowledge_published = list(knowledge_sources.rglob("README.md"))
    assert knowledge_published, f"expected README.md under {knowledge_sources}"
    assert (target / ".coding-scaffold" / "skills" / "release-review.md").exists()
    assert (target / ".opencode" / "agents" / "reviewer.md").exists()
    assert (target / ".coding-scaffold" / "policy" / "imported" / "company.md").exists()
    assert (target / ".coding-scaffold" / "configs" / "opencode.json").exists()
    provenance = json.loads((target / ".coding-scaffold" / "team-provenance.json").read_text())
    assert provenance["team"] == "platform-api"
    assert provenance["secrets_allowed"] is False
    # Agent-facing copies must not contain .git directories.
    for agent_dir in [
        target / ".coding-scaffold" / "skills",
        target / ".opencode" / "agents",
        target / ".coding-scaffold" / "policy" / "imported",
        target / ".coding-scaffold" / "configs",
    ]:
        assert not list(agent_dir.rglob(".git")), agent_dir


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

    result = preview_team(target, str(manifest), allow_local=True)

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


def test_team_sync_never_touches_knowledge_dir(tmp_path) -> None:
    """User-owned .coding-scaffold/knowledge/ files survive team sync."""
    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "secret-note.md").write_text("private", encoding="utf-8")

    # Manifest with a benign local-path remote (allow_local enabled).
    remote = tmp_path / "team-remote"
    remote.mkdir()
    (remote / "shared.md").write_text("shared", encoding="utf-8")
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.write_text(
        json.dumps(
            {
                "team": "t",
                "knowledge": {
                    "backend": "markdown",
                    "path": ".coding-scaffold/knowledge",
                    "remote": str(remote),
                },
            }
        ),
        encoding="utf-8",
    )

    sync_team(tmp_path, allow_local=True)

    assert (knowledge / "secret-note.md").exists()
    assert (knowledge / "secret-note.md").read_text(encoding="utf-8") == "private"


def test_team_sync_rejects_local_remote_without_allow_local(tmp_path) -> None:
    remote = tmp_path / "team-remote"
    remote.mkdir()
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "team": "t",
                "knowledge": {
                    "backend": "markdown",
                    "path": ".coding-scaffold/knowledge",
                    "remote": str(remote),
                },
            }
        ),
        encoding="utf-8",
    )

    result = sync_team(tmp_path)
    assert any(
        "allow-local" in w.lower() or "local path" in w.lower() for w in result.warnings
    )


def test_team_sync_keeps_git_directory_inside_repo_subdir(tmp_path, monkeypatch) -> None:
    """Cloned repo retains .git inside _repo so subsequent syncs can ff-pull."""
    import subprocess as _subprocess
    from pathlib import Path as _Path

    from coding_scaffold import team as team_module

    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "team": "t",
                "knowledge": {
                    "backend": "markdown",
                    "remote": "https://example.test/team-knowledge.git",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(team_module.shutil, "which", lambda name: "/usr/bin/git")

    def fake_run(cmd, *args, **kwargs):
        # Simulate `git clone <remote> <dest>` creating a _repo with .git/HEAD
        # and a sample tracked file.
        if isinstance(cmd, list) and len(cmd) >= 2 and cmd[0] == "git" and cmd[1] == "clone":
            dest = _Path(cmd[3])
            (dest / ".git").mkdir(parents=True, exist_ok=True)
            (dest / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (dest / "README.md").write_text("# Team Knowledge\n", encoding="utf-8")
            return _subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if isinstance(cmd, list) and len(cmd) >= 2 and cmd[0] == "git" and "pull" in cmd:
            return _subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return _subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(team_module.subprocess, "run", fake_run)

    result = sync_team(tmp_path)
    assert not [w for w in result.warnings if "Local path" in w], result.warnings

    knowledge_sources = tmp_path / ".coding-scaffold" / "team" / "sources" / "knowledge"
    # Find the cloned slug dir.
    slug_dirs = [p for p in knowledge_sources.iterdir() if p.is_dir()]
    assert len(slug_dirs) == 1, slug_dirs
    repo_dir = slug_dirs[0] / "_repo"
    assert (repo_dir / ".git" / "HEAD").exists(), f"missing _repo/.git/HEAD under {repo_dir}"
    # Published markdown should land at the destination root (without .git).
    assert (slug_dirs[0] / "README.md").exists()
    # Agent-readable copy must not contain .git.
    for entry in slug_dirs[0].iterdir():
        if entry.name == "_repo":
            continue
        assert entry.name != ".git"


def test_team_sync_strips_nested_git_dirs_from_agent_path(tmp_path) -> None:
    """Submodule .git directories don't leak into the agent-readable copy."""
    remote = tmp_path / "team-remote"
    remote.mkdir()
    (remote / "README.md").write_text("# Team\n", encoding="utf-8")
    # Simulate a submodule with its own .git/HEAD file.
    subrepo_git = remote / "subrepo" / ".git"
    subrepo_git.mkdir(parents=True)
    (subrepo_git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (remote / "subrepo" / "content.md").write_text("# Subrepo\n", encoding="utf-8")

    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "team": "t",
                "knowledge": {"backend": "markdown", "remote": str(remote)},
            }
        ),
        encoding="utf-8",
    )

    sync_team(tmp_path, allow_local=True)

    knowledge_sources = tmp_path / ".coding-scaffold" / "team" / "sources" / "knowledge"
    slug_dirs = [p for p in knowledge_sources.iterdir() if p.is_dir()]
    assert len(slug_dirs) == 1, slug_dirs
    destination = slug_dirs[0]
    # The published (agent-facing) copy must not contain any .git path
    # at any depth. Excluding _repo (which is allowed to keep .git for clones;
    # for local copies it won't have .git either since copytree ignores it).
    published_files = [p for p in destination.rglob("*") if "_repo" not in p.parts]
    assert not any(".git" in p.parts for p in published_files), [
        p for p in published_files if ".git" in p.parts
    ]
    # But the subrepo content (without its .git) should survive.
    assert (destination / "subrepo" / "content.md").exists()
