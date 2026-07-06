"""Memory governance.

Memory entries are reviewable Markdown files under `.coding-scaffold/memory/<class>/`. Each
entry has YAML-ish frontmatter (class, owner, created, expires, source, status) and a free-form
body. The schema is deliberately small so memory stays Git-reviewable.

Classes (from the maintainer brief):
- ``project_fact``    Stable, source-linked.
- ``team_preference`` Reviewable convention.
- ``decision``        Ideally linked to an ADR or issue.
- ``session_lesson``  Expires unless promoted. Default backend for the raw capture flow.
- ``failed_attempt``  Useful but potentially misleading.
- ``secret``          Never store. ``memory capture --class secret`` is refused.
- ``personal_data``   Never store by default. Requires ``--allow-personal``.

Backend: Markdown only in v1. Pluggable storage is on the roadmap (sqlite, mempalace, vector)
but the default is intentionally simple — a folder of Markdown files in Git.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .errors import CliError


MEMORY_DIR = Path(".coding-scaffold") / "memory"
EXPIRED_SUBDIR = "_expired"

MEMORY_CLASSES: tuple[str, ...] = (
    "project_fact",
    "team_preference",
    "decision",
    "session_lesson",
    "failed_attempt",
    "personal_data",
)

# Never-stored classes. Capture refuses these outright.
FORBIDDEN_CLASSES: tuple[str, ...] = ("secret",)

# Classes that require an explicit opt-in flag.
RESTRICTED_CLASSES: tuple[str, ...] = ("personal_data",)

# Default expiry for session_lesson entries when --expires is not given.
SESSION_LESSON_TTL_DAYS = 30

# Heuristic patterns for `memory audit`. Lightweight — these are review hints, not detectors.
SECRET_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?i)\b(?:sk-[A-Za-z0-9]{20,})\b", "OpenAI-style API key prefix"),
    (r"(?i)\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}\b", "GitHub personal access token"),
    (r"(?i)\bAKIA[0-9A-Z]{16}\b", "AWS access key ID"),
    (r"(?i)\baws_secret_access_key\s*=\s*\S+", "AWS secret access key assignment"),
    (r"(?i)\bbearer\s+[A-Za-z0-9._-]{20,}", "Bearer token"),
    (r"-----BEGIN [A-Z ]+PRIVATE KEY-----", "private key block"),
    (r"(?i)\bpassword\s*[:=]\s*\S{4,}", "password assignment"),
)

PII_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "email address"),
    (r"\+?\d[\d\s().-]{8,}\d", "phone-number-like sequence"),
)


@dataclass(frozen=True)
class MemoryEntry:
    """One memory record stored as a Markdown file with frontmatter."""

    id: str
    class_: str  # "class" is a Python keyword
    owner: str
    created: str  # ISO date
    expires: str | None
    source: str | None
    status: str  # "active" | "promoted" | "expired"
    promoted_from: str | None
    promoted_to: str | None
    path: Path
    body: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "class": self.class_,
            "owner": self.owner,
            "created": self.created,
            "expires": self.expires,
            "source": self.source,
            "status": self.status,
            "promoted_from": self.promoted_from,
            "promoted_to": self.promoted_to,
            "path": str(self.path),
        }


@dataclass(frozen=True)
class MemoryCaptureResult:
    entry: MemoryEntry
    created: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "entry": self.entry.to_dict(),
            "created": self.created,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class MemoryReviewReport:
    entries: list[MemoryEntry]
    flagged: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "flagged": {k: list(v) for k, v in self.flagged.items()},
            "warnings": list(self.warnings),
            "counts": {
                "total": len(self.entries),
                "flagged_unowned": len(self.flagged.get("unowned", [])),
                "flagged_expiring_soon": len(self.flagged.get("expiring_soon", [])),
                "flagged_expired": len(self.flagged.get("expired", [])),
            },
        }


@dataclass(frozen=True)
class MemoryPromoteResult:
    source_entry: MemoryEntry | None
    new_entry: MemoryEntry | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_entry": self.source_entry.to_dict() if self.source_entry else None,
            "new_entry": self.new_entry.to_dict() if self.new_entry else None,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class MemoryExpireResult:
    expired_entries: list[str]
    moved_to: dict[str, str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "expired_entries": list(self.expired_entries),
            "moved_to": dict(self.moved_to),
            "warnings": list(self.warnings),
            "counts": {"expired": len(self.expired_entries)},
        }


@dataclass(frozen=True)
class MemoryAuditFinding:
    severity: str  # "error" | "warning" | "info"
    rule: str
    entry_id: str
    file: str
    line: int | None
    pattern_label: str
    suggested_fix: str

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "entry_id": self.entry_id,
            "file": self.file,
            "line": self.line,
            "pattern_label": self.pattern_label,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True)
class MemoryAuditReport:
    findings: list[MemoryAuditFinding]
    entries_scanned: int
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    def to_dict(self) -> dict[str, object]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "entries_scanned": self.entries_scanned,
            "warnings": list(self.warnings),
            "counts": {
                "errors": self.error_count,
                "warnings": sum(1 for f in self.findings if f.severity == "warning"),
                "info": sum(1 for f in self.findings if f.severity == "info"),
            },
        }


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------


def capture_memory(
    target: Path,
    *,
    class_: str,
    content: str,
    owner: str | None = None,
    source: str | None = None,
    expires: str | None = None,
    allow_personal: bool = False,
    when: datetime | None = None,
    slug: str | None = None,
) -> MemoryCaptureResult:
    """Write a new memory entry under `.coding-scaffold/memory/<class>/`.

    Refuses ``class_="secret"``. Refuses ``class_="personal_data"`` unless ``allow_personal``
    is True. Refuses content that the audit heuristic recognizes as a secret.
    """

    root = target.expanduser().resolve()
    if class_ in FORBIDDEN_CLASSES:
        raise CliError(
            f"Memory class {class_!r} is never stored.",
            "Move the value out of the repo and use a proper secret store.",
        )
    if class_ in RESTRICTED_CLASSES and not allow_personal:
        raise CliError(
            f"Memory class {class_!r} is restricted.",
            "Pass --allow-personal to confirm the team has approved this category for storage.",
        )
    if class_ not in MEMORY_CLASSES:
        raise CliError(
            f"Unknown memory class {class_!r}.",
            f"Choose one of: {', '.join(MEMORY_CLASSES)}.",
        )

    # Heuristic secret check on the content itself.
    for pattern, label in SECRET_PATTERNS:
        if re.search(pattern, content):
            raise CliError(
                f"Content looks like a secret ({label}); capture refused.",
                "Store the value in .env.local or a real secret manager; reference it "
                "indirectly here.",
            )

    captured_at = when or datetime.now(UTC)
    today = captured_at.date()
    base_slug = _safe_slug(slug or _derive_slug(content))
    entry_id = f"{today.isoformat()}-{base_slug}"
    class_dir = root / MEMORY_DIR / class_
    class_dir.mkdir(parents=True, exist_ok=True)
    candidate = class_dir / f"{entry_id}.md"
    counter = 2
    while candidate.exists():
        entry_id = f"{today.isoformat()}-{base_slug}-{counter}"
        candidate = class_dir / f"{entry_id}.md"
        counter += 1

    if expires is None and class_ == "session_lesson":
        expires_dt = today + timedelta(days=SESSION_LESSON_TTL_DAYS)
        expires = expires_dt.isoformat()

    frontmatter = {
        "id": entry_id,
        "class": class_,
        "owner": owner or "",
        "created": today.isoformat(),
        "expires": expires or "",
        "source": source or "",
        "status": "active",
    }
    payload = _render_entry(frontmatter, content)
    candidate.write_text(payload, encoding="utf-8")

    entry = MemoryEntry(
        id=entry_id,
        class_=class_,
        owner=frontmatter["owner"],
        created=frontmatter["created"],
        expires=expires or None,
        source=source or None,
        status="active",
        promoted_from=None,
        promoted_to=None,
        path=candidate,
        body=content,
    )
    warnings: list[str] = []
    if not owner:
        warnings.append("Owner is empty. Edit the file or pass --owner.")
    return MemoryCaptureResult(entry=entry, created=True, warnings=warnings)


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


def review_memory(target: Path, *, when: date | None = None) -> MemoryReviewReport:
    """List active memory entries; surface unowned and expiring-soon items."""

    root = target.expanduser().resolve()
    entries = list_memory_entries(root)
    today = when or datetime.now(UTC).date()
    flagged: dict[str, list[str]] = {
        "unowned": [],
        "expiring_soon": [],
        "expired": [],
    }
    soon_window = timedelta(days=7)
    for entry in entries:
        if entry.status != "active":
            continue
        if not entry.owner.strip() or entry.owner.strip().startswith("<"):
            flagged["unowned"].append(entry.id)
        if entry.expires:
            try:
                expires_at = date.fromisoformat(entry.expires)
            except ValueError:
                continue
            if expires_at < today:
                flagged["expired"].append(entry.id)
            elif expires_at - today <= soon_window:
                flagged["expiring_soon"].append(entry.id)
    return MemoryReviewReport(entries=entries, flagged=flagged)


# ---------------------------------------------------------------------------
# Promote
# ---------------------------------------------------------------------------


def promote_memory(
    target: Path,
    *,
    entry_id: str,
    new_class: str,
    new_owner: str | None = None,
    when: datetime | None = None,
) -> MemoryPromoteResult:
    """Move an entry from one class to another. Source is marked promoted but kept for audit."""

    root = target.expanduser().resolve()
    if new_class in FORBIDDEN_CLASSES:
        raise CliError(
            f"Cannot promote to class {new_class!r}.",
            f"Choose one of: {', '.join(sorted(set(MEMORY_CLASSES) - set(FORBIDDEN_CLASSES)))}.",
        )
    if new_class not in MEMORY_CLASSES:
        raise CliError(
            f"Unknown memory class {new_class!r}.",
            f"Choose one of: {', '.join(MEMORY_CLASSES)}.",
        )
    entry = _find_entry(root, entry_id)
    if entry is None:
        raise CliError(
            f"Memory entry {entry_id!r} not found.",
            "Run `coding-scaffold memory review` to list entry ids.",
        )
    if entry.class_ == new_class:
        return MemoryPromoteResult(
            source_entry=entry,
            new_entry=None,
            warnings=[f"Entry is already in class {new_class!r}; nothing to do."],
        )

    captured_at = when or datetime.now(UTC)
    today = captured_at.date()
    new_dir = root / MEMORY_DIR / new_class
    new_dir.mkdir(parents=True, exist_ok=True)
    new_id = f"{today.isoformat()}-{entry.id}"
    candidate = new_dir / f"{new_id}.md"
    counter = 2
    while candidate.exists():
        new_id = f"{today.isoformat()}-{entry.id}-{counter}"
        candidate = new_dir / f"{new_id}.md"
        counter += 1

    new_frontmatter = {
        "id": new_id,
        "class": new_class,
        "owner": new_owner or entry.owner,
        "created": entry.created,  # preserve original creation date
        "expires": "",
        "source": entry.source or "",
        "status": "active",
        "promoted_from": entry.id,
    }
    new_payload = _render_entry(new_frontmatter, entry.body)
    candidate.write_text(new_payload, encoding="utf-8")

    # Mark the source as promoted (do not delete — the original is part of the audit trail).
    source_frontmatter, body = _parse_entry_text(entry.path.read_text(encoding="utf-8-sig"))
    source_frontmatter["status"] = "promoted"
    source_frontmatter["promoted_to"] = new_id
    entry.path.write_text(_render_entry(source_frontmatter, body), encoding="utf-8")

    new_entry = MemoryEntry(
        id=new_id,
        class_=new_class,
        owner=new_frontmatter["owner"],
        created=entry.created,
        expires=None,
        source=entry.source,
        status="active",
        promoted_from=entry.id,
        promoted_to=None,
        path=candidate,
        body=entry.body,
    )
    return MemoryPromoteResult(source_entry=entry, new_entry=new_entry)


# ---------------------------------------------------------------------------
# Expire
# ---------------------------------------------------------------------------


def expire_memory(target: Path, *, when: date | None = None) -> MemoryExpireResult:
    """Move active entries past their expiry into `.coding-scaffold/memory/_expired/`."""

    root = target.expanduser().resolve()
    today = when or datetime.now(UTC).date()
    expired_dir = root / MEMORY_DIR / EXPIRED_SUBDIR
    expired_ids: list[str] = []
    moved: dict[str, str] = {}
    warnings: list[str] = []
    for entry in list_memory_entries(root):
        if entry.status != "active" or not entry.expires:
            continue
        try:
            expires_at = date.fromisoformat(entry.expires)
        except ValueError:
            warnings.append(f"Entry {entry.id} has unparseable expires {entry.expires!r}.")
            continue
        if expires_at >= today:
            continue
        expired_dir.mkdir(parents=True, exist_ok=True)
        target_path = expired_dir / f"{entry.class_}--{entry.path.name}"
        counter = 2
        while target_path.exists():
            target_path = expired_dir / f"{entry.class_}--{entry.path.stem}-{counter}.md"
            counter += 1
        frontmatter, body = _parse_entry_text(entry.path.read_text(encoding="utf-8-sig"))
        frontmatter["status"] = "expired"
        target_path.write_text(_render_entry(frontmatter, body), encoding="utf-8")
        entry.path.unlink()
        expired_ids.append(entry.id)
        moved[entry.id] = str(target_path)
    return MemoryExpireResult(expired_entries=expired_ids, moved_to=moved, warnings=warnings)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def audit_memory(target: Path) -> MemoryAuditReport:
    """Scan every memory file for content that looks like a secret or like PII."""

    root = target.expanduser().resolve()
    entries = list_memory_entries(root, include_expired=True)
    findings: list[MemoryAuditFinding] = []
    for entry in entries:
        try:
            text = entry.path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        rel_path = str(entry.path.relative_to(root)) if root in entry.path.parents else str(entry.path)
        # Lines for line-number reporting.
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, label in SECRET_PATTERNS:
                if re.search(pattern, line):
                    findings.append(MemoryAuditFinding(
                        severity="error",
                        rule="looks-like-secret",
                        entry_id=entry.id,
                        file=rel_path,
                        line=lineno,
                        pattern_label=label,
                        suggested_fix=(
                            "Remove the value from the memory entry. Store secrets in a real "
                            "secret manager and reference them indirectly."
                        ),
                    ))
            for pattern, label in PII_PATTERNS:
                if re.search(pattern, line):
                    findings.append(MemoryAuditFinding(
                        severity="warning",
                        rule="looks-like-pii",
                        entry_id=entry.id,
                        file=rel_path,
                        line=lineno,
                        pattern_label=label,
                        suggested_fix=(
                            "Confirm the value is needed for the memory entry. If it's "
                            "incidental, redact. If it's load-bearing, ensure the team has "
                            "approved personal-data storage."
                        ),
                    ))
    findings.sort(key=lambda f: (
        {"error": 0, "warning": 1, "info": 2}[f.severity],
        f.file,
        f.line or 0,
        f.rule,
    ))
    return MemoryAuditReport(findings=findings, entries_scanned=len(entries))


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def list_memory_entries(root: Path, *, include_expired: bool = False) -> list[MemoryEntry]:
    memory_dir = root / MEMORY_DIR
    if not memory_dir.exists():
        return []
    entries: list[MemoryEntry] = []
    for class_dir in sorted(memory_dir.iterdir()):
        if not class_dir.is_dir():
            continue
        if class_dir.name == EXPIRED_SUBDIR and not include_expired:
            continue
        for path in sorted(class_dir.glob("*.md")):
            entry = _read_entry(path)
            if entry:
                entries.append(entry)
    return entries


def _find_entry(root: Path, entry_id: str) -> MemoryEntry | None:
    for entry in list_memory_entries(root, include_expired=True):
        if entry.id == entry_id:
            return entry
    return None


def _read_entry(path: Path) -> MemoryEntry | None:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    frontmatter, body = _parse_entry_text(text)
    return MemoryEntry(
        id=str(frontmatter.get("id", path.stem)),
        class_=str(frontmatter.get("class", path.parent.name)),
        owner=str(frontmatter.get("owner", "")),
        created=str(frontmatter.get("created", "")),
        expires=str(frontmatter.get("expires", "")) or None,
        source=str(frontmatter.get("source", "")) or None,
        status=str(frontmatter.get("status", "active")),
        promoted_from=str(frontmatter.get("promoted_from", "")) or None,
        promoted_to=str(frontmatter.get("promoted_to", "")) or None,
        path=path,
        body=body.strip(),
    )


def _render_entry(frontmatter: dict[str, object], body: str) -> str:
    """Write a Markdown entry with simple key: value frontmatter (one line per field)."""

    lines = ["---"]
    for key in (
        "id",
        "class",
        "owner",
        "created",
        "expires",
        "source",
        "status",
        "promoted_from",
        "promoted_to",
    ):
        if key in frontmatter:
            value = frontmatter[key]
            if value is None:
                value = ""
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    body_stripped = body.rstrip()
    if body_stripped:
        lines.append(body_stripped)
        lines.append("")
    return "\n".join(lines)


def _parse_entry_text(text: str) -> tuple[dict[str, str], str]:
    """Parse the simple `key: value` frontmatter we emit."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    frontmatter: dict[str, str] = {}
    body_start = len(lines)
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            body_start = index + 1
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", lines[index])
        if not match:
            continue
        frontmatter[match.group(1)] = match.group(2).strip()
    body = "\n".join(lines[body_start:])
    return frontmatter, body


