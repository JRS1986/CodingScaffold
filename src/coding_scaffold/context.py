from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MAX_CONTEXT_TOKENS = 100_000
DEFAULT_CONTEXT_WINDOW = 250_000
DEFAULT_MAX_CONTEXT_RATIO = 0.4

TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml"}
COMPRESSIBLE_SUFFIXES = {".md", ".txt"}
IGNORED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}
FILLER_WORDS = {
    "basically",
    "certainly",
    "clearly",
    "essentially",
    "generally",
    "really",
    "simply",
    "very",
}


@dataclass(frozen=True)
class ContextFile:
    path: str
    tokens_estimate: int

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "tokens_estimate": self.tokens_estimate,
        }


@dataclass(frozen=True)
class ContextBudget:
    source: str
    tokens_estimate: int
    file_count: int
    max_tokens: int
    context_window: int
    max_ratio: float
    window_ratio: float
    recommendation: str
    warnings: list[str]
    files: list[ContextFile]

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "tokens_estimate": self.tokens_estimate,
            "file_count": self.file_count,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "max_ratio": self.max_ratio,
            "window_ratio": self.window_ratio,
            "recommendation": self.recommendation,
            "warnings": self.warnings,
            "files": [file.to_dict() for file in self.files],
        }


@dataclass(frozen=True)
class CompressionResult:
    files: list[Path]
    skipped: list[Path]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "files": [str(path) for path in self.files],
            "skipped": [str(path) for path in self.skipped],
            "warnings": self.warnings,
        }


def inspect_context_budget(
    target: Path,
    source: str = "knowledge",
    max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    max_ratio: float = DEFAULT_MAX_CONTEXT_RATIO,
) -> ContextBudget:
    root = target.expanduser().resolve()
    files = [
        ContextFile(_display_path(path, root), _estimate_tokens(path.read_text(encoding="utf-8")))
        for path in _iter_source_files(root, source, TEXT_SUFFIXES)
    ]
    total = sum(file.tokens_estimate for file in files)
    window_ratio = total / context_window if context_window > 0 else 1.0
    warnings: list[str] = []
    if total > max_tokens:
        warnings.append(
            f"Estimated context is {total} tokens, above the {max_tokens} token budget."
        )
    if window_ratio > max_ratio:
        warnings.append(
            f"Estimated context uses {window_ratio:.0%} of the configured context window."
        )
    recommendation = (
        "Compress context sidecars, split retrieval by scope, or start a fresh session."
        if warnings
        else "Context budget looks healthy. Load only the files needed for the task."
    )
    return ContextBudget(
        source=source,
        tokens_estimate=total,
        file_count=len(files),
        max_tokens=max_tokens,
        context_window=context_window,
        max_ratio=max_ratio,
        window_ratio=window_ratio,
        recommendation=recommendation,
        warnings=warnings,
        files=sorted(files, key=lambda item: item.tokens_estimate, reverse=True),
    )


def compress_context(
    target: Path,
    source: str = "knowledge",
    overwrite: bool = False,
) -> CompressionResult:
    root = target.expanduser().resolve()
    written: list[Path] = []
    skipped: list[Path] = []
    warnings: list[str] = []
    for path in _iter_source_files(root, source, COMPRESSIBLE_SUFFIXES):
        if path.name.endswith(".caveman.md") or path.name.endswith(".caveman.txt"):
            continue
        output = _compressed_path(path)
        if output.exists() and not overwrite:
            skipped.append(output)
            continue
        original = path.read_text(encoding="utf-8")
        compressed = _compress_text(original)
        if _estimate_tokens(compressed) >= _estimate_tokens(original):
            warnings.append(f"Skipped {path}: compression would not reduce estimated tokens.")
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(compressed, encoding="utf-8")
        written.append(output)
    return CompressionResult(written, skipped, warnings)


def _iter_source_files(root: Path, source: str, suffixes: set[str]) -> list[Path]:
    paths = _source_paths(root, source)
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix.lower() in suffixes:
                files.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and child.suffix.lower() in suffixes and not _is_ignored(child, root):
                files.append(child)
    return sorted(files)


def _source_paths(root: Path, source: str) -> list[Path]:
    scaffold = root / ".coding-scaffold"
    if source == "knowledge":
        return [scaffold / "knowledge"]
    if source == "team":
        return [
            scaffold / "knowledge",
            scaffold / "skills",
            scaffold / "policy",
            root / ".opencode" / "agents",
        ]
    candidate = Path(source).expanduser()
    return [candidate if candidate.is_absolute() else root / candidate]


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _compress_text(text: str) -> str:
    compressed_lines: list[str] = []
    in_fence = False
    previous_blank = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_fence = not in_fence
            compressed_lines.append(line)
            previous_blank = False
            continue
        if in_fence:
            compressed_lines.append(line)
            previous_blank = False
            continue
        line = _strip_html_comments(line).strip()
        if not line:
            if not previous_blank:
                compressed_lines.append("")
            previous_blank = True
            continue
        line = _compress_sentence(line)
        compressed_lines.append(line)
        previous_blank = False
    return "\n".join(compressed_lines).strip() + "\n"


def _compress_sentence(line: str) -> str:
    prefix = ""
    body = line
    match = re.match(r"^(\s*(?:[-*]|\d+\.)\s+)(.*)$", line)
    if match:
        prefix, body = match.groups()
    body = re.sub(r"\b(in order to|it is important to|please note that)\b", "", body, flags=re.I)
    body = re.sub(r"\b(the|a|an)\b", "", body, flags=re.I)
    body = re.sub(rf"\b({'|'.join(sorted(FILLER_WORDS))})\b", "", body, flags=re.I)
    body = re.sub(r"\s+", " ", body).strip()
    return f"{prefix}{body}" if body else prefix.strip()


def _strip_html_comments(line: str) -> str:
    return re.sub(r"<!--.*?-->", "", line)


def _compressed_path(path: Path) -> Path:
    if path.suffix.lower() == ".txt":
        return path.with_name(f"{path.stem}.caveman.txt")
    return path.with_name(f"{path.stem}.caveman.md")


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return any(part in IGNORED_PARTS for part in parts)


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
