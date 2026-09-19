"""Opt-in native lifecycle hooks that run bounded, local scaffold checks only."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .compatibility import check_compatibility, validate_hooks
from .context_lint import lint_context
from .errors import CliError
from .file_ops import write_json
from .skills import lint_skills


HOOK_COMMAND = "coding-scaffold tools hook-run"
HOOK_CONFIGS = {"codex": ".codex/hooks.json", "claude-code": ".claude/settings.json"}
HOOK_REPORT_RELATIVE = Path(".coding-scaffold/hook-report.json")


def write_hooks(target: Path, tools: list[str]) -> dict[str, object]:
    """Explicit opt-in; merge only our hooks, preserving all existing settings/handlers."""
    root = target.expanduser().resolve()
    pending: list[tuple[Path, dict]] = []
    skipped: list[str] = []
    # Validate every requested config before writing any of them.
    for tool in dict.fromkeys(tools):
        if tool not in HOOK_CONFIGS:
            raise CliError(
                f"Lifecycle hooks are not supported for {tool}.", "Choose codex or claude-code."
            )
        path = root / HOOK_CONFIGS[tool]
        if not path.resolve().is_relative_to(root):
            raise CliError(
                "Hook configuration leaves the project.", "Use a project-local config file."
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
            if not isinstance(payload, dict) or validate_hooks(payload.get("hooks", {}), str(path)):
                raise ValueError
        except (OSError, UnicodeError, ValueError) as exc:
            raise CliError(
                f"Cannot merge hooks into {HOOK_CONFIGS[tool]}.",
                "Fix the existing JSON/hook structure and retry.",
            ) from exc
        hooks = payload.setdefault("hooks", {})
        changed = False
        for event in ("SessionStart", "Stop"):
            groups = hooks.setdefault(event, [])
            # Do not replace user customizations of an existing scaffold handler.
            if any(
                handler.get("command") == HOOK_COMMAND
                for group in groups
                for handler in group["hooks"]
            ):
                continue
            groups.append({"hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 15}]})
            changed = True
        if changed:
            pending.append((path, payload))
        else:
            skipped.append(str(path))
    for path, payload in pending:
        write_json(path, payload)
    return {
        "files": [str(path) for path, _ in pending],
        "skipped": skipped,
        "notes": [
            "coding-scaffold must be on the agent's PATH; review and trust native hooks before use.",
            "Hooks run local metadata checks, not your project's test suite. No chat transcripts are saved.",
            "Stop writes .coding-scaffold/hook-report.json; add it to your ignore rules if desired.",
        ],
    }


def run_hook(payload: object) -> dict[str, object]:
    """Consume only event/cwd/loop-guard fields; never execute or persist tool/chat input."""
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("hook_event_name"), str)
        or payload["hook_event_name"] not in {"SessionStart", "Stop"}
    ):
        raise CliError(
            "Unsupported lifecycle hook input.", "Send a SessionStart or Stop JSON object on stdin."
        )
    cwd = payload.get("cwd")
    if "stop_hook_active" in payload and not isinstance(payload["stop_hook_active"], bool):
        raise CliError("Invalid stop_hook_active value.", "Use a JSON boolean for the loop guard.")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        raise CliError(
            "Hook input requires an existing absolute cwd.",
            "Let the native agent supply the working directory.",
        )
    current = Path(cwd).resolve()
    root = next(
        (
            path
            for path in (current, *current.parents)
            if (path / ".git").exists() or (path / ".coding-scaffold").is_dir()
        ),
        current,
    )
    compatibility = check_compatibility(root)
    event = payload["hook_event_name"]
    if event == "SessionStart":
        count = len(compatibility.findings)
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": (
                    f"CodingScaffold: {count} compatibility finding(s). "
                    "Use coding-scaffold tools compatibility --target . for details. "
                    "The Stop hook checks scaffold metadata only; use the project's documented verification commands."
                ),
            }
        }
    context = lint_context(root)
    skills = lint_skills(root)
    counts = {
        "context_errors": context.error_count,
        "skill_errors": skills.error_count,
        "compatibility_errors": compatibility.error_count,
    }
    has_errors = any(counts.values())
    counts.update(
        {
            "context_warnings": context.warning_count,
            "skill_warnings": skills.warning_count,
            "compatibility_warnings": len(compatibility.findings) - compatibility.error_count,
        }
    )
    report_path = root / HOOK_REPORT_RELATIVE
    if not report_path.resolve().is_relative_to(root):
        raise CliError(
            "Hook report path leaves the project.", "Keep .coding-scaffold local to this worktree."
        )
    # Only aggregate local results. No session IDs, user text, commands or tool outputs.
    write_json(
        report_path,
        {
            "schema_version": 1,
            "event": "Stop",
            "checks": counts,
            "checked_at": datetime.now(UTC).isoformat(),
            "project_tests_run": False,
        },
    )
    if has_errors:
        reason = (
            "CodingScaffold found metadata errors. Run context lint, skills lint, and "
            "tools compatibility for details; fix errors relevant to this change."
        )
        if not payload.get("stop_hook_active"):
            return {"decision": "block", "reason": reason}
        return {"systemMessage": reason + " Automatic continuation is limited to one attempt."}
    return {}
