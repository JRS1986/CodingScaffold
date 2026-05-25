"""Coverage for `--persona` on doctor/pilot and `coding-scaffold tour` (issues #90, #91)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.artifacts import artifact_keys
from coding_scaffold.cli import build_parser, main
from coding_scaffold.doctor import format_doctor_text, run_doctor
from coding_scaffold.personas import (
    DEFAULT_PERSONA,
    PERSONAS,
    get_persona,
    persona_keys,
)
from coding_scaffold.pilot import format_pilot_text, run_pilot
from coding_scaffold.tour import format_tour, screens


# ---------------------------------------------------------------------------
# Persona registry invariants
# ---------------------------------------------------------------------------


def test_default_persona_is_beginner() -> None:
    assert DEFAULT_PERSONA == "beginner"


def test_personas_cover_four_distinct_keys() -> None:
    assert set(persona_keys()) == {"beginner", "control", "security", "team-lead"}


@pytest.mark.parametrize("persona_key", sorted(PERSONAS))
def test_every_persona_references_known_artifacts(persona_key: str) -> None:
    persona = get_persona(persona_key)
    known = set(artifact_keys())
    unknown = set(persona.artifact_keys) - known
    assert not unknown, f"persona {persona_key!r} references unknown {unknown}"


@pytest.mark.parametrize("persona_key", sorted(PERSONAS))
def test_every_persona_recommends_at_least_one_command(persona_key: str) -> None:
    persona = get_persona(persona_key)
    assert persona.next_commands, f"persona {persona_key!r} has no recommended commands"


# ---------------------------------------------------------------------------
# Doctor honors --persona
# ---------------------------------------------------------------------------


def test_doctor_security_persona_recommends_policy_first(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, persona="security")
    assert report.persona == "security"
    first = report.next_steps[0]
    assert "policy" in first or "mcp" in first or "permissions" in first


def test_doctor_security_persona_reorders_artifacts(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, persona="security")
    # The first three artifact keys should be the security-focus ones.
    head = list(report.artifacts)[:3]
    assert set(head) <= {
        "policy_pack", "mcp_policy", "permissions_json",
    }


def test_doctor_persona_writes_persona_marker_into_notes(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, persona="team-lead")
    assert any("Persona: Team Lead" in note for note in report.notes)


def test_doctor_rejects_unknown_persona(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown persona"):
        run_doctor(tmp_path, persona="not-a-persona")


def test_doctor_default_persona_keeps_existing_behavior(tmp_path: Path) -> None:
    """Regression guard: the beginner-default path must keep the original
    recommendation logic so existing tests don't regress."""

    report = run_doctor(tmp_path)
    assert report.persona == DEFAULT_PERSONA
    assert any("pilot" in step for step in report.next_steps)


def test_doctor_cli_accepts_persona_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["doctor", "--target", str(tmp_path), "--persona", "control", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["persona"] == "control"


def test_doctor_cli_rejects_unknown_persona(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["doctor", "--target", str(tmp_path), "--persona", "wat"])


# ---------------------------------------------------------------------------
# Pilot honors --persona
# ---------------------------------------------------------------------------


def test_pilot_security_persona_substitutes_recipe(tmp_path: Path) -> None:
    report = run_pilot(tmp_path, tool="opencode", persona="security")
    assert report.persona == "security"
    # The first printed step should be a policy / permissions / mcp command,
    # not the beginner-default `setup run`.
    first = report.steps[0]
    assert any(word in first for word in ("policy", "permissions", "mcp"))


def test_pilot_team_lead_persona_recommends_team_init(tmp_path: Path) -> None:
    report = run_pilot(tmp_path, tool="opencode", persona="team-lead")
    assert any("team init" in step for step in report.steps)


def test_pilot_rejects_unknown_persona(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown persona"):
        run_pilot(tmp_path, tool="opencode", persona="bad")


def test_pilot_cli_accepts_persona_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(
        [
            "pilot",
            "--target",
            str(tmp_path),
            "--tool",
            "opencode",
            "--persona",
            "control",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["persona"] == "control"


def test_pilot_default_persona_unchanged(tmp_path: Path) -> None:
    report = run_pilot(tmp_path, tool="opencode")
    assert report.persona == DEFAULT_PERSONA
    assert len(report.steps) == 3


# ---------------------------------------------------------------------------
# Tour
# ---------------------------------------------------------------------------


def test_tour_writes_no_files(tmp_path: Path) -> None:
    format_tour(tmp_path)
    assert not list(tmp_path.iterdir()), "tour must be stateless: no files written"


def test_tour_has_five_screens() -> None:
    assert len(screens()) == 5


def test_tour_ends_with_recommended_next_command() -> None:
    text = format_tour()
    assert "coding-scaffold doctor --target ." in text


def test_tour_lists_artifact_families_with_rationale() -> None:
    text = format_tour()
    for key in artifact_keys():
        assert key in text, f"tour missing artifact {key!r}"


def test_tour_links_to_wiki_pages() -> None:
    text = format_tour()
    assert "jrs1986.github.io/CodingScaffold/wiki" in text


def test_tour_cli_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["tour", "--target", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "first 10 minutes" in out
    assert "coding-scaffold doctor" in out


# ---------------------------------------------------------------------------
# CLI parser still wires the flags
# ---------------------------------------------------------------------------


def test_parser_doctor_persona_flag() -> None:
    args = build_parser().parse_args(["doctor", "--persona", "security"])
    assert args.persona == "security"


def test_parser_pilot_persona_flag() -> None:
    args = build_parser().parse_args(
        ["pilot", "--tool", "opencode", "--persona", "control"]
    )
    assert args.persona == "control"


def test_parser_tour_subcommand_present() -> None:
    args = build_parser().parse_args(["tour"])
    assert args.command == "tour"


def test_doctor_format_text_includes_persona_label_when_set(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, persona="team-lead")
    text = format_doctor_text(report)
    assert "Team Lead" in text


def test_pilot_format_text_includes_persona_label_when_set(tmp_path: Path) -> None:
    report = run_pilot(tmp_path, tool="opencode", persona="control")
    text = format_pilot_text(report)
    assert "Control" in text
