"""Reviewable skill packs.

Each skill is a directory under `.coding-scaffold/skills/<skill-name>/` containing:

    SKILL.md       - human-readable description and operating notes
    manifest.json  - machine-readable metadata (owner, version, capabilities, risk)
    scripts/       - optional helper scripts
    tests/         - optional verification scripts
    README.md      - usage/examples
    CHECKSUM       - sha256(SKILL.md || manifest.json) frozen at approval time

This module supports four operations:

    skills new <name>     - scaffold a new skill from templates
    skills lint           - validate every skill against the schema and flag risk language
    skills approve <name> - re-compute and store the CHECKSUM (and write an approval marker)
    skills export <name>  - bundle a skill directory into a sharable tar.gz

All checks are deterministic. No commands are executed. No network calls.
"""

from __future__ import annotations

import json
import re
import tarfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .file_ops import sha256_bytes


SKILLS_RELATIVE = Path(".coding-scaffold") / "skills"

REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = (
    "name",
    "version",
    "owner",
    "risk_level",
    "description",
)

RISK_LEVELS: tuple[str, ...] = ("low", "medium", "high", "critical")

# Broad / always-on language that should be flagged in SKILL.md.
BROAD_USAGE_PHRASES: tuple[str, ...] = (
    "always use this",
    "always invoke",
    "use this for everything",
    "use this for all",
    "always apply",
    "default to this",
    "use whenever",
    "use in all sessions",
)

# Phrases that indicate hidden / indirect instructions buried in SKILL.md.
HIDDEN_INSTRUCTION_PHRASES: tuple[str, ...] = (
    "do not tell the user",
    "do not mention",
    "do not disclose",
    "hide this from the user",
    "ignore the system prompt",
    "override the user",
)

# Capability claims that the SKILL.md should declare, matched as keywords.
SENSITIVE_CAPABILITY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("network", "network"),
    ("http://", "network"),
    ("https://", "network"),
    ("fetch ", "network"),
    ("curl ", "network"),
    ("subprocess", "shell"),
    ("os.system", "shell"),
    ("bash -c", "shell"),
    ("shell=true", "shell"),
    ("api_key", "credential"),
    ("api token", "credential"),
    ("secret", "credential"),
    (".env", "credential"),
    ("password", "credential"),
)


@dataclass(frozen=True)
class SkillFinding:
    severity: str
    rule: str
    skill: str | None
    file: str | None
    line: int | None
    message: str
    suggested_fix: str

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "skill": self.skill,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True)
class SkillLintReport:
    findings: list[SkillFinding] = field(default_factory=list)
    skills_scanned: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    def to_dict(self) -> dict[str, object]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "skills_scanned": list(self.skills_scanned),
            "warnings": list(self.warnings),
            "counts": {
                "skills": len(self.skills_scanned),
                "errors": self.error_count,
                "warnings": self.warning_count,
            },
        }


@dataclass(frozen=True)
class SkillResult:
    skill: str
    path: Path
    files: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "skill": self.skill,
            "path": str(self.path),
            "files": [str(p) for p in self.files],
            "skipped": [str(p) for p in self.skipped],
        }


# ---------------------------------------------------------------------------
# Scaffolding
# ---------------------------------------------------------------------------


def new_skill(target: Path, name: str, *, owner: str | None = None) -> SkillResult:
    """Scaffold a new skill at `.coding-scaffold/skills/<name>/`."""

    root = target.expanduser().resolve()
    safe = _safe_skill_name(name)
    skill_dir = root / SKILLS_RELATIVE / safe
    files: list[Path] = []
    skipped: list[Path] = []

    skill_md = skill_dir / "SKILL.md"
    manifest = skill_dir / "manifest.json"
    readme = skill_dir / "README.md"
    scripts_dir = skill_dir / "scripts"
    tests_dir = skill_dir / "tests"

    skill_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    _write_if_absent(skill_md, _skill_md_template(safe), files, skipped)
    _write_if_absent(manifest, _manifest_template(safe, owner=owner), files, skipped)
    _write_if_absent(readme, _readme_template(safe), files, skipped)
    _write_if_absent(scripts_dir / ".gitkeep", "", files, skipped)
    _write_if_absent(tests_dir / ".gitkeep", "", files, skipped)

    return SkillResult(skill=safe, path=skill_dir, files=files, skipped=skipped)


