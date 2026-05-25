import json
import subprocess

from coding_scaffold.team import (
    connect_team,
    doctor_team,
    inspect_team_doctor,
    preview_team,
    push_team,
    sync_team,
    write_team_manifest,
)


def test_write_team_manifest_creates_non_secret_template(tmp_path) -> None:
    path = write_team_manifest(
        tmp_path,
        team="platform-api",
        knowledge_remote="https://example.test/team-knowledge.git",
        knowledge_backend="obsidian",
    )

    payload = json.loads(path.read_text())
    assert payload["manifest_schema_version"] == 1
    assert payload["manifest_version"] == "1.0.0"
    assert payload["min_scaffold_version"] == "0.5.0"
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


def test_team_sync_refuses_incompatible_min_scaffold_version(tmp_path) -> None:
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "min_scaffold_version": "999.0.0",
                "team": "t",
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )

    result = sync_team(tmp_path)

    assert "requires coding-scaffold" in result.warnings[0]


def test_team_sync_writes_conflict_sidecar_for_local_skill_override(tmp_path) -> None:
    remote = tmp_path / "skills"
    remote.mkdir()
    (remote / "release.md").write_text("# Team Release\n", encoding="utf-8")
    local = tmp_path / ".coding-scaffold" / "skills"
    local.mkdir(parents=True)
    (local / "release.md").write_text("# Local Release\n", encoding="utf-8")
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.write_text(
        json.dumps(
            {
                "team": "t",
                "skills": {"remotes": [str(remote)]},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )

    result = sync_team(tmp_path, allow_local=True)

    assert any("Conflict for skill" in action for action in result.actions)
    assert (local / "release.md").read_text(encoding="utf-8") == "# Local Release\n"
    assert (local / "release.md.conflict").read_text(encoding="utf-8") == "# Team Release\n"


def test_team_sync_resolves_parent_manifest_and_refuses_allowlist_loosen(tmp_path) -> None:
    parent = tmp_path / "parent.json"
    parent.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "team": "org",
                "mcp": {"allowlist": ["filesystem", "github"]},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "extends": str(parent),
                "team": "team",
                "mcp": {"allowlist": ["filesystem", "slack"]},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )

    result = sync_team(tmp_path, allow_local=True)

    assert "cannot loosen parent mcp.allowlist" in result.warnings[0]


def test_team_push_dry_run_lists_local_artifacts(tmp_path) -> None:
    skill = tmp_path / ".coding-scaffold" / "skills" / "debug.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Debug\n", encoding="utf-8")

    result = push_team(tmp_path, dry_run=True)

    assert result.actions == ["Would nominate skills: debug.md"]


def test_team_sync_warns_and_doctor_reports_failed_pull(tmp_path, monkeypatch) -> None:
    from coding_scaffold import team as team_module

    destination = tmp_path / ".coding-scaffold" / "team" / "sources" / "knowledge" / "team-knowledge-git"
    repo = destination / "_repo" / ".git"
    repo.mkdir(parents=True)
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "team": "t",
                "knowledge": {"backend": "markdown", "remote": "https://example.test/team-knowledge.git"},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(team_module.shutil, "which", lambda name: "/usr/bin/git")

    def fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and cmd[:2] == ["git", "-C"] and "pull" in cmd:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="permission denied")
        if isinstance(cmd, list) and cmd[:2] == ["git", "-C"] and "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(team_module.subprocess, "run", fake_run)

    result = sync_team(tmp_path)

    assert any("git pull failed: permission denied" in warning for warning in result.warnings)
    provenance = json.loads((tmp_path / ".coding-scaffold" / "team-provenance.json").read_text())
    assert provenance["stale_pulls"][0]["error"] == "permission denied"
    doctor = doctor_team(tmp_path)
    assert any("Recent team source update failed" in warning for warning in doctor.warnings)


def test_team_doctor_reports_field_provenance_for_overrides(tmp_path) -> None:
    parent = tmp_path / "parent.json"
    parent.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "team": "org",
                "tools": {"default": "opencode", "required_addons": ["llmfit"]},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "extends": str(parent),
                "team": "frontend",
                "tools": {"default": "claude-code", "required_addons": ["llmfit", "routellm"]},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )

    report = inspect_team_doctor(tmp_path)

    assert report.field_provenance["tools.default"]["layer"] == "frontend"
    assert report.field_provenance["tools.required_addons"]["layer"] == "frontend"
    assert any("Effective field: tools.default = claude-code [frontend]" in action for action in report.actions)


