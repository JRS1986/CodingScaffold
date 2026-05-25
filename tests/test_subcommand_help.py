"""Coverage for issue #89 (per-subcommand --help) and #92 (error message style)."""

from __future__ import annotations

import argparse
from io import StringIO

import pytest

from coding_scaffold.cli import build_parser
from coding_scaffold.cli_help import HELP_REGISTRY, doc_for
from coding_scaffold.errors import CliError, fail_with, format_error


# ---------------------------------------------------------------------------
# Subcommand --help has descriptions + examples
# ---------------------------------------------------------------------------


def _walk(parser: argparse.ArgumentParser, path: tuple[str, ...] = ()):
    yield path, parser
    for action in parser._actions:  # noqa: SLF001 — argparse has no public hook
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            for name, subparser in action.choices.items():
                yield from _walk(subparser, path + (name,))


def _visible_paths(parser: argparse.ArgumentParser) -> list[tuple[str, ...]]:
    """Subcommand paths that show up in `--help` (skip the top-level parser and
    any subparser whose help was SUPPRESS-ed)."""

    paths: list[tuple[str, ...]] = []
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            visible_top_names = {
                ca.dest
                for ca in action._choices_actions  # noqa: SLF001
                if ca.help is not argparse.SUPPRESS
            }
            for name, subparser in action.choices.items():
                if name not in visible_top_names:
                    continue
                paths.append((name,))
                for sub_path, _ in _walk(subparser, (name,)):
                    if sub_path != (name,) and sub_path not in paths:
                        paths.append(sub_path)
    return paths


def test_every_visible_subcommand_has_a_non_empty_description() -> None:
    parser = build_parser()
    for path, _ in _walk(parser):
        if not path:
            continue
        subparser = _resolve(parser, path)
        if subparser is None:
            continue
        # Hidden flat aliases inherit the canonical doc; we don't lint them.
        assert subparser.description, (
            f"subcommand path {path} has no description; add it to HELP_REGISTRY"
        )


def test_every_visible_subcommand_has_at_least_one_example() -> None:
    parser = build_parser()
    for path in _visible_paths(parser):
        subparser = _resolve(parser, path)
        if subparser is None:
            continue
        epilog = subparser.epilog or ""
        assert "Examples:" in epilog, (
            f"subcommand path {path} has no examples block; add one to HELP_REGISTRY"
        )


def test_help_registry_entries_carry_examples() -> None:
    for path, entry in HELP_REGISTRY.items():
        assert entry.description, f"{path} missing description"
        assert entry.examples, f"{path} missing examples"


def _resolve(parser: argparse.ArgumentParser, path: tuple[str, ...]):
    current = parser
    for name in path:
        sub_action = next(
            (
                a
                for a in current._actions  # noqa: SLF001
                if isinstance(a, argparse._SubParsersAction)  # noqa: SLF001
            ),
            None,
        )
        if sub_action is None or name not in sub_action.choices:
            return None
        current = sub_action.choices[name]
    return current


def test_doc_for_returns_known_entry() -> None:
    assert doc_for(("setup", "run")) is not None
    assert doc_for(("knowledge", "lint")) is not None
    assert doc_for(("does", "not", "exist")) is None


# ---------------------------------------------------------------------------
# Error helpers (#92)
# ---------------------------------------------------------------------------


def test_fail_with_renders_three_lines(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        fail_with(
            cause="thing is missing",
            next_step="run `coding-scaffold setup run`",
            link="https://example.test/wiki/Recovery",
        )
    err = capsys.readouterr().err
    assert excinfo.value.code == 1
    assert "error: thing is missing" in err
    assert "next: run `coding-scaffold setup run`" in err
    assert "see: https://example.test/wiki/Recovery" in err


def test_fail_with_without_link(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        fail_with(cause="x", next_step="y")
    err = capsys.readouterr().err
    assert "error: x" in err
    assert "next: y" in err
    assert "see:" not in err


def test_fail_with_requires_cause_and_next() -> None:
    with pytest.raises(ValueError, match="cause"):
        fail_with(cause="", next_step="do thing")
    with pytest.raises(ValueError, match="next_step"):
        fail_with(cause="something happened", next_step="")


def test_format_error_renders_clierror_payload() -> None:
    e = CliError(
        cause="missing AGENTS.md",
        next_step="run `coding-scaffold setup run --mode beginner`",
        link="https://example.test/wiki/Errors-and-Recovery",
    )
    text = format_error(e)
    assert "error: missing AGENTS.md" in text
    assert "next: run" in text
    assert "see:" in text


def test_fail_with_writes_to_provided_stream() -> None:
    """Allows tests / library callers to capture without using capsys."""

    buf = StringIO()
    with pytest.raises(SystemExit):
        fail_with(cause="x", next_step="y", stream=buf)
    assert "error: x" in buf.getvalue()
