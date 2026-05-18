from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .context import IGNORED_PARTS

_MAX_WALK_DEPTH = 4
_MAX_FILES_SCANNED = 5000
_IGNORED_DIRS = IGNORED_PARTS | {".coding-scaffold"}


@dataclass(frozen=True)
class IntakeAnswers:
    language: str | None = None
    project_target: str | None = None
    existing_codebase: bool | None = None
    privacy: str | None = None
    tool: str | None = None
    preferred_local_model: str | None = None
    mode: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def agent(self) -> str | None:
        return self.tool


def collect_intake(target: Path, provided: IntakeAnswers, interactive: bool) -> IntakeAnswers:
    detected_language = _detect_language(target) if provided.language is None else None
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
        tool=_value(
            provided.tool,
            "Coding environment / IDE (opencode/openclaude/hermes/pi/both/manual)",
            "opencode",
            interactive,
        ),
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
