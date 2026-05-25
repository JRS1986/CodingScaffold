"""Coverage for `setup update` version pinning + .new reconciliation output (issue #96)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold import __version__
from coding_scaffold.cli import main
from coding_scaffold.scaffold_version import (
    SCAFFOLD_VERSION_FILE,
    compare_versions,
    read_min_supported_version,
    write_scaffold_hashes,
    write_scaffold_version,
)


# ---------------------------------------------------------------------------
# Snapshot now carries min_supported_scaffold_version
# ---------------------------------------------------------------------------


def test_write_scaffold_version_records_min_supported(tmp_path: Path) -> None:
    a = tmp_path / ".coding-scaffold" / "a.json"
    a.parent.mkdir(parents=True)
    a.write_text("x", encoding="utf-8")
    write_scaffold_version(tmp_path, [a])

    payload = json.loads((tmp_path / SCAFFOLD_VERSION_FILE).read_text(encoding="utf-8"))
    assert payload["min_supported_scaffold_version"] == __version__


def test_write_scaffold_hashes_records_min_supported(tmp_path: Path) -> None:
    write_scaffold_hashes(tmp_path, {"a.md": "h"})
    payload = json.loads((tmp_path / SCAFFOLD_VERSION_FILE).read_text(encoding="utf-8"))
    assert payload["min_supported_scaffold_version"] == __version__


def test_read_min_supported_version_returns_none_when_missing(tmp_path: Path) -> None:
    assert read_min_supported_version(tmp_path) is None


def test_read_min_supported_version_returns_value_when_present(tmp_path: Path) -> None:
    target = tmp_path / SCAFFOLD_VERSION_FILE
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"version": 1, "min_supported_scaffold_version": "99.0.0", "files": {}}),
        encoding="utf-8",
    )
    assert read_min_supported_version(tmp_path) == "99.0.0"


def test_read_min_supported_version_tolerates_corrupt_json(tmp_path: Path) -> None:
    target = tmp_path / SCAFFOLD_VERSION_FILE
    target.parent.mkdir(parents=True)
    target.write_text("not json{{", encoding="utf-8")
    assert read_min_supported_version(tmp_path) is None


# ---------------------------------------------------------------------------
# compare_versions semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("0.5.0", "0.5.0", 0),
        ("0.5.0", "0.5.1", -1),
        ("0.5.1", "0.5.0", 1),
        ("0.5", "0.5.0", -1),  # short version sorts before its longer expansion
        ("1.0.0", "0.9.99", 1),
        ("0.5.1.dev0", "0.5.1", 1),  # dev suffix sorts after release per str compare
    ],
)
def test_compare_versions_orders_correctly(a: str, b: str, expected: int) -> None:
    result = compare_versions(a, b)
    assert (result, result == 0, result > 0) == (expected, expected == 0, expected > 0)


# ---------------------------------------------------------------------------
# setup update refuses to run on incompatible snapshot
# ---------------------------------------------------------------------------


def _plant_min_supported(root: Path, version: str) -> None:
    target = root / SCAFFOLD_VERSION_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"version": 1, "min_supported_scaffold_version": version, "files": {}}),
        encoding="utf-8",
    )


def test_setup_update_refuses_when_installed_is_older(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _plant_min_supported(tmp_path, "99.99.99")
    rc = main(["setup", "update", "--target", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "99.99.99" in err
    assert "next:" in err
    assert "Upgrading" in err


def test_setup_update_force_flag_bypasses_compatibility(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--force lets the user override the compatibility refusal.

    We can't run the full refresh in a tmp_path without a fully-wired project,
    so we only assert the gate is bypassed (the run proceeds past the refusal
    and either succeeds or fails for downstream reasons).
    """

    _plant_min_supported(tmp_path, "99.99.99")
    rc = main(["setup", "update", "--target", str(tmp_path), "--force"])
    err = capsys.readouterr().err
    # The compatibility refusal message should NOT appear.
    assert "but " not in err or "99.99.99" not in err, (
        "compatibility refusal should be bypassed with --force"
    )
    # Whatever downstream rc we get, the gate didn't refuse.
    assert rc in (0, 1)  # don't pin to a single rc — depends on intake/providers


def test_setup_update_runs_when_installed_matches_or_newer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Snapshot with min_supported == installed version should pass the gate."""

    _plant_min_supported(tmp_path, __version__)
    # We don't assert success of the full refresh (it needs an intake); only
    # that we don't get the compatibility refusal exit.
    rc = main(["setup", "update", "--target", str(tmp_path)])
    err = capsys.readouterr().err
    assert "but " + __version__ + " is installed" not in err


def test_setup_update_runs_when_snapshot_predates_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Legacy snapshots without min_supported_scaffold_version don't get refused."""

    target = tmp_path / SCAFFOLD_VERSION_FILE
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"version": 1, "files": {}}), encoding="utf-8")
    rc = main(["setup", "update", "--target", str(tmp_path)])
    err = capsys.readouterr().err
    assert "but" not in err or "is installed" not in err
    assert rc in (0, 1)


# ---------------------------------------------------------------------------
# Wiki page exists
# ---------------------------------------------------------------------------


def test_upgrading_wiki_page_exists_and_covers_required_topics() -> None:
    root = Path(__file__).resolve().parent.parent
    page = root / "docs" / "docs" / "wiki" / "Upgrading.md"
    assert page.exists(), "Upgrading.md is the upgrade contract; it must exist"
    text = page.read_text(encoding="utf-8")
    for topic in (
        ".new",
        "rollback",
        "min_supported_scaffold_version",
        "breaking",
        "CHANGELOG",
        "diff -u",
    ):
        assert topic.lower() in text.lower(), f"Upgrading.md missing topic: {topic!r}"


def test_upgrading_wiki_linked_from_meta_json() -> None:
    root = Path(__file__).resolve().parent.parent
    meta = json.loads(
        (root / "docs" / "docs" / "wiki" / "_meta.json").read_text(encoding="utf-8")
    )
    assert "Upgrading" in meta
