"""Shared CLI error helpers (issue #92).

Every CLI failure path should pass through ``fail_with`` so the user sees:

    error: <cause>
      next: <one concrete recovery step>
      see: <optional wiki link>

…and the process exits with a non-zero status. The format is deliberately three
lines because experienced devs want the cause first, the fix second, and the
documentation pointer optional.

Use ``CliError`` if you need to bubble the same payload up through library code
before the CLI surface — handlers in ``cli.py`` catch it and route through
``fail_with``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass
class CliError(Exception):
    """Library-side counterpart of ``fail_with`` so non-CLI callers can raise the
    same recovery shape and let the CLI render it.

    Deliberately not ``frozen=True``: Python's re-raise machinery (e.g.
    ``contextlib``'s ``__exit__``) assigns ``__traceback__`` on the exception
    object, which a frozen dataclass rejects with ``FrozenInstanceError``."""

    cause: str
    next_step: str
    link: str | None = None
    exit_code: int = 1

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.cause


def fail_with(
    cause: str,
    next_step: str,
    link: str | None = None,
    *,
    exit_code: int = 1,
    stream=None,
) -> None:
    """Print a three-line error block to stderr and ``sys.exit(exit_code)``.

    ``cause`` and ``next_step`` are required so we never ship a silent exit and
    never ship an error without a recovery hint. ``link`` is optional but
    recommended when a wiki page explains the failure mode.
    """

    if not cause:
        raise ValueError("fail_with: 'cause' is required so the user knows what went wrong")
    if not next_step:
        raise ValueError(
            "fail_with: 'next_step' is required so the user knows how to recover"
        )

    out = stream or sys.stderr
    print(f"error: {cause}", file=out)
    print(f"  next: {next_step}", file=out)
    if link:
        print(f"  see: {link}", file=out)
    sys.exit(exit_code)


def format_error(error: CliError) -> str:
    """Render a CliError without exiting — for tests and library callers."""

    lines = [f"error: {error.cause}", f"  next: {error.next_step}"]
    if error.link:
        lines.append(f"  see: {error.link}")
    return "\n".join(lines)
