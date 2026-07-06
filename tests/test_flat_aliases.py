"""Deprecated flat aliases: still work, warn on use, and cannot drift from the
canonical grouped commands (issue #48). The aliases are scheduled for removal
in 0.9.0; these tests keep them honest until then."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from coding_scaffold.cli import _FLAT_ALIAS_CANONICAL, build_parser, main
from coding_scaffold.cli_stability import COMMAND_STABILITY


def _subparser_map(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def _resolve(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> argparse.ArgumentParser:
    current = parser
    for name in path:
        current = _subparser_map(current)[name]
    return current


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    return {
        option
        for action in parser._actions
        for option in action.option_strings
        if option != "--help" and option != "-h"
    }


@pytest.mark.parametrize("alias", sorted(_FLAT_ALIAS_CANONICAL))
def test_flat_alias_accepts_same_flags_as_canonical(alias: str) -> None:
    """Drift guard: every hidden flat alias must expose exactly the option set
    of its canonical grouped command. Both are built from the same
    _add_*_args helper, so a mismatch means someone re-inlined arguments."""

    parser = build_parser()
    alias_parser = _resolve(parser, (alias,))
    canonical_parser = _resolve(parser, _FLAT_ALIAS_CANONICAL[alias])
    assert _option_strings(alias_parser) == _option_strings(canonical_parser), (
        f"alias {alias!r} drifted from {' '.join(_FLAT_ALIAS_CANONICAL[alias])!r}"
    )


@pytest.mark.parametrize("alias", sorted(_FLAT_ALIAS_CANONICAL))
def test_flat_alias_is_marked_deprecated(alias: str) -> None:
    assert COMMAND_STABILITY[alias] == "deprecated"


def test_flat_alias_warns_on_use(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["knowledge", "create", "--target", str(tmp_path), "--adapter", "none"])
    capsys.readouterr()
    rc = main(["knowledge-status", "--target", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 0
    assert "deprecated alias" in err
    assert "coding-scaffold knowledge status" in err
    assert "0.9.0" in err


def test_grouped_command_does_not_warn(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["knowledge", "create", "--target", str(tmp_path), "--adapter", "none"])
    capsys.readouterr()
    rc = main(["knowledge", "status", "--target", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 0
    assert "deprecated alias" not in err
