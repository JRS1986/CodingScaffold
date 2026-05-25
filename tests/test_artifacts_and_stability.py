"""Coverage for the artifact registry, doctor rationale lines, Glossary, and the
CLI stability markers (issues #87, #88, #95)."""

from __future__ import annotations

from pathlib import Path

import pytest

from coding_scaffold.artifacts import (
    ARTIFACTS,
    artifact_keys,
    get_artifact,
    rationale_for,
)
from coding_scaffold.cli import build_parser
from coding_scaffold.cli_stability import (
    COMMAND_STABILITY,
    STABILITY_LEVELS,
    marker_for,
)
from coding_scaffold.doctor import format_doctor_text, run_doctor


# ---------------------------------------------------------------------------
# Artifact registry
# ---------------------------------------------------------------------------


def test_artifact_keys_match_doctor_survey(tmp_path: Path) -> None:
    """Doctor's artifact dict must enumerate exactly the registry."""

    report = run_doctor(tmp_path)
    assert tuple(report.artifacts) == artifact_keys()


def test_every_artifact_has_a_short_rationale() -> None:
    for artifact in ARTIFACTS:
        assert artifact.why, f"artifact {artifact.key!r} missing rationale"
        # Hard limit enforced in __post_init__; double-check here too.
        assert len(artifact.why) <= 100


def test_rationale_lookup_round_trip() -> None:
    for artifact in ARTIFACTS:
        assert rationale_for(artifact.key) == artifact.why
        assert get_artifact(artifact.key) is artifact


# ---------------------------------------------------------------------------
# Doctor output renders rationale + glossary link
# ---------------------------------------------------------------------------


def test_doctor_renders_rationale_for_each_artifact(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)
    text = format_doctor_text(report)
    for artifact in ARTIFACTS:
        # The arrow + rationale appears on the same line as the artifact key.
        line = next(
            (raw for raw in text.splitlines() if artifact.key in raw and "->" in raw),
            None,
        )
        assert line is not None, (
            f"doctor output missing rationale line for {artifact.key!r}"
        )
        assert artifact.why in line


def test_doctor_renders_glossary_link(tmp_path: Path) -> None:
    text = format_doctor_text(run_doctor(tmp_path))
    assert "Glossary" in text
    assert "Glossary" in text


# ---------------------------------------------------------------------------
# Glossary file exists + is linked from the wiki index and CLI help
# ---------------------------------------------------------------------------


def test_glossary_page_exists_and_lists_core_terms() -> None:
    root = Path(__file__).resolve().parent.parent
    glossary = root / "docs" / "docs" / "wiki" / "Glossary.md"
    assert glossary.exists(), "wiki Glossary.md is the cheapest new-dev win; ship it"
    text = glossary.read_text(encoding="utf-8")
    # Required terms — every word a doctor user will see in output.
    for term in (
        "adapter",
        "artifact",
        "context",
        "doctor",
        "eval",
        "knowledge base",
        "MCP",
        "memory",
        "persona",
        "pilot",
        "policy pack",
        "provider",
        "scaffold version",
        "session trace",
        "skill",
        "stability marker",
        "team manifest",
        "weak model",
        "strong model",
    ):
        assert term.lower() in text.lower(), f"Glossary missing required term: {term!r}"


def test_top_level_help_links_glossary_and_stability() -> None:
    text = build_parser().format_help()
    assert "Glossary" in text
    assert "Stability" in text


# ---------------------------------------------------------------------------
# Stability markers
# ---------------------------------------------------------------------------


def test_stability_levels_are_a_known_set() -> None:
    for command, level in COMMAND_STABILITY.items():
        assert level in STABILITY_LEVELS, (
            f"command {command!r} has unknown stability {level!r}"
        )


def test_marker_for_known_command_round_trips() -> None:
    for command, level in COMMAND_STABILITY.items():
        assert marker_for(command) == f"[{level}]"


def test_every_visible_top_level_command_has_a_stability_entry() -> None:
    """Every command rendered in `--help` must carry a marker.

    Catches the common omission of forgetting to update `cli_stability.py` when
    adding a new top-level command.
    """

    parser = build_parser()
    # The single subparsers action sits as the only positional. Walk it.
    sub_action = next(
        action
        for action in parser._actions  # noqa: SLF001 — argparse has no public hook
        if isinstance(action.choices, dict) and action.choices
    )
    visible = [
        name
        for name, sub in sub_action.choices.items()
        if any(
            ca.dest == name and ca.help and ca.help != "==SUPPRESS=="
            for ca in sub_action._choices_actions  # noqa: SLF001
        )
    ]
    for command in visible:
        assert command in COMMAND_STABILITY, (
            f"command {command!r} appears in --help but has no entry in "
            "src/coding_scaffold/cli_stability.py"
        )


def test_top_level_help_renders_stability_markers() -> None:
    text = build_parser().format_help()
    # At least one of each marker level appears in the rendered help.
    assert "[stable]" in text
    assert "[preview]" in text


@pytest.mark.parametrize("command", sorted(COMMAND_STABILITY))
def test_each_marker_is_one_of_three_levels(command: str) -> None:
    assert COMMAND_STABILITY[command] in STABILITY_LEVELS
