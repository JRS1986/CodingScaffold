from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_INSTALL_TIMEOUT_SECONDS = 300
_CAPTURED_OUTPUT_LIMIT = 4096


def _format_captured_output(completed: subprocess.CompletedProcess) -> str:
    parts: list[str] = []
    stdout = (completed.stdout or "").strip() if isinstance(completed.stdout, str) else ""
    stderr = (completed.stderr or "").strip() if isinstance(completed.stderr, str) else ""
    if stdout:
        parts.append(f"stdout:\n{stdout}")
    if stderr:
        parts.append(f"stderr:\n{stderr}")
    combined = "\n".join(parts)
    if len(combined) > _CAPTURED_OUTPUT_LIMIT:
        combined = combined[-_CAPTURED_OUTPUT_LIMIT:]
        combined = f"...(truncated)\n{combined}"
    return combined


@dataclass(frozen=True)
class ToolInstallPlan:
    tool: str
    executable: str
    detected: bool
    install_command: list[str]
    install_description: str
    post_install: str
    cwd: Path | None = None
    installable: bool = True


@dataclass(frozen=True)
class ToolInstallResult:
    tool: str
    status: str
    message: str


def build_install_plans(selection: str) -> list[ToolInstallPlan]:
    tools = ["opencode", "openclaude"] if selection == "both" else [selection]
    return [_plan_for(tool) for tool in tools if tool != "manual"]


def install_missing_tools(
    selection: str,
    interactive: bool,
    assume_yes: bool = False,
    target: Path | None = None,
) -> list[ToolInstallResult]:
    results: list[ToolInstallResult] = []
    for plan in build_install_plans(selection):
        results.append(_install_plan(plan, interactive, assume_yes, target))
    return results


def build_addon_install_plans(selection: str, target: Path | None = None) -> list[ToolInstallPlan]:
    addons = (
        ["llmfit", "routellm", "open-multi-agent", "obsidian", "caveman-compression"]
        if selection == "all"
        else [selection]
    )
    return [_addon_plan_for(addon, target) for addon in addons]


def install_missing_addons(
    selection: str,
    interactive: bool,
    assume_yes: bool = False,
    target: Path | None = None,
) -> list[ToolInstallResult]:
    results: list[ToolInstallResult] = []
    for plan in build_addon_install_plans(selection, target):
        results.append(_install_plan(plan, interactive, assume_yes, target))
    return results


def _plan_for(tool: str) -> ToolInstallPlan:
    if tool == "claude-code":
        return ToolInstallPlan(
            tool="claude-code",
            executable="claude",
            detected=shutil.which("claude") is not None,
            install_command=["npm", "install", "-g", "@anthropic-ai/claude-code"],
            install_description="Install Claude Code globally with npm.",
            post_install="Claude Code installed. Start it in a project with: claude",
        )
    if tool == "codex":
        return ToolInstallPlan(
            tool="codex",
            executable="codex",
            detected=shutil.which("codex") is not None,
            install_command=["npm", "install", "-g", "@openai/codex"],
            install_description="Install OpenAI Codex CLI globally with npm.",
            post_install="Codex installed. Start it in a project with: codex",
        )
    if tool == "hermes":
        return ToolInstallPlan(
            tool="hermes",
            executable="hermes",
            detected=shutil.which("hermes") is not None,
            install_command=[
                "bash",
                "-lc",
                "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash",
            ],
            install_description="Install Hermes Agent with the official installer.",
            post_install="Hermes installed. Configure it with `hermes setup`, then start it with: hermes",
        )
    if tool == "pi":
        return ToolInstallPlan(
            tool="pi",
            executable="pi",
            detected=shutil.which("pi") is not None,
            install_command=["npm", "install", "-g", "@earendil-works/pi-coding-agent"],
            install_description="Install Pi Coding Agent globally with npm.",
            post_install="Pi installed. Start it in a project with: pi",
        )
    if tool == "openclaude":
        return ToolInstallPlan(
            tool="openclaude",
            executable="openclaude",
            detected=shutil.which("openclaude") is not None,
            install_command=["npm", "install", "-g", "@gitlawb/openclaude"],
            install_description="Install OpenClaude globally with npm.",
            post_install="OpenClaude installed. Start it with: openclaude",
        )
    return ToolInstallPlan(
        tool="opencode",
        executable="opencode",
        detected=shutil.which("opencode") is not None,
        install_command=["bash", "-lc", "curl -fsSL https://opencode.ai/install | bash"],
        install_description="Install OpenCode with the official install script.",
        post_install="OpenCode installed. Start it with: opencode",
    )


