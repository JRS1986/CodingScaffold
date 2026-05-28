"""Coverage for the canonical --tool normalizer (spec §4.3)."""

from __future__ import annotations

import pytest

from coding_scaffold.errors import CliError
from coding_scaffold.intake import (
    DEFAULT_TOOLS,
    VALID_TOOLS,
    normalize_tools,
)


def test_none_returns_default_tools() -> None:
    assert normalize_tools(None) == list(DEFAULT_TOOLS)


def test_empty_list_returns_default_tools() -> None:
    assert normalize_tools([]) == list(DEFAULT_TOOLS)


def test_single_string_returns_singleton_list() -> None:
    assert normalize_tools("codex") == ["codex"]


def test_list_of_strings_passes_through() -> None:
    assert normalize_tools(["codex", "claude-code"]) == ["codex", "claude-code"]


def test_comma_separated_string_is_split() -> None:
    assert normalize_tools("codex,claude-code") == ["codex", "claude-code"]


def test_mixed_repeats_and_commas_are_flattened() -> None:
    assert normalize_tools(["codex,opencode", "claude-code"]) == [
        "codex", "opencode", "claude-code",
    ]


def test_duplicates_are_removed_preserving_order() -> None:
    assert normalize_tools(["codex", "codex", "claude-code", "codex"]) == [
        "codex", "claude-code",
    ]


def test_manual_with_real_tool_raises_clierror() -> None:
    with pytest.raises(CliError) as excinfo:
        normalize_tools(["manual", "codex"])
    assert "manual" in excinfo.value.cause.lower()
    assert "next" in excinfo.value.next_step.lower() or "pick" in excinfo.value.next_step.lower()


def test_manual_alone_is_accepted() -> None:
    assert normalize_tools("manual") == ["manual"]


def test_whitespace_around_comma_is_trimmed() -> None:
    assert normalize_tools(" codex , claude-code ") == ["codex", "claude-code"]


def test_unknown_tool_raises_with_help_message() -> None:
    """Typos at the CLI must produce an actionable error, not a downstream crash.

    argparse `choices=` was removed from the widened surfaces so comma-separated
    values can be parsed. `normalize_tools` recovers the same early-error
    behaviour and gives a clearer recovery hint.
    """

    with pytest.raises(CliError) as excinfo:
        normalize_tools(["xodex"])
    assert "xodex" in excinfo.value.cause
    assert "unknown tool" in excinfo.value.cause.lower()
    # Recovery message names the valid choices.
    for valid in ("codex", "claude-code", "opencode"):
        assert valid in excinfo.value.next_step


def test_unknown_tool_in_mixed_list_raises_with_full_list() -> None:
    with pytest.raises(CliError) as excinfo:
        normalize_tools(["codex", "xodex", "wat"])
    # Both invalid tokens are named in the error.
    assert "xodex" in excinfo.value.cause
    assert "wat" in excinfo.value.cause


def test_valid_tools_is_derived_from_coding_tools() -> None:
    """As of v0.7.0 these are one source of truth — `VALID_TOOLS = frozenset(CODING_TOOLS)`.

    A trivial assertion, but it pins the invariant so a future refactor can't
    silently break the derivation.
    """

    from coding_scaffold.intake import CODING_TOOLS

    assert VALID_TOOLS == frozenset(CODING_TOOLS)


def test_both_raises_cli_error_for_programmatic_callers() -> None:
    """Removed in 0.7.0 — every caller (CLI or programmatic) gets a CliError.

    The `setup run --tool` surface uses ``action="append"`` *without*
    ``choices=`` (so comma-separated values like ``codex,claude-code`` parse),
    which means argparse does NOT pre-validate the token list. The rejection
    happens here, in ``normalize_tools``, for both CLI and library callers.
    """

    with pytest.raises(CliError) as excinfo:
        normalize_tools(["both"])
    assert "removed in 0.7.0" in excinfo.value.cause
    assert "opencode,openclaude" in excinfo.value.next_step
    assert "Upgrading" in (excinfo.value.link or "")
