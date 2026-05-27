"""`coding-scaffold pilot` — safe guided wrapper for the 10-minute happy path.

The pilot command runs only **read-only local checks** and then prints the exact commands a
new user should run next. It deliberately does not install tools, does not edit files, and
does not call any model. The whole point is progressive disclosure: a new user should walk
away knowing the three commands they need today.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .hardware import probe_hardware
from .personas import DEFAULT_PERSONA, PERSONAS, get_persona


SUPPORTED_TOOLS: tuple[str, ...] = (
    "opencode",
    "claude-code",
    "codex",
    "openclaude",
    "hermes",
    "pi",
)

# Tools whose Python-launchable binary lives on PATH under a known name. Used only for the
# "is the tool installed?" read-only check — not for installation.
TOOL_BINARY_NAMES: dict[str, str] = {
    "opencode": "opencode",
    "claude-code": "claude",
    "codex": "codex",
    "openclaude": "openclaude",
    "hermes": "hermes",
    "pi": "pi",
}

# Advanced surfaces the pilot script omits from the recommendation list.
IGNORE_FOR_NOW: tuple[str, ...] = (
    "policy",
    "mcp",
    "skills",
    "memory",
    "team",
    "permissions write",
    "tools route",
)


@dataclass(frozen=True)
class PilotReport:
    target: str
    tools: list[str]              # was: tool: str
    environment_ok: bool
    environment: dict[str, object]
    steps: list[str]
    ignore_for_now: list[str]
    warnings: list[str] = field(default_factory=list)
    persona: str = DEFAULT_PERSONA

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "tools": list(self.tools),
            "persona": self.persona,
            "environment_ok": self.environment_ok,
            "environment": dict(self.environment),
            "steps": list(self.steps),
            "ignore_for_now": list(self.ignore_for_now),
            "warnings": list(self.warnings),
        }


def run_pilot(
    target: Path | None = None,
    *,
    tool: str | None = None,
    tools: list[str] | None = None,
    persona: str = DEFAULT_PERSONA,
) -> PilotReport:
    """Build a structured PilotReport. Read-only — no commands are executed beyond
    `probe_hardware()` (which itself is a local inspection).

    Pass ``tools=[...]`` for multi-tool projects. The ``tool=`` kwarg is
    preserved for backward-compatible callers; it is normalized via
    ``normalize_tools`` so legacy passes like ``tool="opencode"`` keep working.
    """

    from .errors import CliError
    from .intake import normalize_tools

    try:
        if tools is not None:
            canonical = normalize_tools(tools)
        elif tool is not None:
            canonical = normalize_tools(tool)
        else:
            canonical = normalize_tools("opencode")
    except CliError as exc:
        raise ValueError(f"Unknown tool — {exc.cause}") from exc

    root = (target or Path.cwd()).expanduser().resolve()
    if persona not in PERSONAS:
        raise ValueError(
            f"Unknown persona {persona!r}. Choose from: {', '.join(PERSONAS)}."
        )

    warnings: list[str] = []
    env_info: dict[str, object] = {}

    # 1. Python version check.
    py = sys.version_info
    env_info["python"] = f"{py.major}.{py.minor}.{py.micro}"
    python_ok = (py.major, py.minor) >= (3, 11)
    if not python_ok:
        warnings.append(
            f"Python {py.major}.{py.minor} detected; the scaffold requires Python 3.11+."
        )

    # 2. Hardware probe (read-only).
    hardware = probe_hardware()
    env_info["os"] = hardware.os_name
    env_info["wsl"] = hardware.is_wsl

    # 3. git availability.
    git_path = shutil.which("git")
    env_info["git"] = bool(git_path)
    if not git_path:
        warnings.append("git is not on PATH. `setup run` and `session start` need it.")

    # 4. Selected tools present on PATH? (No install.) One entry per tool.
    per_tool_info: list[dict[str, object]] = []
    for t in canonical:
        binary = TOOL_BINARY_NAMES.get(t, t)
        installed = shutil.which(binary) is not None
        per_tool_info.append({"name": t, "binary": binary, "installed": installed})
        if not installed:
            warnings.append(
                f"`{binary}` is not on PATH. The setup step below offers --install-tools "
                "to add it; "
                "this pilot wrapper never installs anything itself."
            )
    env_info["tools"] = per_tool_info
    all_tools_installed = all(entry["installed"] for entry in per_tool_info)

    # 5. Any credential or local runtime path. Don't run providers.detect_providers — it
    # probes endpoints, which is more than this safe wrapper should do.
    cred_keys = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN")
    found_keys = [k for k in cred_keys if os.environ.get(k)]
    env_info["credentials_in_env"] = list(found_keys)
    local_runtime_binaries = [
        name for name in ("ollama", "lmstudio", "llama-server") if shutil.which(name)
    ]
    env_info["local_runtime_cli"] = local_runtime_binaries
    if not found_keys and not local_runtime_binaries:
        warnings.append(
            "No credentials in env and no local runtime CLI found. The agent step at the end "
            "of the path needs at least one model path; set OPENAI_API_KEY / ANTHROPIC_API_KEY "
            "or install Ollama before running it."
        )

    environment_ok = (
        python_ok
        and bool(git_path)
        and all_tools_installed
        and (bool(found_keys) or bool(local_runtime_binaries))
    )

    # Build the printable recipe. Shape depends on whether single- or multi-tool.
    if persona == DEFAULT_PERSONA:
        if len(canonical) == 1:
            # Single-tool: preserve today's 3-step recipe verbatim (golden test path).
            t = canonical[0]
            tool_present = per_tool_info[0]["installed"]
            assert isinstance(tool_present, bool)
            steps = _build_steps(root, tool=t, tool_present=tool_present)
        else:
            # Multi-tool: shared setup + per-tool agent lines.
            any_missing = not all_tools_installed
            steps = _build_multi_tool_steps(root, tools=canonical, any_missing=any_missing)
        ignore = list(IGNORE_FOR_NOW)
    else:
        focus = get_persona(persona)
        steps = list(focus.next_commands)[:3]
        ignore = list(focus.ignore_for_now)
        warnings.insert(0, f"Persona: {focus.title} — {focus.focus}")

    return PilotReport(
        target=str(root),
        tools=canonical,
        environment_ok=environment_ok,
        environment=env_info,
        steps=steps,
        ignore_for_now=ignore,
        warnings=warnings,
        persona=persona,
    )


def _build_steps(root: Path, *, tool: str, tool_present: bool) -> list[str]:
    setup_args = f"--target {_format_target(root)} --tool {tool} --mode beginner"
    if not tool_present:
        setup_args += " --install-tools"
    return [
        f"coding-scaffold setup run {setup_args}",
        f"coding-scaffold pr-template init --target {_format_target(root)}",
        (
            f"{TOOL_BINARY_NAMES.get(tool, tool)}   "
            "# inside the agent: run /first-session (inspect-only), then /agentic-change"
        ),
    ]


def _build_multi_tool_steps(
    root: Path, *, tools: list[str], any_missing: bool
) -> list[str]:
    """Build the multi-tool recipe: shared setup step + per-tool agent lines."""
    tools_flag = ",".join(tools)
    setup_args = f"--target {_format_target(root)} --tool {tools_flag} --mode beginner"
    if any_missing:
        setup_args += " --install-tools"
    steps = [
        f"coding-scaffold setup run {setup_args}",
        f"coding-scaffold pr-template init --target {_format_target(root)}",
    ]
    # Per-tool agent lines (will be rendered specially by format_pilot_text)
    for t in tools:
        binary = TOOL_BINARY_NAMES.get(t, t)
        steps.append(
            f"{binary}   "
            "# inside the agent: /first-session, then /agentic-change"
        )
    return steps


def _format_target(root: Path) -> str:
    """Print `.` for the cwd, else the absolute path. Keeps the recipe scannable."""

    try:
        if root == Path.cwd().resolve():
            return "."
    except OSError:
        pass
    return str(root)


def format_pilot_text(report: PilotReport) -> str:
    """Render the report as human-readable text. Stable for golden tests."""

    lines: list[str] = []
    lines.append(f"CodingScaffold pilot — 10-minute happy path for {report.target}")
    lines.append("")

    multi_tool = len(report.tools) > 1

    if multi_tool:
        lines.append(f"Tools: {', '.join(report.tools)}")
    else:
        # Single-tool: original format — "Tool: <name>"
        lines.append(f"Tool: {report.tools[0]}")

    lines.append(f"Environment OK: {'yes' if report.environment_ok else 'no'}")
    lines.append("")
    lines.append("Environment check:")
    env = report.environment
    lines.append(f"  - Python: {env.get('python')}")
    lines.append(f"  - OS: {env.get('os')}")
    lines.append(f"  - git on PATH: {env.get('git')}")

    # Per-tool installed lines
    tool_entries = env.get("tools")
    if isinstance(tool_entries, list):
        for entry in tool_entries:
            if isinstance(entry, dict):
                name = entry.get("name")
                binary = entry.get("binary")
                installed = entry.get("installed")
                # Render as Python bool to preserve the historic single-tool
                # format (`installed: True` / `installed: False`). The
                # multi-tool case inherits the same rendering for consistency.
                lines.append(f"  - {name} ({binary}) installed: {installed}")

    creds = env.get("credentials_in_env") or []
    if isinstance(creds, list) and creds:
        lines.append(f"  - Credentials in env: {', '.join(str(k) for k in creds)}")
    else:
        lines.append("  - Credentials in env: none")
    runtimes = env.get("local_runtime_cli") or []
    if isinstance(runtimes, list) and runtimes:
        lines.append(f"  - Local runtime CLI: {', '.join(str(r) for r in runtimes)}")
    lines.append("")
    if report.warnings:
        lines.append("Warnings:")
        for warning in report.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    if multi_tool:
        # Multi-tool format: shared setup steps, then per-tool agent lines
        # Steps layout: [0] = setup run, [1] = pr-template init, [2..] = per-tool binaries
        shared_steps = report.steps[:2]
        agent_steps = report.steps[2:]
        lines.append("Run these once (covers all selected tools):")
        for i, step in enumerate(shared_steps, start=1):
            lines.append(f"  {i}. {step}")
        lines.append("")
        lines.append("Then start a session with whichever tool you reach for today:")
        for step in agent_steps:
            lines.append(f"  {step}")
    else:
        # Single-tool: original 3-step format
        lines.append("Run these next (in order):")
        for i, step in enumerate(report.steps, start=1):
            lines.append(f"  {i}. {step}")

    lines.append("")
    lines.append("After the steps:")
    lines.append("  - Review the diff before merging.")
    lines.append("  - Run `coding-scaffold doctor` for the next thing to do.")
    lines.append("")
    lines.append("Ignore for now (advanced):")
    lines.append(f"  {', '.join(report.ignore_for_now)}")
    return "\n".join(lines)