def _addon_plan_for(addon: str, target: Path | None = None) -> ToolInstallPlan:
    root = target.expanduser().resolve() if target else Path.cwd()
    if addon == "llmfit":
        if shutil.which("brew"):
            command = ["brew", "install", "llmfit"]
            description = "Install llmfit with Homebrew for hardware-aware local model fitting."
        else:
            command = ["bash", "-lc", "curl -fsSL https://llmfit.axjns.dev/install.sh | sh"]
            description = "Install llmfit with the official quick install script."
        return ToolInstallPlan(
            tool="llmfit",
            executable="llmfit",
            detected=shutil.which("llmfit") is not None,
            install_command=command,
            install_description=description,
            post_install="llmfit installed. Run hardware checks with: llmfit",
        )
    if addon == "routellm":
        return ToolInstallPlan(
            tool="routellm",
            executable="python package routellm",
            detected=importlib.util.find_spec("routellm") is not None,
            install_command=[sys.executable, "-m", "pip", "install", "routellm[serve,eval]"],
            install_description="Install RouteLLM into the active Python environment.",
            post_install="RouteLLM installed. Generate config with: coding-scaffold route --target .",
        )
    if addon == "open-multi-agent":
        return ToolInstallPlan(
            tool="open-multi-agent",
            executable="node package @jackchen_me/open-multi-agent",
            detected=(root / "node_modules" / "@jackchen_me" / "open-multi-agent").exists(),
            install_command=["npm", "install", "@jackchen_me/open-multi-agent"],
            install_description="Install Open Multi-Agent into the target Node.js project.",
            post_install="Open Multi-Agent installed. Generate workflow files with: coding-scaffold workflow --target .",
            cwd=root,
        )
    if addon == "caveman-compression":
        tools_dir = root / ".coding-scaffold" / "tools"
        tool_dir = tools_dir / "caveman-compression"
        return ToolInstallPlan(
            tool="caveman-compression",
            executable="local clone .coding-scaffold/tools/caveman-compression",
            detected=tool_dir.exists(),
            install_command=[
                "git",
                "clone",
                "https://github.com/wilpel/caveman-compression.git",
                "caveman-compression",
            ],
            install_description="Clone Caveman Compression for optional token-saving context compression.",
            post_install=(
                "Caveman Compression cloned. Try scaffold sidecars with: "
                "coding-scaffold compress-context --target ."
            ),
            cwd=tools_dir,
        )
    return _obsidian_plan()


def _obsidian_plan() -> ToolInstallPlan:
    detected = shutil.which("obsidian") is not None
    if _is_wsl():
        return ToolInstallPlan(
            tool="obsidian",
            executable="obsidian",
            detected=detected,
            install_command=[],
            install_description=(
                "Obsidian is a desktop app. In WSL, install it on Windows and open "
                ".coding-scaffold/knowledge as a vault."
            ),
            post_install="Open .coding-scaffold/knowledge as an Obsidian vault.",
            installable=False,
        )
    if platform.system() == "Darwin" and shutil.which("brew"):
        return ToolInstallPlan(
            tool="obsidian",
            executable="obsidian",
            detected=detected,
            install_command=["brew", "install", "--cask", "obsidian"],
            install_description="Install the Obsidian desktop app with Homebrew Cask.",
            post_install="Obsidian installed. Open .coding-scaffold/knowledge as a vault.",
        )
    if shutil.which("snap"):
        return ToolInstallPlan(
            tool="obsidian",
            executable="obsidian",
            detected=detected,
            install_command=["sudo", "snap", "install", "obsidian", "--classic"],
            install_description="Install the Obsidian desktop app from Snap.",
            post_install="Obsidian installed. Open .coding-scaffold/knowledge as a vault.",
        )
    return ToolInstallPlan(
        tool="obsidian",
        executable="obsidian",
        detected=detected,
        install_command=[],
        install_description=(
            "Obsidian was not found and no supported installer was detected. Install it from "
            "https://obsidian.md/download and open .coding-scaffold/knowledge as a vault."
        ),
        post_install="Open .coding-scaffold/knowledge as an Obsidian vault.",
        installable=False,
    )


def _install_plan(
    plan: ToolInstallPlan,
    interactive: bool,
    assume_yes: bool,
    target: Path | None = None,
) -> ToolInstallResult:
    if plan.detected:
        return ToolInstallResult(plan.tool, "present", f"{plan.executable} is already installed.")
    if not plan.installable:
        return ToolInstallResult(plan.tool, "manual", plan.install_description)
    if not interactive and not assume_yes:
        return ToolInstallResult(
            plan.tool,
            "missing",
            f"{plan.executable} is not installed. Run: {' '.join(plan.install_command)}",
        )
    if not assume_yes and not _confirm_install(plan):
        return ToolInstallResult(plan.tool, "skipped", f"Skipped installing {plan.tool}.")
    cwd = plan.cwd or (target.expanduser().resolve() if target else None)
    capture = not interactive
    try:
        if cwd:
            cwd.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            plan.install_command,
            check=False,
            cwd=cwd,
            timeout=_INSTALL_TIMEOUT_SECONDS,
            capture_output=capture,
            text=capture,
        )
    except subprocess.TimeoutExpired:
        return ToolInstallResult(
            plan.tool,
            "failed",
            (
                f"{plan.tool} installer timed out after "
                f"{_INSTALL_TIMEOUT_SECONDS} seconds."
            ),
        )
    except OSError as exc:
        return ToolInstallResult(
            plan.tool,
            "failed",
            f"Could not start installer for {plan.tool}: {exc}",
        )
    if completed.returncode == 0:
        if plan.tool == "caveman-compression" and cwd:
            shutil.rmtree(cwd / "caveman-compression" / ".git", ignore_errors=True)
        return ToolInstallResult(plan.tool, "installed", plan.post_install)
    message = f"{plan.tool} installer exited with code {completed.returncode}."
    if capture:
        output = _format_captured_output(completed)
        if output:
            message = f"{message}\n{output}"
    return ToolInstallResult(
        plan.tool,
        "failed",
        message,
    )


def _confirm_install(plan: ToolInstallPlan) -> bool:
    command = " ".join(plan.install_command)
    answer = input(
        f"{plan.executable} was not found. {plan.install_description}\n"
        f"Command: {command}\n"
        "Install now? [y/N]: "
    ).strip()
    return answer.lower() in {"y", "yes"}


def _is_wsl() -> bool:
    if platform.system() != "Linux":
        return False
    try:
        version = Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "microsoft" in version or "wsl" in version
