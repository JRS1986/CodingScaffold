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
    tool: str
    environment_ok: bool
    environment: dict[str, object]
    steps: list[str]
    ignore_for_now: list[str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "tool": self.tool,
            "environment_ok": self.environment_ok,
            "environment": dict(self.environment),
            "steps": list(self.steps),
            "ignore_for_now": list(self.ignore_for_now),
            "warnings": list(self.warnings),
        }


def run_pilot(target: Path | None = None, tool: str = "opencode") -> PilotReport:
    """Build a structured PilotReport. Read-only — no commands are executed beyond
    `probe_hardware()` (which itself is a local inspection)."""

    root = (target or Path.cwd()).expanduser().resolve()
    if tool not in SUPPORTED_TOOLS:
        raise ValueError(
            f"Unknown tool {tool!r}. Choose from: {', '.join(SUPPORTED_TOOLS)}."
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

    # 4. Selected tool present on PATH? (No install.)
    tool_binary = TOOL_BINARY_NAMES.get(tool, tool)
    tool_present = shutil.which(tool_binary) is not None
    env_info["tool"] = {"name": tool, "binary": tool_binary, "installed": tool_present}
    if not tool_present:
        warnings.append(
            f"`{tool_binary}` is not on PATH. The setup step below offers --install-tools "
            "to add it; "
            "this pilot wrapper never installs anything itself."
        )

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
        and tool_present
        and (bool(found_keys) or bool(local_runtime_binaries))
    )

    # Build the printable recipe. Same shape regardless of tool, with the tool name woven in.
    steps = _build_steps(root, tool=tool, tool_present=tool_present)

    return PilotReport(
        target=str(root),
        tool=tool,
        environment_ok=environment_ok,
        environment=env_info,
        steps=steps,
        ignore_for_now=list(IGNORE_FOR_NOW),
        warnings=warnings,
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
    lines.append(f"Tool: {report.tool}")
    lines.append(f"Environment OK: {'yes' if report.environment_ok else 'no'}")
    lines.append("")
    lines.append("Environment check:")
    env = report.environment
    lines.append(f"  - Python: {env.get('python')}")
    lines.append(f"  - OS: {env.get('os')}")
    lines.append(f"  - git on PATH: {env.get('git')}")
    tool_info = env.get("tool")
    if isinstance(tool_info, dict):
        installed = tool_info.get("installed")
        binary = tool_info.get("binary")
        lines.append(f"  - {report.tool} ({binary}) installed: {installed}")
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
