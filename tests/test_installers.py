from coding_scaffold.installers import install_missing_addons, install_missing_tools


def test_install_missing_tools_reports_present_tool(monkeypatch) -> None:
    monkeypatch.setattr("coding_scaffold.installers.shutil.which", lambda name: f"/usr/bin/{name}")

    results = install_missing_tools("opencode", interactive=False)

    assert results[0].status == "present"
    assert "already installed" in results[0].message


def test_install_missing_tools_reports_missing_without_prompt(monkeypatch) -> None:
    monkeypatch.setattr("coding_scaffold.installers.shutil.which", lambda name: None)

    results = install_missing_tools("openclaude", interactive=False)

    assert results[0].status == "missing"
    assert "npm install -g @gitlawb/openclaude" in results[0].message


def test_install_missing_tools_supports_hermes(monkeypatch) -> None:
    monkeypatch.setattr("coding_scaffold.installers.shutil.which", lambda name: None)

    results = install_missing_tools("hermes", interactive=False)

    assert results[0].tool == "hermes"
    assert results[0].status == "missing"
    assert "NousResearch/hermes-agent" in results[0].message


def test_install_missing_tools_supports_pi(monkeypatch) -> None:
    monkeypatch.setattr("coding_scaffold.installers.shutil.which", lambda name: None)

    results = install_missing_tools("pi", interactive=False)

    assert results[0].tool == "pi"
    assert results[0].status == "missing"
    assert "@earendil-works/pi-coding-agent" in results[0].message


def test_install_missing_tools_runs_installer_when_confirmed(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Completed:
        returncode = 0

    monkeypatch.setattr("coding_scaffold.installers.shutil.which", lambda name: None)
    monkeypatch.setattr(
        "coding_scaffold.installers.subprocess.run",
        lambda command, check, cwd=None: calls.append(command) or Completed(),
    )

    results = install_missing_tools("opencode", interactive=False, assume_yes=True)

    assert results[0].status == "installed"
    assert calls == [["bash", "-lc", "curl -fsSL https://opencode.ai/install | bash"]]


def test_install_missing_addon_reports_routellm_missing(monkeypatch) -> None:
    monkeypatch.setattr("coding_scaffold.installers.importlib.util.find_spec", lambda name: None)

    results = install_missing_addons("routellm", interactive=False)

    assert results[0].status == "missing"
    assert "routellm[serve,eval]" in results[0].message


def test_install_missing_addon_installs_open_multi_agent_in_target(tmp_path, monkeypatch) -> None:
    calls: list[tuple[list[str], object]] = []

    class Completed:
        returncode = 0

    monkeypatch.setattr(
        "coding_scaffold.installers.subprocess.run",
        lambda command, check, cwd=None: calls.append((command, cwd)) or Completed(),
    )

    results = install_missing_addons(
        "open-multi-agent",
        interactive=False,
        assume_yes=True,
        target=tmp_path,
    )

    assert results[0].status == "installed"
    assert calls == [(["npm", "install", "@jackchen_me/open-multi-agent"], tmp_path)]


def test_install_missing_addon_clones_caveman_compression(tmp_path, monkeypatch) -> None:
    calls: list[tuple[list[str], object]] = []
    removed: list[object] = []

    class Completed:
        returncode = 0

    monkeypatch.setattr(
        "coding_scaffold.installers.subprocess.run",
        lambda command, check, cwd=None: calls.append((command, cwd)) or Completed(),
    )
    monkeypatch.setattr(
        "coding_scaffold.installers.shutil.rmtree",
        lambda path, ignore_errors=False: removed.append((path, ignore_errors)),
    )

    results = install_missing_addons(
        "caveman-compression",
        interactive=False,
        assume_yes=True,
        target=tmp_path,
    )

    assert results[0].status == "installed"
    assert calls[0][0][:3] == ["git", "clone", "https://github.com/wilpel/caveman-compression.git"]
    assert calls[0][0][3] == "caveman-compression"
    assert calls[0][1] == tmp_path / ".coding-scaffold" / "tools"
    assert removed == [(tmp_path / ".coding-scaffold" / "tools" / "caveman-compression" / ".git", True)]


def test_obsidian_in_wsl_is_manual(monkeypatch) -> None:
    monkeypatch.setattr("coding_scaffold.installers.shutil.which", lambda name: None)
    monkeypatch.setattr("coding_scaffold.installers._is_wsl", lambda: True)

    results = install_missing_addons("obsidian", interactive=False)

    assert results[0].status == "manual"
    assert "desktop app" in results[0].message