def _safe_slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-").lower()
    return cleaned or "note"


def _derive_slug(content: str) -> str:
    snippet = content.strip().splitlines()[0] if content.strip() else "note"
    words = snippet.split()[:6]
    return _safe_slug(" ".join(words)) or "note"


def write_memory_config(target: Path, *, force: bool = False) -> dict[str, object]:
    """Optional config file documenting the memory backend choice. Markdown-only in v1."""

    root = target.expanduser().resolve()
    path = root / MEMORY_DIR / "config.json"
    if path.exists() and not force:
        return {"path": str(path), "created": False, "skipped": True}
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "$schema_version": 1,
        "description": (
            "Memory backend configuration. Markdown is the v1 default. sqlite, mempalace, and "
            "vector backends are on the roadmap."
        ),
        "backend": "markdown",
        "classes": list(MEMORY_CLASSES),
        "forbidden_classes": list(FORBIDDEN_CLASSES),
        "restricted_classes": list(RESTRICTED_CLASSES),
        "session_lesson_ttl_days": SESSION_LESSON_TTL_DAYS,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(path), "created": True, "skipped": False}


# Reserved for future backends; keep the import surface stable.
__all__ = (
    "MEMORY_DIR",
    "MEMORY_CLASSES",
    "FORBIDDEN_CLASSES",
    "RESTRICTED_CLASSES",
    "MemoryEntry",
    "MemoryCaptureResult",
    "MemoryReviewReport",
    "MemoryPromoteResult",
    "MemoryExpireResult",
    "MemoryAuditReport",
    "MemoryAuditFinding",
    "capture_memory",
    "review_memory",
    "promote_memory",
    "expire_memory",
    "audit_memory",
    "list_memory_entries",
    "write_memory_config",
)
