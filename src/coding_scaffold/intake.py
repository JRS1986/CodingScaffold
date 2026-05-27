from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .context import IGNORED_PARTS
from .errors import CliError

DEFAULT_TOOLS: tuple[str, ...] = ("opencode",)
# Legacy `--tool both` literal expansion. Removed in 0.7.0 alongside the value
# itself; see docs/docs/wiki/Upgrading.md.
_BOTH_EXPANSION: tuple[str, ...] = ("opencode", "openclaude")

# Canonical valid tool names. Kept in sync with `CODING_TOOLS` in cli.py
# (the CLI's argparse `choices=` list). We can't import from cli.py here
# without a circular dependency, so the list is duplicated — a test
# (`tests/test_normalize_tools.py::test_valid_tools_matches_cli_coding_tools`)
# asserts both sets stay in sync.
VALID_TOOLS: frozenset[str] = frozenset({
    "opencode", "claude-code", "codex", "openclaude", "hermes", "pi",
    "both", "manual",
})

# Single-fire deprecation warning state. Reset between tests via
# `reset_deprecation_state()`.
_BOTH_WARNING_FIRED: bool = False


def reset_deprecation_state() -> None:
    """Reset the once-per-process deprecation warning latch. Test-only."""

    global _BOTH_WARNING_FIRED
    _BOTH_WARNING_FIRED = False


def normalize_tools(value: str | list[str] | None) -> list[str]:
    """Return a canonical deduped tool list from any accepted input shape.

    Accepts: None, "", "codex", "codex,claude-code", ["codex"],
    ["codex", "claude-code"], ["codex,opencode", "claude-code"], ["both"].

    Expands the deprecated `both` literal to `opencode,openclaude` with a
    one-line stderr warning that fires at most once per process.

    Raises `CliError` when `manual` appears alongside any real tool — `manual`
    means "no adapter," which is incompatible with also picking a real one.
    """

    if value is None or value == "":
        return list(DEFAULT_TOOLS)
    if isinstance(value, str):
        raw_parts = [value]
    else:
        raw_parts = list(value)
    if not raw_parts:
        return list(DEFAULT_TOOLS)

    # Flatten commas + trim whitespace.
    # We do NOT coerce non-str elements (e.g. None) via str() — silently
    # coercing would write a tool literally named "None" into project.json.
    # The type annotation promises str; let Python raise AttributeError on
    # a non-str element instead.
    flat: list[str] = []
    for part in raw_parts:
        for chunk in part.split(","):
            chunk = chunk.strip()
            if chunk:
                flat.append(chunk)
    if not flat:
        return list(DEFAULT_TOOLS)

    # Expand `both` with a one-fire deprecation warning.
    global _BOTH_WARNING_FIRED
    expanded: list[str] = []
    for chunk in flat:
        if chunk == "both":
            if not _BOTH_WARNING_FIRED:
                print(
                    "warning: '--tool both' is deprecated; "
                    "using '--tool opencode,openclaude' instead.\n"
                    "         Will be removed in 0.7.0. "
                    "See https://jrs1986.github.io/CodingScaffold/wiki/Upgrading.",
                    file=sys.stderr,
                )
                _BOTH_WARNING_FIRED = True
            expanded.extend(_BOTH_EXPANSION)
            continue
        expanded.append(chunk)

    # Dedupe, preserve first-seen order.
    seen: set[str] = set()
    canonical: list[str] = []
    for chunk in expanded:
        if chunk in seen:
            continue
        seen.add(chunk)
        canonical.append(chunk)

    # Validate against the canonical tool set. We do this here instead of via
    # argparse `choices=` because the CLI accepts comma-separated values
    # (`--tool codex,claude-code`) which `choices=` would reject as a single
    # invalid token. Validation here catches typos the same way and gives a
    # clearer error than argparse's "invalid choice".
    invalid = [chunk for chunk in canonical if chunk not in VALID_TOOLS]
    if invalid:
        raise CliError(
            cause=f"unknown tool(s): {', '.join(repr(t) for t in invalid)}",
            next_step=(
                f"choose from: {', '.join(sorted(VALID_TOOLS))}. "
                "Multiple tools: repeat --tool or comma-separate."
            ),
            link="https://jrs1986.github.io/CodingScaffold/wiki/Glossary",
        )

    # `manual` is exclusive — it means "no adapter."
    if "manual" in canonical and len(canonical) > 1:
        others = [t for t in canonical if t != "manual"]
        raise CliError(
            cause=f"`--tool manual` excludes other tools; got manual + {', '.join(others)}",
            next_step="pick one of: `--tool manual` OR `--tool <real-tool>...`",
            link="https://jrs1986.github.io/CodingScaffold/wiki/Glossary",
        )

    return canonical

