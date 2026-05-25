"""Coverage for the file_ops helpers used by every writer module (issue #93)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.file_ops import (
    collect_json,
    collect_text,
    deep_merge_mapping,
    write_json,
    write_text,
)


# ---------------------------------------------------------------------------
# write_text
# ---------------------------------------------------------------------------


def test_write_text_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c.txt"
    write_text(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"


def test_write_text_overwrites_by_default(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    write_text(target, "first")
    write_text(target, "second")
    assert target.read_text(encoding="utf-8") == "second"


def test_write_text_skips_overwrite_when_disabled(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    write_text(target, "first")
    write_text(target, "second", overwrite=False)
    assert target.read_text(encoding="utf-8") == "first"


def test_write_text_writes_when_missing_even_with_overwrite_false(tmp_path: Path) -> None:
    target = tmp_path / "new.txt"
    write_text(target, "fresh", overwrite=False)
    assert target.read_text(encoding="utf-8") == "fresh"


def test_write_text_uses_utf8(tmp_path: Path) -> None:
    target = tmp_path / "u.txt"
    write_text(target, "héllo — café")
    raw = target.read_bytes()
    assert raw.decode("utf-8") == "héllo — café"


# ---------------------------------------------------------------------------
# write_json
# ---------------------------------------------------------------------------


def test_write_json_pretty_prints_sorted_by_default(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    write_json(target, {"b": 2, "a": 1})
    content = target.read_text(encoding="utf-8")
    # Sorted keys: "a" appears before "b".
    assert content.index('"a"') < content.index('"b"')
    # Trailing newline so files end clean.
    assert content.endswith("\n")
    # Round-trip equal.
    assert json.loads(content) == {"a": 1, "b": 2}


def test_write_json_can_disable_sort(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    write_json(target, {"b": 2, "a": 1}, sort_keys=False)
    content = target.read_text(encoding="utf-8")
    # Insertion-order preserved.
    assert content.index('"b"') < content.index('"a"')


def test_write_json_respects_overwrite_flag(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    write_json(target, {"first": True})
    write_json(target, {"second": True}, overwrite=False)
    assert json.loads(target.read_text(encoding="utf-8")) == {"first": True}


# ---------------------------------------------------------------------------
# collect_text / collect_json
# ---------------------------------------------------------------------------


def test_collect_text_appends_new_files_and_records_skips(tmp_path: Path) -> None:
    files: list[Path] = []
    skipped: list[Path] = []
    new = tmp_path / "new.md"
    existing = tmp_path / "existing.md"
    existing.write_text("keep me", encoding="utf-8")

    collect_text(files, skipped, new, "fresh content")
    collect_text(files, skipped, existing, "would clobber")

    assert files == [new]
    assert skipped == [existing]
    assert new.read_text(encoding="utf-8") == "fresh content"
    # The existing file is untouched.
    assert existing.read_text(encoding="utf-8") == "keep me"


def test_collect_text_does_not_duplicate_on_re_run(tmp_path: Path) -> None:
    """Idempotency: a second pass over the same path moves it from files to skipped."""

    files: list[Path] = []
    skipped: list[Path] = []
    target = tmp_path / "doc.md"
    collect_text(files, skipped, target, "first run")
    collect_text(files, skipped, target, "second run")
    assert target.read_text(encoding="utf-8") == "first run"
    # After two runs: the file was written once, then recorded as skipped.
    assert files == [target]
    assert skipped == [target]


def test_collect_json_writes_pretty_and_records_skips(tmp_path: Path) -> None:
    files: list[Path] = []
    skipped: list[Path] = []
    target = tmp_path / "config.json"

    collect_json(files, skipped, target, {"a": 1})
    assert files == [target]
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload == {"a": 1}

    collect_json(files, skipped, target, {"a": 2})
    assert skipped == [target]
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}


# ---------------------------------------------------------------------------
# deep_merge_mapping
# ---------------------------------------------------------------------------


def test_deep_merge_shallow_overlay_wins() -> None:
    merged = deep_merge_mapping({"a": 1, "b": 2}, {"b": 3, "c": 4})
    assert merged == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_with_deep_keys_recurses_one_level() -> None:
    base = {"settings": {"x": 1, "y": 2}, "other": "keep"}
    overlay = {"settings": {"y": 20, "z": 30}}
    merged = deep_merge_mapping(base, overlay, deep_keys=("settings",))
    assert merged == {"settings": {"x": 1, "y": 20, "z": 30}, "other": "keep"}


def test_deep_merge_falls_back_to_overlay_when_types_disagree() -> None:
    merged = deep_merge_mapping(
        {"settings": "string"},
        {"settings": {"x": 1}},
        deep_keys=("settings",),
    )
    # Base is not a mapping, so overlay wins outright.
    assert merged == {"settings": {"x": 1}}


def test_deep_merge_does_not_mutate_inputs() -> None:
    base = {"a": {"x": 1}}
    overlay = {"a": {"y": 2}}
    deep_merge_mapping(base, overlay, deep_keys=("a",))
    assert base == {"a": {"x": 1}}
    assert overlay == {"a": {"y": 2}}


def test_deep_merge_with_no_deep_keys_is_shallow() -> None:
    merged = deep_merge_mapping({"a": {"x": 1}}, {"a": {"y": 2}})
    assert merged == {"a": {"y": 2}}


# Sanity: write_json round-trips arbitrary primitives.
@pytest.mark.parametrize(
    "payload",
    [
        {"none": None, "int": 1, "float": 1.5, "bool": True, "list": [1, "two", 3.0]},
        [1, 2, 3],
        "just a string is valid JSON",
    ],
)
def test_write_json_round_trips_primitives(tmp_path: Path, payload: object) -> None:
    target = tmp_path / "x.json"
    write_json(target, payload)
    assert json.loads(target.read_text(encoding="utf-8")) == payload
