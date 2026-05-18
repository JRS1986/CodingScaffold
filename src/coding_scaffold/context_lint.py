"""Deterministic linter for agent-context files (AGENTS.md, CLAUDE.md, llms.txt, etc.).

The checker is purely heuristic — no LLM calls, no network, no model assumptions. Its job is
to flag rules that are vague, duplicated, contradictory, beginner-hostile, or unverifiable, and
to surface obviously-missing build/test commands. All output is deterministic so the checks can
be golden-tested.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


# Files we scan by default. Each entry is a path relative to the project root.
DEFAULT_CONTEXT_PATHS: tuple[str, ...] = (
    "AGENTS.md",
    "CLAUDE.md",
    "llms.txt",
    ".coding-scaffold/AGENTS.md",
    ".coding-scaffold/TOOLS.md",
    ".coding-scaffold/CREDENTIALS.md",
    ".coding-scaffold/KNOWLEDGE.md",
    ".coding-scaffold/ORCHESTRATION.md",
    ".coding-scaffold/SKILLS.md",
    ".coding-scaffold/GETTING_STARTED.md",
    ".coding-scaffold/FIRST_SESSION.md",
)

# Thresholds. Tunable in one place — keep heuristic, not magic.
EXCESSIVE_TOKEN_BUDGET = 2000
EXCESSIVE_CHAR_BUDGET = 8000
MIN_DUPLICATE_RULE_WORDS = 4
DUPLICATE_SIMILARITY_THRESHOLD = 0.85

# Words that flag vague, non-verifiable directives when used as the headline rule.
VAGUE_QUALITY_WORDS = (
    "clean",
    "good",
    "best practice",
    "best practices",
    "quality",
    "appropriate",
    "reasonable",
    "professional",
    "elegant",
    "idiomatic",
    "robust",
    "modern",
    "well-structured",
    "well structured",
    "well-designed",
    "well designed",
)

# Tokens that indicate the rule does cite a verifier (so it's not vague).
VERIFICATION_TOKENS = (
    "pytest",
    "ruff",
    "mypy",
    "pyright",
    "black",
    "npm test",
    "npm run",
    "yarn test",
    "pnpm test",
    "cargo test",
    "cargo check",
    "go test",
    "go vet",
    "make test",
    "make lint",
    "ctest",
    "tox",
    "jest",
    "vitest",
    "playwright",
    "cypress",
    "rspec",
    "phpunit",
    "eslint",
    "prettier",
    "shellcheck",
    "verify",
    "validates",
    "passes",
    "exits with",
    "returns 0",
    "must succeed",
    "ci",
    "ci check",
)

# Contradictory rule pairs. Each entry is (pattern_a, pattern_b, label).
# Matched on normalized line text; case-insensitive. Heuristic — small curated set.
CONTRADICTION_PAIRS: tuple[tuple[str, str, str], ...] = (
    (r"always run (the )?tests?", r"(skip|do not run) (the )?tests?", "always-vs-skip-tests"),
    (r"\buse yarn\b", r"\buse npm\b", "yarn-vs-npm"),
    (r"\buse pnpm\b", r"\buse npm\b", "pnpm-vs-npm"),
    (r"\bauto[- ]commit\b", r"never commit", "auto-commit-vs-no-commit"),
    (r"never push", r"\bauto[- ]push\b", "auto-push-vs-no-push"),
    (r"always ask before editing", r"edit (without|w/o) (asking|approval)", "ask-vs-no-ask"),
    (r"do not write tests", r"always write tests", "tests-required-vs-forbidden"),
)

# Patterns that look like dangerous shell guidance baked into agent instructions.
DANGEROUS_RECOMMENDATIONS: tuple[tuple[str, str], ...] = (
    (r"\brm\s+-rf\s+/(\s|$)", "recommends `rm -rf /`"),
    (r"\bchmod\s+777\b", "recommends `chmod 777`"),
    (r"\bsudo\s+rm\b", "recommends `sudo rm`"),
    (r"--no-verify", "recommends bypassing git hooks with --no-verify"),
    (r"git\s+push\s+--force(\s+--no-lease)?", "recommends force-push without lease"),
    (r"curl\s+[^|]+\|\s*(sudo\s+)?(sh|bash)", "recommends piping curl directly to a shell"),
    (r"disable.*\b(tls|ssl|certificate)\b", "recommends disabling TLS/SSL/cert checks"),
)

# Project-type detection: file -> "(tool, expected_command_hint)".
PROJECT_SIGNALS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("pyproject.toml", "Python", ("pytest", "tox", "ruff", "uv run pytest", "python -m pytest")),
    ("package.json", "Node", ("npm test", "yarn test", "pnpm test", "jest", "vitest")),
    ("Cargo.toml", "Rust", ("cargo test", "cargo check")),
    ("go.mod", "Go", ("go test", "go vet")),
    ("Gemfile", "Ruby", ("rspec", "bundle exec test")),
    ("composer.json", "PHP", ("phpunit", "composer test")),
    ("CMakeLists.txt", "C/C++ (CMake)", ("ctest", "make test")),
)

# Advanced concepts that beginner-mode instructions should not lead with.
ADVANCED_CONCEPTS: tuple[str, ...] = (
    "mcp",
    "model context protocol",
    "multi-agent",
    "subagent",
    "orchestration",
    "routellm",
    "hooks",
    "plugin",
    "vector database",
    "embeddings",
    "fine-tune",
    "fine tuning",
)

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class LintFinding:
    """One actionable finding from the context linter."""

    severity: str  # "error" | "warning" | "info"
    rule: str  # short stable identifier, e.g. "vague-rule"
    file: str  # path relative to the project root
    line: int | None  # 1-based; None when the finding is file-level
    message: str
    suggested_fix: str

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True)
class LintReport:
    findings: list[LintFinding] = field(default_factory=list)
    scanned_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "info")

    def to_dict(self) -> dict[str, object]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "scanned_files": list(self.scanned_files),
            "skipped_files": list(self.skipped_files),
            "warnings": list(self.warnings),
            "counts": {
                "error": self.error_count,
                "warning": self.warning_count,
                "info": self.info_count,
            },
        }


def lint_context(target: Path, paths: Iterable[str] | None = None) -> LintReport:
    """Run the context linter against the given project root.

    Args:
        target: project root.
        paths: optional iterable of paths (relative to ``target``) to lint. When ``None`` the
            default agent-context file list is used.
    """

    root = target.expanduser().resolve()
    candidate_paths = list(paths) if paths is not None else list(DEFAULT_CONTEXT_PATHS)

    scanned: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []
    findings: list[LintFinding] = []
    file_payloads: list[tuple[str, str, list[str]]] = []  # (rel_path, text, normalized_lines)

    for rel_path in candidate_paths:
        full = root / rel_path
        if not full.exists():
            skipped.append(rel_path)
            continue
        try:
            text = full.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            warnings.append(f"Could not read {rel_path}: {exc}")
            continue
        scanned.append(rel_path)
        file_payloads.append((rel_path, text, _normalized_lines(text)))

    project_type = _detect_project_type(root)

    # Per-file checks.
    for rel_path, text, normalized in file_payloads:
        findings.extend(_check_excessive_length(rel_path, text))
        findings.extend(_check_dangerous_recommendations(rel_path, text))
        findings.extend(_check_vague_rules(rel_path, text))
        findings.extend(_check_contradictions(rel_path, text))
        findings.extend(_check_advanced_concepts_without_basics(rel_path, text, normalized))

    # Cross-file checks.
    findings.extend(_check_duplicates_across_files(file_payloads))
    findings.extend(_check_missing_build_test_commands(file_payloads, project_type))
    findings.extend(_check_tooling_conflicts(file_payloads, root))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file, f.line or 0, f.rule))

    return LintReport(
        findings=findings,
        scanned_files=scanned,
        skipped_files=skipped,
        warnings=warnings,
    )


def explain_context(target: Path, paths: Iterable[str] | None = None) -> dict[str, object]:
    """Return a deterministic summary of the agent-context surface.

    Counts rules per file, surfaces detected verification tokens, and reports the project type
    the linter would assume.  Useful for ``coding-scaffold context explain`` output and for
    debugging the linter's view of the repo.
    """

    root = target.expanduser().resolve()
    candidate_paths = list(paths) if paths is not None else list(DEFAULT_CONTEXT_PATHS)
    project_type = _detect_project_type(root)

    files: list[dict[str, object]] = []
    for rel_path in candidate_paths:
        full = root / rel_path
        if not full.exists():
            continue
        try:
            text = full.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        rule_lines = _normalized_lines(text)
        verification_hits = sorted({token for token in VERIFICATION_TOKENS if token in text.lower()})
        files.append({
            "file": rel_path,
            "chars": len(text),
            "lines": text.count("\n") + (0 if text.endswith("\n") else 1),
            "approx_tokens": _approx_tokens(text),
            "rule_lines": len(rule_lines),
            "verification_tokens": verification_hits,
            "mentions_advanced_concepts": sorted({c for c in ADVANCED_CONCEPTS if c in text.lower()}),
        })

    totals = {
        "files": len(files),
        "chars": sum(int(f["chars"]) for f in files),
        "approx_tokens": sum(int(f["approx_tokens"]) for f in files),
        "rule_lines": sum(int(f["rule_lines"]) for f in files),
    }
    return {
        "project_type": project_type[0] if project_type else None,
        "files": files,
        "totals": totals,
    }


# ---------------------------------------------------------------------------
# Per-file checks
# ---------------------------------------------------------------------------


def _check_excessive_length(rel_path: str, text: str) -> list[LintFinding]:
    tokens = _approx_tokens(text)
    chars = len(text)
    if tokens <= EXCESSIVE_TOKEN_BUDGET and chars <= EXCESSIVE_CHAR_BUDGET:
        return []
    return [
        LintFinding(
            severity="warning",
            rule="excessive-length",
            file=rel_path,
            line=None,
            message=(
                f"Context length ~{tokens} tokens ({chars} chars) exceeds the recommended budget "
                f"of {EXCESSIVE_TOKEN_BUDGET} tokens."
            ),
            suggested_fix=(
                "Move long sections into linked docs (docs/wiki/, knowledge/wiki/) and keep the "
                "agent-context file focused on rules, commands, and project-specific norms."
            ),
        ),
    ]


def _check_dangerous_recommendations(rel_path: str, text: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        # Skip fenced code-block content — examples inside fences are not "recommendations".
        # Heuristic: this is a single-line scan; we don't try to track fence state perfectly.
        for pattern, label in DANGEROUS_RECOMMENDATIONS:
            if re.search(pattern, raw_line, flags=re.IGNORECASE):
                findings.append(LintFinding(
                    severity="error",
                    rule="dangerous-recommendation",
                    file=rel_path,
                    line=lineno,
                    message=f"Line {label}.",
                    suggested_fix=(
                        "Replace with a narrower, reviewable instruction or remove. Agent "
                        "instructions should not normalize destructive defaults."
                    ),
                ))
    return findings


def _check_vague_rules(rel_path: str, text: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or not _looks_like_rule(line):
            continue
        lower = line.lower()
        if not any(word in lower for word in VAGUE_QUALITY_WORDS):
            continue
        # If the line itself names a verifier, it's not vague.
        if any(token in lower for token in VERIFICATION_TOKENS):
            continue
        findings.append(LintFinding(
            severity="warning",
            rule="vague-rule",
            file=rel_path,
            line=lineno,
            message=(
                f"Rule uses vague quality language ({_first_match(lower, VAGUE_QUALITY_WORDS)!r}) "
                "without naming a verifier."
            ),
            suggested_fix=(
                "Pair the rule with a concrete check, for example `code passes `ruff check`` or "
                "`exports a `test` script that exits 0`."
            ),
        ))
        # Limit a single linter run from flooding on one bad file.
        if len(findings) >= 10:
            findings.append(LintFinding(
                severity="info",
                rule="vague-rule-truncated",
                file=rel_path,
                line=None,
                message="More vague rules likely present; output truncated at 10.",
                suggested_fix="Address the flagged lines first, then re-run `context lint`.",
            ))
            break
    return findings


def _check_contradictions(rel_path: str, text: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    lines = text.splitlines()
    for pattern_a, pattern_b, label in CONTRADICTION_PAIRS:
        hits_a = [i for i, line in enumerate(lines, start=1) if re.search(pattern_a, line, flags=re.IGNORECASE)]
        hits_b = [i for i, line in enumerate(lines, start=1) if re.search(pattern_b, line, flags=re.IGNORECASE)]
        if hits_a and hits_b:
            findings.append(LintFinding(
                severity="error",
                rule=f"contradictory-rule:{label}",
                file=rel_path,
                line=hits_a[0],
                message=(
                    f"Contradictory rules detected ({label}): line {hits_a[0]} vs line {hits_b[0]}."
                ),
                suggested_fix=(
                    "Keep one canonical rule. If exceptions exist, name them explicitly with "
                    "conditions instead of stating both as defaults."
                ),
            ))
    return findings


def _check_advanced_concepts_without_basics(
    rel_path: str,
    text: str,
    normalized: list[str],
) -> list[LintFinding]:
    lower = text.lower()
    advanced_hits = [c for c in ADVANCED_CONCEPTS if c in lower]
    if not advanced_hits:
        return []
    mentions_test = any(token in lower for token in VERIFICATION_TOKENS)
    if mentions_test:
        return []
    return [
        LintFinding(
            severity="warning",
            rule="beginner-hostile",
            file=rel_path,
            line=None,
            message=(
                f"File references advanced concepts ({', '.join(sorted(set(advanced_hits)))}) "
                "but does not mention any test/lint/build verifier first."
            ),
            suggested_fix=(
                "Lead with the project's test/lint commands. Move advanced topics (MCP, "
                "orchestration, hooks, plugins) below the basics or into a dedicated doc."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Cross-file checks
# ---------------------------------------------------------------------------


def _check_duplicates_across_files(
    file_payloads: list[tuple[str, str, list[str]]],
) -> list[LintFinding]:
    findings: list[LintFinding] = []
    # Build a normalized -> [(file, line, original)] index.
    index: dict[str, list[tuple[str, int, str]]] = {}
    for rel_path, text, _normalized in file_payloads:
        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not _looks_like_rule(line):
                continue
            normalized = _normalize_rule(line)
            if len(normalized.split()) < MIN_DUPLICATE_RULE_WORDS:
                continue
            index.setdefault(normalized, []).append((rel_path, lineno, line))

    for normalized, occurrences in index.items():
        unique_files = {o[0] for o in occurrences}
        if len(unique_files) < 2:
            continue
        files_ordered = sorted(unique_files)
        first_file, first_line, _ = next(o for o in occurrences if o[0] == files_ordered[0])
        findings.append(LintFinding(
            severity="warning",
            rule="duplicate-rule",
            file=first_file,
            line=first_line,
            message=(
                f"Rule appears in {len(files_ordered)} files: {', '.join(files_ordered)}. "
                "Duplicated rules drift over time."
            ),
            suggested_fix=(
                "Keep one canonical home for the rule and link to it from the other files."
            ),
        ))
    return findings


def _check_missing_build_test_commands(
    file_payloads: list[tuple[str, str, list[str]]],
    project_type: tuple[str, str, tuple[str, ...]] | None,
) -> list[LintFinding]:
    if not project_type:
        return []
    _, language, hints = project_type
    combined = "\n".join(text for _path, text, _norm in file_payloads).lower()
    if not combined.strip():
        return []
    if any(hint.lower() in combined for hint in hints):
        return []
    # We have at least one context file but none mentions a recognizable command. File-level
    # finding attached to the first context file alphabetically so the output is deterministic.
    first_file = sorted(p for p, _t, _n in file_payloads)[0]
    return [
        LintFinding(
            severity="error",
            rule="missing-build-test-commands",
            file=first_file,
            line=None,
            message=(
                f"Project looks like {language} but none of the agent-context files mention a "
                f"recognizable test/lint command (looked for: {', '.join(hints)})."
            ),
            suggested_fix=(
                "Add a `Commands` section to the agent-context file listing the exact build, "
                "test, and lint commands. Agents that don't know how to verify a change tend to "
                "skip verification."
            ),
        ),
    ]


def _check_tooling_conflicts(
    file_payloads: list[tuple[str, str, list[str]]],
    root: Path,
) -> list[LintFinding]:
    findings: list[LintFinding] = []
    combined_lower = "\n".join(text.lower() for _path, text, _norm in file_payloads)
    # Node lockfile conflicts.
    if (root / "package-lock.json").exists() and "use yarn" in combined_lower:
        findings.append(LintFinding(
            severity="warning",
            rule="tooling-conflict",
            file=_first_file_with(file_payloads, "use yarn"),
            line=None,
            message="Instructions say `use yarn` but the project commits `package-lock.json` (npm).",
            suggested_fix=(
                "Either switch the project to yarn (commit `yarn.lock`, remove `package-lock.json`) "
                "or update the instructions to `use npm`."
            ),
        ))
    if (root / "yarn.lock").exists() and "use npm" in combined_lower:
        findings.append(LintFinding(
            severity="warning",
            rule="tooling-conflict",
            file=_first_file_with(file_payloads, "use npm"),
            line=None,
            message="Instructions say `use npm` but the project commits `yarn.lock`.",
            suggested_fix="Reconcile the lockfile and the instructions; keep one source of truth.",
        ))
    if (root / "pnpm-lock.yaml").exists() and "use npm" in combined_lower:
        findings.append(LintFinding(
            severity="warning",
            rule="tooling-conflict",
            file=_first_file_with(file_payloads, "use npm"),
            line=None,
            message="Instructions say `use npm` but the project commits `pnpm-lock.yaml`.",
            suggested_fix="Reconcile the lockfile and the instructions; keep one source of truth.",
        ))
    # Python package-manager conflicts.
    if (root / "uv.lock").exists() and "use poetry" in combined_lower:
        findings.append(LintFinding(
            severity="warning",
            rule="tooling-conflict",
            file=_first_file_with(file_payloads, "use poetry"),
            line=None,
            message="Instructions say `use poetry` but the project commits `uv.lock`.",
            suggested_fix=(
                "Either standardize on uv (drop the poetry instructions) or migrate to poetry "
                "(commit `poetry.lock`, drop `uv.lock`)."
            ),
        ))
    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_project_type(root: Path) -> tuple[str, str, tuple[str, ...]] | None:
    for filename, language, hints in PROJECT_SIGNALS:
        if (root / filename).exists():
            return filename, language, hints
    return None


def _approx_tokens(text: str) -> int:
    # The compress module also estimates tokens; mirror its approximation for consistency.
    return max(1, len(text) // 4)


def _looks_like_rule(line: str) -> bool:
    if not line:
        return False
    if line.startswith("#"):
        return False  # heading, not a rule
    if line.startswith(">"):
        return False  # quote
    if line.startswith("```") or line.startswith("~~~"):
        return False
    stripped = line.lstrip("-*+ ").lstrip("0123456789. ")
    return bool(stripped) and len(stripped.split()) >= 3


def _normalize_rule(line: str) -> str:
    stripped = line.lstrip("-*+ ").lstrip("0123456789. ")
    cleaned = re.sub(r"[`*_\[\]]", "", stripped)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.lower().strip()


def _normalized_lines(text: str) -> list[str]:
    return [_normalize_rule(line) for line in text.splitlines() if _looks_like_rule(line.strip())]


def _first_match(text: str, candidates: Iterable[str]) -> str:
    for candidate in candidates:
        if candidate in text:
            return candidate
    return ""


def _first_file_with(
    file_payloads: list[tuple[str, str, list[str]]],
    needle: str,
) -> str:
    for rel_path, text, _norm in file_payloads:
        if needle in text.lower():
            return rel_path
    return file_payloads[0][0] if file_payloads else ""