_MAX_WALK_DEPTH = 4
_MAX_FILES_SCANNED = 5000
_IGNORED_DIRS = IGNORED_PARTS | {".coding-scaffold"}


@dataclass(frozen=True)
class IntakeAnswers:
    language: str | None = None
    project_target: str | None = None
    existing_codebase: bool | None = None
    privacy: str | None = None
    tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOLS))
    preferred_local_model: str | None = None
    mode: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def agent(self) -> str | None:
        """First tool, or None if the list is empty.

        No production call site currently reads this. It is retained as a
        migration safety net for downstream library callers / external scripts
        that still expect the historical attribute name, and as a single point
        to remove when the back-compat window closes alongside `--tool both`
        in 0.7.0.
        """

        return self.tools[0] if self.tools else None


def _normalize_persisted_intake(payload: dict[str, object]) -> dict[str, object]:
    """Migrate a persisted intake payload to the canonical `tools` shape.

    Legacy `.coding-scaffold/project.json` files written before 0.6.0 carry
    `tool: "opencode"` (singular). Even older files used the `agent` alias.
    New files carry `tools: ["opencode", ...]`. Returns a payload with only
    `tools` populated; legacy `tool` and `agent` keys are stripped.

    Removed in 0.7.0 once the migration window closes; see Upgrading.md.
    """

    result = dict(payload)
    legacy_tool = result.pop("tool", None)
    legacy_agent = result.pop("agent", None)
    if "tools" in result:
        return result
    legacy = legacy_tool or legacy_agent
    if legacy:
        result["tools"] = [str(legacy)]
    else:
        result["tools"] = list(DEFAULT_TOOLS)
    return result


def collect_intake(target: Path, provided: IntakeAnswers, interactive: bool) -> IntakeAnswers:
    detected_language = _detect_language(target) if provided.language is None else None
    raw_tool_answer = _value(
        ",".join(provided.tools) if provided.tools else None,
        "Coding tools to set up (comma-separated, e.g. `codex,claude-code`)",
        "opencode",
        interactive,
    )
    return IntakeAnswers(
        language=_value(
            provided.language,
            "Primary language",
            detected_language or "python",
            interactive,
        ),
        project_target=_value(provided.project_target, "Project target", "CLI/tooling", interactive),
        existing_codebase=(
            provided.existing_codebase
            if provided.existing_codebase is not None
            else _bool_value("Existing codebase", _has_code(target), interactive)
        ),
        privacy=_value(provided.privacy, "Privacy mode", "local-first", interactive),
        tools=normalize_tools(raw_tool_answer),
        preferred_local_model=_value(
            provided.preferred_local_model,
            "Preferred local model",
            "auto",
            interactive,
        ),
        mode=_value(provided.mode, "Guidance mode", "standard", interactive),
    )


def _value(current: str | None, label: str, default: str, interactive: bool) -> str:
    if current:
        return current
    if not interactive:
        return default
    answer = input(f"{label} [{default}]: ").strip()
    return answer or default


def _bool_value(label: str, default: bool, interactive: bool) -> bool:
    if not interactive:
        return default
    default_text = "Y/n" if default else "y/N"
    answer = input(f"{label}? [{default_text}]: ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes", "true", "1"}


def _has_code(target: Path) -> bool:
    return any(path.suffix in _LANGUAGE_BY_SUFFIX for path in _iter_project_files(target))


def _detect_language(target: Path) -> str | None:
    counts: dict[str, int] = {}
    for path in _iter_project_files(target):
        if path.suffix in _LANGUAGE_BY_SUFFIX:
            language = _LANGUAGE_BY_SUFFIX[path.suffix]
            counts[language] = counts.get(language, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _iter_project_files(target: Path):
    target_path = Path(target)
    root_depth = len(target_path.parts)
    scanned = 0
    for root, dirnames, filenames in os.walk(target_path):
        root_path = Path(root)
        depth = len(root_path.parts) - root_depth
        dirnames[:] = [dirname for dirname in dirnames if dirname not in _IGNORED_DIRS]
        if depth >= _MAX_WALK_DEPTH:
            dirnames[:] = []
        for filename in filenames:
            if scanned >= _MAX_FILES_SCANNED:
                return
            scanned += 1
            yield root_path / filename


_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".rb": "ruby",
    ".php": "php",
}
