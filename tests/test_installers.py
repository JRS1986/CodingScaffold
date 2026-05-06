from coding_scaffold.installers import install_missing_tools


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


def test_install_missing_tools_runs_installer_when_confirmed(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Completed:
        returncode = 0

    monkeypatch.setattr("coding_scaffold.installers.shutil.which", lambda name: None)
    monkeypatch.setattr(
        "coding_scaffold.installers.subprocess.run",
        lambda command, check: calls.append(command) or Completed(),
    )

    results = install_missing_tools("opencode", interactive=False, assume_yes=True)

    assert results[0].status == "installed"
    assert calls == [["bash", "-lc", "curl -fsSL https://opencode.ai/install | bash"]]