def test_cascade_tighten_only_fields_reject_and_relax(tmp_path) -> None:
    parent = tmp_path / "parent.json"
    parent.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "team": "org",
                "mcp": {"allowlist": ["filesystem", "github"]},
                "policy": {
                    "allowed_providers": ["azure-openai", "openai"],
                    "allowed_mcp_servers": ["filesystem", "github"],
                },
                "security": {"secrets_allowed": False, "required_review_modes": ["human"]},
                "tools": {"required_addons": ["llmfit", "routellm"]},
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "extends": str(parent),
                "team": "team",
                "mcp": {"allowlist": ["filesystem", "slack"]},
                "policy": {
                    "allowed_providers": ["openai", "anthropic"],
                    "allowed_mcp_servers": ["filesystem", "slack"],
                },
                "security": {"secrets_allowed": False, "required_review_modes": ["ai"]},
                "tools": {"required_addons": ["llmfit"]},
            }
        ),
        encoding="utf-8",
    )

    result = sync_team(tmp_path, allow_local=True)

    assert "cannot loosen parent mcp.allowlist" in result.warnings[0]

    parent.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "manifest_version": "1.0.0",
                "team": "org",
                "inheritable": {
                    "mcp.allowlist": "relax",
                    "policy.allowed_providers": "relax",
                    "policy.allowed_mcp_servers": "relax",
                    "security.required_review_modes": "relax",
                    "tools.required_addons": "relax",
                },
                "mcp": {"allowlist": ["filesystem", "github"]},
                "policy": {
                    "allowed_providers": ["azure-openai", "openai"],
                    "allowed_mcp_servers": ["filesystem", "github"],
                },
                "security": {"secrets_allowed": False, "required_review_modes": ["human"]},
                "tools": {"required_addons": ["llmfit", "routellm"]},
            }
        ),
        encoding="utf-8",
    )

    relaxed = sync_team(tmp_path, allow_local=True)

    assert relaxed.warnings == []


def test_cascade_rejects_each_tighten_only_field_family(tmp_path) -> None:
    cases = [
        (
            "mcp-allowlist",
            {"mcp": {"allowlist": ["filesystem", "github"]}},
            {"mcp": {"allowlist": ["filesystem", "slack"]}},
            "mcp.allowlist",
        ),
        (
            "policy-providers",
            {"policy": {"allowed_providers": ["azure-openai", "openai"]}},
            {"policy": {"allowed_providers": ["openai", "anthropic"]}},
            "policy.allowed_providers",
        ),
        (
            "policy-mcp",
            {"policy": {"allowed_mcp_servers": ["filesystem", "github"]}},
            {"policy": {"allowed_mcp_servers": ["filesystem", "slack"]}},
            "policy.allowed_mcp_servers",
        ),
        (
            "security-review",
            {"security": {"required_review_modes": ["human", "security"]}},
            {"security": {"required_review_modes": ["human"]}},
            "security.required_review_modes",
        ),
        (
            "tools-addons",
            {"tools": {"required_addons": ["llmfit", "routellm"]}},
            {"tools": {"required_addons": ["llmfit"]}},
            "tools.required_addons",
        ),
    ]
    for name, parent_extra, child_extra, field in cases:
        root = tmp_path / name
        parent = root / "parent.json"
        parent.parent.mkdir(parents=True)
        parent_payload = {
            "manifest_schema_version": 1,
            "manifest_version": "1.0.0",
            "team": "org",
            "security": {"secrets_allowed": False},
            **parent_extra,
        }
        if "security" in parent_extra:
            parent_payload["security"] = {"secrets_allowed": False, **parent_extra["security"]}
        parent.write_text(json.dumps(parent_payload), encoding="utf-8")
        manifest = root / ".coding-scaffold" / "team-onboarding.json"
        manifest.parent.mkdir(parents=True)
        child_payload = {
            "manifest_schema_version": 1,
            "manifest_version": "1.0.0",
            "extends": str(parent),
            "team": "team",
            "security": {"secrets_allowed": False},
            **child_extra,
        }
        if "security" in child_extra:
            child_payload["security"] = {"secrets_allowed": False, **child_extra["security"]}
        manifest.write_text(json.dumps(child_payload), encoding="utf-8")

        result = sync_team(root, allow_local=True)

        assert field in result.warnings[0]


def test_team_sync_records_inbound_nominations(tmp_path) -> None:
    remote = tmp_path / "org-knowledge"
    remote.mkdir()
    (remote / "inbound-nominations.json").write_text(
        json.dumps(
            [
                {
                    "slug": "api-runbook",
                    "source_team": "platform",
                    "source_scope": "team",
                    "accepted_at": "2026-05-25T16:00:00Z",
                    "manifest_ref": "org-commit",
                }
            ]
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "team": "consumer",
                "knowledge": {"backend": "markdown", "remote": str(remote)},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )

    sync_team(tmp_path, allow_local=True)

    provenance = json.loads((tmp_path / ".coding-scaffold" / "team-provenance.json").read_text())
    assert provenance["inbound_nominations"][0]["slug"] == "api-runbook"
    doctor = doctor_team(tmp_path)
    assert any("Inbound nomination: api-runbook from platform" in action for action in doctor.actions)


def test_team_push_open_pr_falls_back_when_gh_missing(tmp_path, monkeypatch) -> None:
    skill = tmp_path / ".coding-scaffold" / "skills" / "debug.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Debug\n", encoding="utf-8")
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.write_text(
        json.dumps(
            {
                "team": "t",
                "_sync_source": {"manifest": "https://github.com/acme/manifest.git"},
                "security": {"secrets_allowed": False},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("coding_scaffold.team.shutil.which", lambda name: None)

    result = push_team(tmp_path, open_pr=True)

    assert any("Wrote nomination bundle" in action for action in result.actions)
    assert result.warnings == ["team push --open-pr requires gh on PATH; kept the outbox bundle."]
