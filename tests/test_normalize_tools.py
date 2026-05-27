"""Coverage for the canonical --tool normalizer (spec §4.3)."""

from __future__ import annotations

import pytest

from coding_scaffold.errors import CliError
from coding_scaffold.intake import (
    DEFAULT_TOOLS,
    VALID_TOOLS,
    normalize_tools,
    reset_deprecation_state,
)


@pytest.fixture(autouse=True)
def _reset_deprecation():
    # The "both" warning only fires once per process; reset between tests.
    reset_deprecation_state()
    yield
    reset_deprecation_state()


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


def test_both_expands_to_opencode_openclaude_and_warns(capsys: pytest.CaptureFixture[str]) -> None:
    result = normalize_tools(["both"])
    assert result == ["opencode", "openclaude"]
    err = capsys.readouterr().err
    assert "deprecated" in err.lower()
    assert "0.7.0" in err
    assert "opencode,openclaude" in err


def test_both_deprecation_warning_fires_once_per_process(
    capsys: pytest.CaptureFixture[str],
) -> None:
    normalize_tools(["both"])
    normalize_tools(["both"])
    err = capsys.readouterr().err
    assert err.count("deprecated") == 1


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
