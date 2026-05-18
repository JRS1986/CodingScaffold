"""Direct unit tests for :func:`coding_scaffold.updater.refresh_scaffold`.

These tests exercise the 3-way-merge behavior of ``refresh_scaffold`` without
going through the CLI. They construct the same minimal intake/hardware/provider
fixture used by ``tests/test_writers.py`` and drive drift by mutating
``IntakeAnswers`` between calls (e.g. swapping the project language), since
``write_scaffold`` embeds those fields verbatim into a number of generated
files.

Scenario 4 (drift on a user-edited file) currently exercises a latent bug: the
``scaffold-version.json`` file always advances to the *desired* hashes even when
the on-disk content was kept as the user's version (see issue #34). The
``xfail(strict=True, ...)`` assertion documents the desired behavior and will
flip green once #34 is fixed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.hardware import HardwareProfile
from coding_scaffold.intake import IntakeAnswers
from coding_scaffold.providers import Provider
from coding_scaffold.router import RoutingPlan
from coding_scaffold.scaffold_version import SCAFFOLD_VERSION_FILE
from coding_scaffold.updater import refresh_scaffold


def _fixture(language: str = "python") -> tuple[IntakeAnswers, HardwareProfile, list[Provider], RoutingPlan]:
    """Return a deterministic intake/hardware/providers/routing fixture.

    Pass a different ``language`` between calls to produce content drift in
    the generated AGENTS.md / GETTING_STARTED.md files.
    """
    intake = IntakeAnswers(
        language=language,
        project_target="CLI",
        existing_codebase=True,
        privacy="local-first",
        tool="manual",
    )
    hardware = HardwareProfile("linux", False, 8, 32, None, None, True, ["ollama"])
    providers = [Provider("ollama", "local", True, "CLI found", "http://127.0.0.1:11434/v1")]
    routing = RoutingPlan(
        "local-first-router",
        "qwen2.5-coder:14b-instruct",
        "qwen2.5-coder:32b-instruct",
        0.1,
        "http://127.0.0.1:11434/v1",
        None,
        None,
        ["route locally"],
        {"selection_mode": "recommend"},
    )
    return intake, hardware, providers, routing


def _agents_md(root: Path) -> Path:
    return root / ".coding-scaffold" / "AGENTS.md"


def _version_file(root: Path) -> Path:
    return root / SCAFFOLD_VERSION_FILE


def _read_version_hashes(root: Path) -> dict[str, str]:
    return json.loads(_version_file(root).read_text(encoding="utf-8"))["files"]


def test_first_run_writes_everything_and_creates_version_file(tmp_path: Path) -> None:
    intake, hardware, providers, routing = _fixture()

    result = refresh_scaffold(tmp_path, intake, hardware, providers, routing)

    # Every generated file landed on disk.
    assert _agents_md(tmp_path).exists()
    assert _version_file(tmp_path).exists()
    # All non-version files appear under ``updated`` (nothing was staged or skipped).
    assert result.staged == []
    assert result.skipped == []
    # The version file is recorded in ``updated`` too.
    assert _version_file(tmp_path) in result.updated
    # And it contains hashes for the generated files (e.g. AGENTS.md).
    hashes = _read_version_hashes(tmp_path)
    assert ".coding-scaffold/AGENTS.md" in hashes
    # Warning about missing prior version is emitted.
    assert any("scaffold-version.json" in w for w in result.warnings)


def test_clean_rerun_skips_everything(tmp_path: Path) -> None:
    intake, hardware, providers, routing = _fixture()
    refresh_scaffold(tmp_path, intake, hardware, providers, routing)
    version_before = _version_file(tmp_path).read_bytes()
    agents_before = _agents_md(tmp_path).read_bytes()

    result = refresh_scaffold(tmp_path, intake, hardware, providers, routing)

    # No file should have been rewritten (other than the version file, which
    # ``refresh_scaffold`` always rewrites at the end — but with identical
    # content).
    assert result.staged == []
    assert result.skipped  # everything matched
    # No ``.new`` files were left behind.
    assert list(tmp_path.rglob("*.new")) == []
    assert list(tmp_path.rglob("*.new2")) == []
    # On-disk content unchanged.
    assert _agents_md(tmp_path).read_bytes() == agents_before
    # Version file content unchanged (same hashes, same serialization).
    assert _version_file(tmp_path).read_bytes() == version_before


def test_drift_with_unmodified_user_file_overwrites(tmp_path: Path) -> None:
    # Initial scaffold under language=python.
    intake_v1, hardware, providers, routing = _fixture(language="python")
    refresh_scaffold(tmp_path, intake_v1, hardware, providers, routing)
    agents = _agents_md(tmp_path)
    original_content = agents.read_text(encoding="utf-8")
    assert "Project language: python" in original_content
    hashes_before = _read_version_hashes(tmp_path)

    # Second run with different intake => generated content drifts. The user
    # has not touched AGENTS.md, so the previous-hash matches the current
    # on-disk hash and the updater overwrites with the new desired content.
    intake_v2, _, _, _ = _fixture(language="typescript")
    result = refresh_scaffold(tmp_path, intake_v2, hardware, providers, routing)

    new_content = agents.read_text(encoding="utf-8")
    assert "Project language: typescript" in new_content
    assert new_content != original_content
    assert agents in result.updated
    # No staging of edited user content (there was no edit).
    assert not any(str(p).endswith(".new") for p in result.staged)
    # The hash file advanced to reflect the new desired content.
    hashes_after = _read_version_hashes(tmp_path)
    assert hashes_after[".coding-scaffold/AGENTS.md"] != hashes_before[".coding-scaffold/AGENTS.md"]


def test_drift_with_user_edited_file_stages_new_keeps_user_copy(tmp_path: Path) -> None:
    intake_v1, hardware, providers, routing = _fixture(language="python")
    refresh_scaffold(tmp_path, intake_v1, hardware, providers, routing)
    agents = _agents_md(tmp_path)

    # User edits AGENTS.md locally.
    edited = agents.read_text(encoding="utf-8") + "\nLocal note from the user.\n"
    agents.write_text(edited, encoding="utf-8")

    # Second run with drifted intake.
    intake_v2, _, _, _ = _fixture(language="typescript")
    result = refresh_scaffold(tmp_path, intake_v2, hardware, providers, routing)

    # The user's edit is preserved on disk.
    assert agents.read_text(encoding="utf-8") == edited
    # A .new file holds the newly-desired content.
    new_path = agents.with_name(agents.name + ".new")
    assert new_path.exists()
    assert "Project language: typescript" in new_path.read_text(encoding="utf-8")
    assert new_path in result.staged


@pytest.mark.xfail(
    strict=True,
    reason="#34: scaffold-version.json currently advances even for files whose "
    "new content was only staged as .new (user-edited copy remained on disk).",
)
def test_drift_with_user_edited_file_does_not_advance_version_for_staged(tmp_path: Path) -> None:
    intake_v1, hardware, providers, routing = _fixture(language="python")
    refresh_scaffold(tmp_path, intake_v1, hardware, providers, routing)
    agents = _agents_md(tmp_path)
    hashes_v1 = _read_version_hashes(tmp_path)

    edited = agents.read_text(encoding="utf-8") + "\nLocal note from the user.\n"
    agents.write_text(edited, encoding="utf-8")

    intake_v2, _, _, _ = _fixture(language="typescript")
    refresh_scaffold(tmp_path, intake_v2, hardware, providers, routing)
    hashes_v2 = _read_version_hashes(tmp_path)

    # Desired behavior (will fail until #34 is fixed): because the user's
    # version of AGENTS.md was kept on disk and the new content was only
    # staged as .new, the version file's recorded hash for AGENTS.md should
    # still be the v1 hash — not the v2 hash.
    assert hashes_v2[".coding-scaffold/AGENTS.md"] == hashes_v1[".coding-scaffold/AGENTS.md"]


def test_user_accepts_staged_new_then_rerun_is_clean(tmp_path: Path) -> None:
    intake_v1, hardware, providers, routing = _fixture(language="python")
    refresh_scaffold(tmp_path, intake_v1, hardware, providers, routing)
    agents = _agents_md(tmp_path)

    # User edits the file then accepts the upstream update on a drifted run.
    edited = agents.read_text(encoding="utf-8") + "\nLocal note.\n"
    agents.write_text(edited, encoding="utf-8")

    intake_v2, _, _, _ = _fixture(language="typescript")
    refresh_scaffold(tmp_path, intake_v2, hardware, providers, routing)
    new_path = agents.with_name(agents.name + ".new")
    assert new_path.exists()

    # User accepts the staged update: mv AGENTS.md.new AGENTS.md
    new_content = new_path.read_text(encoding="utf-8")
    agents.write_text(new_content, encoding="utf-8")
    new_path.unlink()

    # A subsequent refresh with the same v2 intake should now see a clean tree.
    result = refresh_scaffold(tmp_path, intake_v2, hardware, providers, routing)

    assert result.staged == []
    # AGENTS.md should be in the skipped list (its content already matches).
    assert agents in result.skipped
    # And no new ``.new`` files were created for it.
    assert not (agents.with_name(agents.name + ".new")).exists()
    assert not (agents.with_name(agents.name + ".new2")).exists()