def _write_if_absent(path: Path, content: str, files: list[Path], skipped: list[Path]) -> None:
    if path.exists():
        skipped.append(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    files.append(path)


def _skill_md_template(name: str) -> str:
    return f"""---
name: {name}
status: draft
---

# Skill: {name}

## When to use

<!-- Describe a concrete trigger. Avoid "always" language. -->

## Inputs

<!-- What the agent needs before running this skill. -->

## Workflow

<!-- Numbered steps. Each step should be reviewable. -->

1.
2.
3.

## Verification

<!-- How does the operator know the skill worked? Name the exact check
(e.g. `pytest tests/`, `ruff check`, output matches expected pattern). -->

## Capabilities required

<!-- Declare any of: network, shell, filesystem-write, credential. -->

- none

## Maintenance notes

<!-- When to review, who to ping, what historically went wrong. -->
"""


def _manifest_template(name: str, *, owner: str | None) -> str:
    payload = {
        "name": name,
        "version": "0.1.0",
        "owner": owner or "<your-handle>",
        "risk_level": "low",
        "description": f"Reviewable skill: {name}.",
        "capabilities": [],
        "verification": "",
        "created": datetime.now(UTC).date().isoformat(),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _readme_template(name: str) -> str:
    return f"""# {name}

Usage and examples for the `{name}` skill. See `SKILL.md` for the operating
contract and `manifest.json` for the machine-readable metadata.

## Example

<!-- Show one concrete invocation. Include expected output. -->
"""


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------


def lint_skills(target: Path) -> SkillLintReport:
    root = target.expanduser().resolve()
    skills_dir = root / SKILLS_RELATIVE
    findings: list[SkillFinding] = []
    skills_scanned: list[str] = []
    warnings: list[str] = []
    if not skills_dir.exists():
        return SkillLintReport(findings=[], skills_scanned=[], warnings=[])
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("."):
            continue
        skill = skill_dir.name
        skills_scanned.append(skill)
        findings.extend(_lint_one_skill(skill, skill_dir))
    findings.sort(key=lambda f: (
        {"error": 0, "warning": 1, "info": 2}[f.severity],
        f.skill or "",
        f.file or "",
        f.line or 0,
        f.rule,
    ))
    return SkillLintReport(findings=findings, skills_scanned=skills_scanned, warnings=warnings)


def _lint_one_skill(skill: str, skill_dir: Path) -> list[SkillFinding]:
    findings: list[SkillFinding] = []
    skill_md = skill_dir / "SKILL.md"
    manifest_path = skill_dir / "manifest.json"

    if not skill_md.exists():
        findings.append(SkillFinding(
            severity="error",
            rule="missing-skill-md",
            skill=skill,
            file=None,
            line=None,
            message="Skill is missing SKILL.md.",
            suggested_fix="Create SKILL.md with at minimum a 'When to use' and 'Verification' section.",
        ))
    else:
        findings.extend(_lint_skill_md(skill, skill_md))

    if not manifest_path.exists():
        findings.append(SkillFinding(
            severity="error",
            rule="missing-manifest",
            skill=skill,
            file=None,
            line=None,
            message="Skill is missing manifest.json.",
            suggested_fix=(
                "Create manifest.json with name, version, owner, risk_level, and description."
            ),
        ))
    else:
        findings.extend(_lint_manifest(skill, manifest_path))

    # Approval / drift check.
    checksum_file = skill_dir / "CHECKSUM"
    if checksum_file.exists() and skill_md.exists() and manifest_path.exists():
        recorded = checksum_file.read_text(encoding="utf-8-sig").strip()
        current = _compute_checksum(skill_md, manifest_path)
        if recorded != current:
            findings.append(SkillFinding(
                severity="warning",
                rule="checksum-drift",
                skill=skill,
                file=str(checksum_file.relative_to(skill_dir)),
                line=None,
                message=(
                    "SKILL.md or manifest.json changed since the recorded approval."
                ),
                suggested_fix=(
                    "Review the diff and re-run `coding-scaffold skills approve "
                    f"{skill}` once the change is intentional."
                ),
            ))
    return findings


def _lint_skill_md(skill: str, path: Path) -> list[SkillFinding]:
    findings: list[SkillFinding] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return [SkillFinding(
            severity="error",
            rule="unreadable",
            skill=skill,
            file=path.name,
            line=None,
            message=f"Could not read SKILL.md: {exc}",
            suggested_fix="Make sure the file is UTF-8 and readable.",
        )]
    lower = text.lower()
    # Broad / always-on language.
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line_lower = raw_line.lower()
        for phrase in BROAD_USAGE_PHRASES:
            if phrase in line_lower:
                findings.append(SkillFinding(
                    severity="warning",
                    rule="broad-usage",
                    skill=skill,
                    file=path.name,
                    line=lineno,
                    message=f"SKILL.md uses broad usage language: {phrase!r}.",
                    suggested_fix=(
                        "Replace 'always' with a concrete trigger condition. Skills that apply "
                        "to every session tend to drift into unsafe defaults."
                    ),
                ))
                break
        for phrase in HIDDEN_INSTRUCTION_PHRASES:
            if phrase in line_lower:
                findings.append(SkillFinding(
                    severity="error",
                    rule="hidden-instruction",
                    skill=skill,
                    file=path.name,
                    line=lineno,
                    message=f"SKILL.md contains hidden-instruction language: {phrase!r}.",
                    suggested_fix=(
                        "Remove the line. Skills must not include instructions designed to "
                        "evade user awareness."
                    ),
                ))
                break

    # Missing required sections.
    required_headings = ("when to use", "verification")
    for heading in required_headings:
        if not re.search(rf"^##\s+{re.escape(heading)}\b", text, flags=re.IGNORECASE | re.MULTILINE):
            findings.append(SkillFinding(
                severity="warning",
                rule=f"missing-section:{heading.replace(' ', '-')}",
                skill=skill,
                file=path.name,
                line=None,
                message=f"SKILL.md is missing a '## {heading.title()}' section.",
                suggested_fix=(
                    f"Add a '## {heading.title()}' section so reviewers and agents can confirm "
                    "the skill's contract."
                ),
            ))

    # Capability claims vs declared capabilities.
    declared = re.search(
        r"##\s+capabilities\s+required\s*\n+(.*?)(?:\n##|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    declared_text = declared.group(1).lower() if declared else ""
    for keyword, capability in SENSITIVE_CAPABILITY_KEYWORDS:
        if keyword in lower and capability not in declared_text:
            findings.append(SkillFinding(
                severity="warning",
                rule="undeclared-capability",
                skill=skill,
                file=path.name,
                line=None,
                message=(
                    f"SKILL.md references {keyword!r} (capability: {capability}) but the "
                    "'Capabilities required' section does not declare it."
                ),
                suggested_fix=(
                    f"Add '{capability}' to the 'Capabilities required' section, or remove the "
                    "reference if the skill doesn't actually need that capability."
                ),
            ))
    return findings


def _lint_manifest(skill: str, path: Path) -> list[SkillFinding]:
    findings: list[SkillFinding] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [SkillFinding(
            severity="error",
            rule="invalid-manifest-json",
            skill=skill,
            file=path.name,
            line=None,
            message=f"manifest.json is not valid JSON: {exc}",
            suggested_fix="Validate the manifest with `python -m json.tool manifest.json`.",
        )]
    if not isinstance(payload, dict):
        return [SkillFinding(
            severity="error",
            rule="invalid-manifest-shape",
            skill=skill,
            file=path.name,
            line=None,
            message="manifest.json must be a JSON object.",
            suggested_fix="Wrap the payload in `{}` and re-run lint.",
        )]
    for required in REQUIRED_MANIFEST_FIELDS:
        if not payload.get(required):
            findings.append(SkillFinding(
                severity="error",
                rule=f"missing-manifest-field:{required}",
                skill=skill,
                file=path.name,
                line=None,
                message=f"manifest.json is missing required field {required!r}.",
                suggested_fix=f"Set `{required}` in manifest.json.",
            ))
    risk = payload.get("risk_level")
    if risk and risk not in RISK_LEVELS:
        findings.append(SkillFinding(
            severity="warning",
            rule="invalid-risk-level",
            skill=skill,
            file=path.name,
            line=None,
            message=(
                f"risk_level {risk!r} is not one of {RISK_LEVELS}."
            ),
            suggested_fix=f"Use one of {RISK_LEVELS}.",
        ))
    if "verification" in payload and not payload.get("verification"):
        findings.append(SkillFinding(
            severity="info",
            rule="empty-verification",
            skill=skill,
            file=path.name,
            line=None,
            message="manifest.json has an empty 'verification' field.",
            suggested_fix=(
                "Fill `verification` with a one-line description of how the skill is checked."
            ),
        ))
    owner = payload.get("owner")
    if isinstance(owner, str) and owner.strip().startswith("<"):
        findings.append(SkillFinding(
            severity="warning",
            rule="placeholder-owner",
            skill=skill,
            file=path.name,
            line=None,
            message=f"manifest.json owner is still a placeholder ({owner!r}).",
            suggested_fix="Replace with a real GitHub handle or team alias.",
        ))
    return findings


# ---------------------------------------------------------------------------
# Approve + export
# ---------------------------------------------------------------------------


def approve_skill(target: Path, name: str) -> dict[str, object]:
    """Compute the checksum of SKILL.md + manifest.json and record it in `CHECKSUM`."""

    root = target.expanduser().resolve()
    safe = _safe_skill_name(name)
    skill_dir = root / SKILLS_RELATIVE / safe
    if not skill_dir.exists():
        return {"approved": False, "skill": safe, "warning": f"Skill {safe!r} does not exist."}
    skill_md = skill_dir / "SKILL.md"
    manifest = skill_dir / "manifest.json"
    if not skill_md.exists() or not manifest.exists():
        return {
            "approved": False,
            "skill": safe,
            "warning": "SKILL.md and manifest.json must exist before approval.",
        }
    checksum = _compute_checksum(skill_md, manifest)
    checksum_file = skill_dir / "CHECKSUM"
    checksum_file.write_text(checksum + "\n", encoding="utf-8")
    return {
        "approved": True,
        "skill": safe,
        "checksum": checksum,
        "checksum_file": str(checksum_file),
    }


def export_skill(target: Path, name: str, *, output: Path | None = None) -> dict[str, object]:
    """Bundle a skill directory into a tar.gz archive for sharing."""

    root = target.expanduser().resolve()
    safe = _safe_skill_name(name)
    skill_dir = root / SKILLS_RELATIVE / safe
    if not skill_dir.exists():
        return {"exported": False, "skill": safe, "warning": f"Skill {safe!r} does not exist."}
    output_path = output.expanduser().resolve() if output else root / f"{safe}.tar.gz"
    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(skill_dir, arcname=safe)
    return {"exported": True, "skill": safe, "archive": str(output_path)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_skill_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-").lower()
    if not cleaned:
        raise ValueError("Skill name cannot be empty.")
    return cleaned


def _compute_checksum(skill_md: Path, manifest: Path) -> str:
    return sha256_bytes(skill_md.read_bytes() + b"\x00" + manifest.read_bytes())
