from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolInstallPlan:
    tool: str
    executable: str
    detected: bool
    install_command: list[str]
    install_description: str
    post_install: str


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
) -> list[ToolInstallResult]:
    results: list[ToolInstallResult] = []
    for plan in build_install_plans(selection):
        if plan.detected:
            results.append(ToolInstallResult(plan.tool, "present", f"{plan.executable} is already installed."))
            continue
        if not interactive and not assume_yes:
            results.append(
                ToolInstallResult(
                    plan.tool,
                    "missing",
                    f"{plan.executable} is not installed. Run: {' '.join(plan.install_command)}",
                )
            )
            continue
        if not assume_yes and not _confirm_install(plan):
            results.append(ToolInstallResult(plan.tool, "skipped", f"Skipped installing {plan.tool}."))
            continue
        try:
            completed = subprocess.run(plan.install_command, check=False)
        except OSError as exc:
            results.append(
                ToolInstallResult(
                    plan.tool,
                    "failed",
                    f"Could not start installer for {plan.tool}: {exc}",
                )
            )
            continue
        if completed.returncode == 0:
            results.append(ToolInstallResult(plan.tool, "installed", plan.post_install))
        else:
            results.append(
                ToolInstallResult(
                    plan.tool,
                    "failed",
                    f"{plan.tool} installer exited with code {completed.returncode}.",
                )
            )
    return results


def _plan_for(tool: str) -> ToolInstallPlan:
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


def _confirm_install(plan: ToolInstallPlan) -> bool:
    command = " ".join(plan.install_command)
    answer = input(
        f"{plan.executable} was not found. {plan.install_description}\n"
        f"Command: {command}\n"
        "Install now? [y/N]: "
    ).strip()
    return answer.lower() in {"y", "yes"}
