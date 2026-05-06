from __future__ import annotations

import re
import subprocess
import sys
import tempfile
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
    prefer: str
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
            "prefer": self.prefer,
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
    prefer: str = "original",
    max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    max_ratio: float = DEFAULT_MAX_CONTEXT_RATIO,
) -> ContextBudget:
    root = target.expanduser().resolve()
    _validate_choice(prefer, {"original", "compressed", "both"}, "prefer")
    files = [
        ContextFile(_display_path(path, root), _estimate_tokens(path.read_text(encoding="utf-8")))
        for path in _iter_source_files(root, source, TEXT_SUFFIXES, prefer=prefer)
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
        prefer=prefer,
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
    engine: str = "builtin",
) -> CompressionResult:
    root = target.expanduser().resolve()
    _validate_choice(engine, {"builtin", "caveman", "auto"}, "engine")
    written: list[Path] = []
    skipped: list[Path] = []
    warnings: list[str] = []
    for path in _iter_source_files(
        root,
        source,
        COMPRESSIBLE_SUFFIXES,
        prefer="original",
        include_policy=False,
    ):
        output = _compressed_path(path)
        if output.exists() and not overwrite:
            skipped.append(output)
            continue
        original = path.read_text(encoding="utf-8")
        compressed, warning = _compress_document(root, path, original, engine)
        if warning:
            warnings.append(warning)
        if _estimate_tokens(compressed) >= _estimate_tokens(original):
            warnings.append(f"Skipped {path}: compression would not reduce estimated tokens.")
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(compressed, encoding="utf-8")
        written.append(output)
    return CompressionResult(written, skipped, warnings)


def _iter_source_files(
    root: Path,
    source: str,
    suffixes: set[str],
    prefer: str = "original",
    include_policy: bool = True,
) -> list[Path]:
    paths = _source_paths(root, source, include_policy=include_policy)
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix.lower() in suffixes and not _is_ignored(path, root):
                files.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and child.suffix.lower() in suffixes and not _is_ignored(child, root):
                files.append(child)
    return sorted(_select_preferred_files(files, prefer))


def _source_paths(root: Path, source: str, include_policy: bool = True) -> list[Path]:
    scaffold = root / ".coding-scaffold"
    if source == "knowledge":
        return [scaffold / "knowledge"]
    if source == "team":
        paths = [
            scaffold / "knowledge",
            scaffold / "skills",
            root / ".opencode" / "agents",
        ]
        if include_policy:
            paths.append(scaffold / "policy")
        return paths
    candidate = Path(source).expanduser()
    return [candidate if candidate.is_absolute() else root / candidate]


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _compress_text(text: str) -> str:
    compressed_lines: list[str] = []
    in_fence = False
    in_frontmatter = False
    previous_blank = False
    for index, raw_line in enumerate(text.splitlines()):
        if index == 0 and raw_line.strip() == "---":
            in_frontmatter = True
            compressed_lines.append(raw_line)
            previous_blank = False
            continue
        if in_frontmatter:
            compressed_lines.append(raw_line)
            if raw_line.strip() == "---":
                in_frontmatter = False
            previous_blank = False
            continue
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
        if not line:
            continue
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
    return f"{prefix}{body}" if body else ""


def _compress_document(root: Path, path: Path, text: str, engine: str) -> tuple[str, str | None]:
    if engine == "auto":
        builtin = _compress_text(text)
        external = _compress_with_caveman(root, text, path.suffix)
        if external and _estimate_tokens(external) < _estimate_tokens(builtin):
            return external, None
        return builtin, None
    if engine == "caveman":
        compressed = _compress_with_caveman(root, text, path.suffix)
        if compressed:
            return compressed, None
        return (
            _compress_text(text),
            f"Caveman Compression was not available for {path}; used built-in compressor.",
        )
    return _compress_text(text), None


def _compress_with_caveman(root: Path, text: str, suffix: str) -> str | None:
    script = root / ".coding-scaffold" / "tools" / "caveman-compression" / "caveman_compress_nlp.py"
    if not script.exists():
        return None
    frontmatter, body = _split_frontmatter(text)
    with tempfile.TemporaryDirectory() as temp:
        input_path = Path(temp) / f"input{suffix if suffix in COMPRESSIBLE_SUFFIXES else '.txt'}"
        output_path = Path(temp) / "output.txt"
        input_path.write_text(body, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(script), "compress", "-f", str(input_path), "-o", str(output_path)],
            check=False,
            cwd=script.parent,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not output_path.exists():
            return None
        compressed = output_path.read_text(encoding="utf-8").strip()
    return f"{frontmatter}{compressed}\n" if compressed else None


def _split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "".join(lines[: index + 1]), "".join(lines[index + 1 :])
    return "", text


def _strip_html_comments(line: str) -> str:
    return re.sub(r"<!--.*?-->", "", line)


def _compressed_path(path: Path) -> Path:
    if path.suffix.lower() == ".txt":
        return path.with_name(f"{path.stem}.caveman.txt")
    return path.with_name(f"{path.stem}.caveman.md")


def _select_preferred_files(files: list[Path], prefer: str) -> list[Path]:
    if prefer == "both":
        return files
    if prefer == "original":
        return [path for path in files if not _is_compressed_sidecar(path)]
    sidecars = {_original_path_for_sidecar(path): path for path in files if _is_compressed_sidecar(path)}
    selected: list[Path] = []
    for path in files:
        if _is_compressed_sidecar(path):
            selected.append(path)
        elif path not in sidecars:
            selected.append(path)
    return selected


def _is_compressed_sidecar(path: Path) -> bool:
    return path.name.endswith(".caveman.md") or path.name.endswith(".caveman.txt")


def _original_path_for_sidecar(path: Path) -> Path:
    if path.name.endswith(".caveman.md"):
        return path.with_name(f"{path.name.removesuffix('.caveman.md')}.md")
    if path.name.endswith(".caveman.txt"):
        return path.with_name(f"{path.name.removesuffix('.caveman.txt')}.txt")
    return path


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


def _validate_choice(value: str, allowed: set[str], name: str) -> None:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {choices}")
