"""Coverage for the scaffold-version SHA256 snapshot used by `setup update` (issue #93).

Why this matters: `setup update` relies on scaffold-version.json to tell unchanged
files (safe to rewrite) from user-edited files (write a `.new` sidecar instead).
If the snapshot is wrong, either user edits silently get clobbered or perfectly
fresh files are flagged as edited.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.scaffold_version import (
    SCAFFOLD_VERSION_FILE,
    display_path,
    read_scaffold_version,
    sha256,
    write_scaffold_hashes,
    write_scaffold_version,
)


def _scaffold_file(root: Path, name: str, content: str) -> Path:
    path = root / ".coding-scaffold" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# write_scaffold_version
# ---------------------------------------------------------------------------


def test_write_scaffold_version_records_sha_for_each_file(tmp_path: Path) -> None:
    a = _scaffold_file(tmp_path, "a.json", "alpha")
    b = _scaffold_file(tmp_path, "b.md", "bravo")

    version_path = write_scaffold_version(tmp_path, [a, b])

    payload = json.loads(version_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    files = payload["files"]
    assert files[".coding-scaffold/a.json"] == sha256(b"alpha")
    assert files[".coding-scaffold/b.md"] == sha256(b"bravo")


def test_write_scaffold_version_excludes_itself(tmp_path: Path) -> None:
    """Don't snapshot the snapshot — the file would change every write."""

    a = _scaffold_file(tmp_path, "a.json", "alpha")
    version_path = tmp_path / SCAFFOLD_VERSION_FILE
    # Plant a stale snapshot the writer should overwrite without hashing.
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text("old", encoding="utf-8")

    write_scaffold_version(tmp_path, [a, version_path])

    payload = json.loads(version_path.read_text(encoding="utf-8"))
    assert SCAFFOLD_VERSION_FILE not in payload["files"]
    assert set(payload["files"]) == {".coding-scaffold/a.json"}


def test_write_scaffold_version_skips_missing_files(tmp_path: Path) -> None:
    """A file in the input list that doesn't exist on disk is silently skipped
    (matches the writer contract — input lists can include planned-but-unwritten
    files when writers short-circuit)."""

    a = _scaffold_file(tmp_path, "a.json", "alpha")
    ghost = tmp_path / ".coding-scaffold" / "ghost.json"
    write_scaffold_version(tmp_path, [a, ghost])
    payload = json.loads((tmp_path / SCAFFOLD_VERSION_FILE).read_text(encoding="utf-8"))
    assert ".coding-scaffold/ghost.json" not in payload["files"]


# ---------------------------------------------------------------------------
# read_scaffold_version + drift detection
# ---------------------------------------------------------------------------


def test_round_trip_snapshot_matches_unchanged_files(tmp_path: Path) -> None:
    a = _scaffold_file(tmp_path, "a.json", "alpha")
    write_scaffold_version(tmp_path, [a])

    snapshot = read_scaffold_version(tmp_path)
    current = sha256(a.read_bytes())
    assert snapshot[".coding-scaffold/a.json"] == current


def test_drift_detected_when_file_is_edited(tmp_path: Path) -> None:
    a = _scaffold_file(tmp_path, "a.json", "alpha")
    write_scaffold_version(tmp_path, [a])

    a.write_text("alpha-edited", encoding="utf-8")
    snapshot = read_scaffold_version(tmp_path)
    assert snapshot[".coding-scaffold/a.json"] != sha256(a.read_bytes()), (
        "drift detection broken: an edited file should not match the snapshot"
    )


def test_restoring_file_brings_back_match(tmp_path: Path) -> None:
    a = _scaffold_file(tmp_path, "a.json", "alpha")
    write_scaffold_version(tmp_path, [a])
    a.write_text("alpha-edited", encoding="utf-8")
    # User reverts; setup update should see the file as unchanged again.
    a.write_text("alpha", encoding="utf-8")
    snapshot = read_scaffold_version(tmp_path)
    assert snapshot[".coding-scaffold/a.json"] == sha256(a.read_bytes())


def test_read_scaffold_version_returns_empty_when_missing(tmp_path: Path) -> None:
    assert read_scaffold_version(tmp_path) == {}


def test_read_scaffold_version_returns_empty_on_corrupt_json(tmp_path: Path) -> None:
    target = tmp_path / SCAFFOLD_VERSION_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("not json{{{", encoding="utf-8")
    assert read_scaffold_version(tmp_path) == {}


def test_read_scaffold_version_returns_empty_when_files_key_is_wrong_type(tmp_path: Path) -> None:
    target = tmp_path / SCAFFOLD_VERSION_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"version": 1, "files": ["not", "a", "dict"]}), encoding="utf-8")
    assert read_scaffold_version(tmp_path) == {}


# ---------------------------------------------------------------------------
# write_scaffold_hashes (manual writer used by updater)
# ---------------------------------------------------------------------------


def test_write_scaffold_hashes_sorts_keys(tmp_path: Path) -> None:
    written = write_scaffold_hashes(tmp_path, {"z.md": "h-z", "a.md": "h-a"})
    payload = json.loads(written.read_text(encoding="utf-8"))
    keys = list(payload["files"])
    assert keys == sorted(keys)


def test_write_scaffold_hashes_replaces_existing_snapshot(tmp_path: Path) -> None:
    write_scaffold_hashes(tmp_path, {"a.md": "old"})
    write_scaffold_hashes(tmp_path, {"a.md": "new"})
    snapshot = read_scaffold_version(tmp_path)
    assert snapshot == {"a.md": "new"}


# ---------------------------------------------------------------------------
# display_path
# ---------------------------------------------------------------------------


def test_display_path_returns_relative_under_root(tmp_path: Path) -> None:
    p = tmp_path / "a" / "b.txt"
    p.parent.mkdir(parents=True)
    p.touch()
    assert display_path(p, tmp_path) == "a/b.txt"


def test_display_path_falls_back_to_absolute_when_outside_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outside = tmp_path / "outside.txt"
    outside.touch()
    other_root = tmp_path / "other"
    other_root.mkdir()
    result = display_path(outside, other_root)
    # Either the absolute path or the resolved relative-with-parent form is acceptable;
    # what matters is that we don't raise.
    assert result.endswith("outside.txt")


def test_sha256_helper_is_stable() -> None:
    assert sha256(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256(b"hello") == sha256(b"hello")
    assert sha256(b"hello") != sha256(b"world")
