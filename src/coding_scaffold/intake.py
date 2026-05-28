from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .context import IGNORED_PARTS
from .errors import CliError

# Canonical list of tool names the CLI accepts. Order matters for the
# argparse `choices=...` ordering shown in --help. Single source of truth:
# cli.py re-exports this as a `list[...]` for argparse and derives
# INSTALLABLE_TOOLS from it. VALID_TOOLS below is derived too.
CODING_TOOLS: tuple[str, ...] = (
    "opencode", "claude-code", "codex", "openclaude", "hermes", "pi",
    "manual",
)

DEFAULT_TOOLS: tuple[str, ...] = ("opencode",)

# Set lookup for normalize_tools' validation. Derived from CODING_TOOLS so
# the two cannot drift.
VALID_TOOLS: frozenset[str] = frozenset(CODING_TOOLS)


def normalize_tools(value: str | list[str] | None) -> list[str]:
    """Return a canonical deduped tool list from any accepted input shape.

    Accepts: None, "", "codex", "codex,claude-code", ["codex"],
    ["codex", "claude-code"], ["codex,opencode", "claude-code"].

    Raises `CliError` when `both` is passed — it was removed in 0.7.0.
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

    # `both` was removed in 0.7.0; reject every caller (CLI or library).
    if "both" in flat:
        raise CliError(
            cause="`--tool both` was removed in 0.7.0",
            next_step="use `--tool opencode,openclaude` instead",
            link="https://jrs1986.github.io/CodingScaffold/wiki/Upgrading",
        )

    # Dedupe, preserve first-seen order.
    seen: set[str] = set()
    canonical: list[str] = []
    for chunk in flat:
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
