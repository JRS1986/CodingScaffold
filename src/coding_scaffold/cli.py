from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import write_route_backend, write_tool_adapter, write_workflow_backend
from .credentials import load_local_credentials, write_local_credential_file
from .enablement import write_orchestration_plan, write_skill_template
from .hardware import probe_hardware
from .installers import install_missing_addons, install_missing_tools
from .intake import IntakeAnswers, collect_intake
from .knowledge import write_knowledge_base
from .model_selection import select_model_for_prompt
from .policy import write_policy_pack
from .providers import detect_providers
from .router import RoutingPlan, build_routing_plan
from .routing_io import load_routing_plan
from .team import connect_team, doctor_team, sync_team, write_team_manifest
from .writers import write_scaffold


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coding-scaffold",
        description="Prepare a local-first AI coding scaffold for a project.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="Inspect hardware and provider availability.")
    probe.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    probe.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")

    init = sub.add_parser("init", help="Create or update .coding-scaffold in a project.")
    init.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    init.add_argument("--language", help="Primary language, e.g. python, rust, typescript.")
    init.add_argument("--project-target", help="Target kind, e.g. CLI, web app, library.")
    init.add_argument("--existing-codebase", action="store_true", help="Project already has code.")
    init.add_argument("--privacy", choices=["local-only", "local-first", "balanced"], default=None)
    init.add_argument("--agent", choices=["opencode", "openclaude", "both", "manual"], default=None)
    init.add_argument("--coding-tool", choices=["opencode", "openclaude", "both", "manual"], dest="agent")
    init.add_argument("--preferred-local-model", help="Preferred local model name.")
    init.add_argument("--mode", choices=["standard", "beginner"], default=None)
    init.add_argument("--non-interactive", action="store_true", help="Use defaults for missing values.")
    init.add_argument("--install-tools", action="store_true", help="Install the selected coding tool if missing.")
    init.add_argument(
        "--addon",
        action="append",
        choices=["llmfit", "routellm", "open-multi-agent", "obsidian", "all"],
        default=[],
        help="Validate or install an optional add-on. Repeat for multiple add-ons.",
    )
    init.add_argument("--install-addons", action="store_true", help="Install selected add-ons if missing.")
    init.add_argument(
        "--knowledge-backend",
        choices=["none", "markdown", "obsidian", "mempalace"],
        default=None,
        help="Configure shared knowledge during setup.",
    )
    init.add_argument("--knowledge-remote", help="GitHub/GitLab remote URL for shared knowledge.")

    wizard = sub.add_parser("wizard", help="Guided setup wizard for a project.")
    wizard.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    wizard.add_argument("--beginner", action="store_true", help="Include a first-project guide.")
    wizard.add_argument("--coding-tool", choices=["opencode", "openclaude", "both", "manual"], dest="agent")
    wizard.add_argument("--install-tools", action="store_true", help="Install the selected coding tool if missing.")
    wizard.add_argument("--no-install-tools", action="store_true", help="Do not offer coding tool installation.")
    wizard.add_argument(
        "--addon",
        action="append",
        choices=["llmfit", "routellm", "open-multi-agent", "obsidian", "all"],
        default=[],
        help="Validate or install an optional add-on. Repeat for multiple add-ons.",
    )
    wizard.add_argument("--install-addons", action="store_true", help="Install selected add-ons if missing.")
    wizard.add_argument("--no-install-addons", action="store_true", help="Do not offer optional add-on setup.")
    wizard.add_argument(
        "--knowledge-backend",
        choices=["none", "markdown", "obsidian", "mempalace"],
        default=None,
        help="Configure shared knowledge during setup.",
    )
    wizard.add_argument("--knowledge-remote", help="GitHub/GitLab remote URL for shared knowledge.")
    wizard.add_argument("--no-knowledge", action="store_true", help="Do not offer knowledge setup.")

    credentials = sub.add_parser("credentials", help="Create ignored local credential files.")
    credentials.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    credentials.add_argument("--format", choices=["env", "json"], default="env")

    skill = sub.add_parser("skill", help="Create a reusable project skill template.")
    skill.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    skill.add_argument("--name", required=True, help="Skill name, e.g. Release Review.")
    skill.add_argument("--description", default="", help="Short description for when to use it.")
    skill.add_argument("--adapter", choices=["none", "opencode"], default="none")

    knowledge = sub.add_parser("knowledge", help="Create a shared team knowledge base.")
    knowledge.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    knowledge.add_argument("--backend", choices=["markdown", "obsidian", "mempalace"], default="markdown")
    knowledge.add_argument("--shared-remote", help="Optional GitHub/GitLab repo URL for team memory.")
    knowledge.add_argument("--adapter", choices=["none", "opencode"], default="opencode")

    orchestrate = sub.add_parser("orchestrate", help="Create an agent orchestration plan.")
    orchestrate.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    orchestrate.add_argument("--profile", choices=["solo", "pair", "team"], default="pair")
    orchestrate.add_argument("--adapter", choices=["none", "opencode"], default="opencode")

    setup_tool = sub.add_parser("setup-tool", help="Install or validate a coding environment.")
    setup_tool.add_argument("--tool", choices=["opencode", "openclaude", "both"], default="opencode")
    setup_tool.add_argument(
        "--install",
        action="store_true",
        help="Install missing tools without an extra prompt when stdin is not interactive.",
    )

    setup_addon = sub.add_parser("setup-addon", help="Install or validate optional scaffold add-ons.")
    setup_addon.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    setup_addon.add_argument(
        "--addon",
        choices=["llmfit", "routellm", "open-multi-agent", "obsidian", "all"],
        default="llmfit",
    )
    setup_addon.add_argument(
        "--install",
        action="store_true",
        help="Install missing add-ons without an extra prompt when stdin is not interactive.",
    )

    setup_knowledge = sub.add_parser("setup-knowledge", help="Configure shared team knowledge.")
    setup_knowledge.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    setup_knowledge.add_argument(
        "--backend",
        choices=["markdown", "obsidian", "mempalace"],
        default="markdown",
        help="Knowledge backend to generate.",
    )
    setup_knowledge.add_argument("--shared-remote", help="GitHub/GitLab repo URL for shared knowledge.")
    setup_knowledge.add_argument("--adapter", choices=["none", "opencode"], default="opencode")

    team = sub.add_parser("team", help="Manage experienced-team onboarding assets.")
    team.add_argument("action", choices=["init", "connect", "sync", "doctor"])
    team.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    team.add_argument("--manifest", help="Local manifest file or Git repo containing team-onboarding.json.")
    team.add_argument("--team", default="team", help="Team name for `team init`.")
    team.add_argument("--knowledge-remote", help="Shared knowledge Git remote for `team init`.")
    team.add_argument(
        "--knowledge-backend",
        choices=["markdown", "obsidian", "mempalace"],
        default="markdown",
        help="Knowledge backend for `team init`.",
    )
    team.add_argument(
        "--tool",
        choices=["opencode", "openclaude", "both", "manual"],
        default="opencode",
        help="Default coding tool for `team init`.",
    )

    policy = sub.add_parser("policy", help="Create company/unit/team policy config.")
    policy.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    policy.add_argument(
        "--scope",
        choices=["company", "unit", "department", "team"],
        default="company",
        help="Audience and ownership layer for this policy.",
    )
    policy.add_argument("--adapter", choices=["none", "opencode"], default="opencode")
    policy.add_argument("--share", choices=["disabled", "manual", "auto"], default="disabled")
    policy.add_argument(
        "--mcp",
        choices=["project-empty", "keep"],
        default="project-empty",
        help="Project MCP default. Use disable-mcp-server for named inherited servers.",
    )
    policy.add_argument(
        "--enable-provider",
        action="append",
        default=[],
        help="Allowlist an OpenCode provider id. Repeat for multiple providers.",
    )
    policy.add_argument(
        "--disable-provider",
        action="append",
        default=[],
        help="Disable an OpenCode provider id. Repeat for multiple providers.",
    )
    policy.add_argument(
        "--disable-mcp-server",
        action="append",
        default=[],
        help="Disable a named OpenCode MCP server. Repeat for multiple servers.",
    )
    policy.add_argument(
        "--relaxed-permissions",
        action="store_true",
        help="Do not force edit/bash approval in generated OpenCode policy.",
    )

    adapt = sub.add_parser("adapt", help="Generate native config for a coding tool.")
    adapt.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    adapt.add_argument("--tool", choices=["opencode", "openclaude", "both"], default="opencode")

    route = sub.add_parser("route", help="Generate optional routing backend docs/config.")
    route.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    route.add_argument("--backend", choices=["routellm"], default="routellm")

    select = sub.add_parser("select-model", help="Recommend a model route for a prompt.")
    select.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    select.add_argument("--prompt", help="Prompt or task description to classify.")
    select.add_argument("--mode", choices=["recommend", "auto"], default="recommend")
    select.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    workflow = sub.add_parser("workflow", help="Generate optional workflow backend docs/config.")
    workflow.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    workflow.add_argument("--backend", choices=["open-multi-agent"], default="open-multi-agent")

    sub.add_parser("doctor", help="Print setup recommendations.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "probe":
        target = args.target.expanduser().resolve()
        hardware = probe_hardware()
        providers = detect_providers(load_local_credentials(target), include_copilot=True)
        payload = {"hardware": hardware.to_dict(), "providers": [p.to_dict() for p in providers]}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            _print_probe(payload)
        return 0

    if args.command == "doctor":
        _print_doctor()
        return 0

    if args.command == "credentials":
        path = write_local_credential_file(args.target, args.format)
        print(f"Wrote local credential template to {path}")
        print("Fill values locally. Do not commit this file.")
        return 0

    if args.command == "skill":
        adapter = None if args.adapter == "none" else args.adapter
        path = write_skill_template(args.target, args.name, args.description, adapter)
        print(f"Wrote project skill template to {path}")
        return 0

    if args.command == "knowledge":
        adapter = None if args.adapter == "none" else args.adapter
        result = write_knowledge_base(args.target, args.backend, args.shared_remote, adapter)
        print(f"Wrote {len(result.files)} knowledge file(s).")
        if result.skipped:
            print(f"Skipped {len(result.skipped)} existing knowledge file(s).")
        return 0

    if args.command == "orchestrate":
        adapter = None if args.adapter == "none" else args.adapter
        path = write_orchestration_plan(args.target, args.profile, adapter)
        print(f"Wrote agent orchestration plan to {path}")
        return 0

    if args.command == "setup-tool":
        results = install_missing_tools(
            args.tool,
            interactive=sys.stdin.isatty(),
            assume_yes=args.install,
        )
        for result in results:
            print(f"{result.tool}: {result.status} - {result.message}")
        return 1 if any(result.status == "failed" for result in results) else 0

    if args.command == "setup-addon":
        results = install_missing_addons(
            args.addon,
            interactive=sys.stdin.isatty(),
            assume_yes=args.install,
            target=args.target,
        )
        for result in results:
            print(f"{result.tool}: {result.status} - {result.message}")
        return 1 if any(result.status == "failed" for result in results) else 0

    if args.command == "setup-knowledge":
        shared_remote = args.shared_remote
        if shared_remote is None and sys.stdin.isatty():
            shared_remote = _prompt_optional(
                "Shared knowledge Git remote URL (empty keeps knowledge project-local)"
            )
        adapter = None if args.adapter == "none" else args.adapter
        result = write_knowledge_base(args.target, args.backend, shared_remote or None, adapter)
        print(f"Wrote {len(result.files)} knowledge file(s).")
        if shared_remote:
            print(f"Configured shared knowledge remote: {shared_remote}")
        if result.skipped:
            print(f"Skipped {len(result.skipped)} existing knowledge file(s).")
        return 0

    if args.command == "team":
        if args.action == "init":
            path = write_team_manifest(
                args.target,
                team=args.team,
                knowledge_remote=args.knowledge_remote,
                knowledge_backend=args.knowledge_backend,
                default_tool=args.tool,
            )
            print(f"Wrote team onboarding manifest to {path}")
            return 0
        if args.action == "connect":
            result = connect_team(args.target, args.manifest)
        elif args.action == "sync":
            result = sync_team(args.target)
        else:
            result = doctor_team(args.target)
        for action in result.actions:
            print(action)
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        return 1 if result.warnings and not result.actions else 0

    if args.command == "policy":
        adapter = None if args.adapter == "none" else args.adapter
        result = write_policy_pack(
            target=args.target,
            scope=args.scope,
            adapter=adapter,
            share=args.share,
            mcp=args.mcp,
            enabled_providers=args.enable_provider,
            disabled_providers=args.disable_provider or None,
            disabled_mcp_servers=args.disable_mcp_server,
            strict_permissions=not args.relaxed_permissions,
        )
        print(f"Wrote {len(result.files)} policy file(s).")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        return 0

    if args.command == "adapt":
        result = write_tool_adapter(args.target, args.tool)
        print(f"Wrote {len(result.files)} adapter file(s).")
        if result.skipped:
            print(f"Skipped {len(result.skipped)} existing file(s).")
        return 0

    if args.command == "route":
        result = write_route_backend(args.target, args.backend)
        print(f"Wrote {len(result.files)} routing backend file(s).")
        return 0

    if args.command == "select-model":
        target = args.target.expanduser().resolve()
        prompt = args.prompt
        if prompt is None and not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        if not prompt:
            print("Provide --prompt or pipe a task description into stdin.", file=sys.stderr)
            return 2
        routing = _load_routing_or_probe(target)
        providers = detect_providers(load_local_credentials(target))
        selection = select_model_for_prompt(prompt, routing, providers, args.mode)
        if args.json:
            print(json.dumps(selection.to_dict(), indent=2, sort_keys=True))
        else:
            _print_model_selection(selection.to_dict())
        return 0

    if args.command == "workflow":
        result = write_workflow_backend(args.target, args.backend)
        print(f"Wrote {len(result.files)} workflow backend file(s).")
        return 0

    if args.command in {"init", "wizard"}:
        target = args.target.expanduser().resolve()
        is_wizard = args.command == "wizard"
        answers = collect_intake(
            target=target,
            provided=IntakeAnswers(
                language=getattr(args, "language", None),
                project_target=getattr(args, "project_target", None),
                existing_codebase=getattr(args, "existing_codebase", False) or None,
                privacy=getattr(args, "privacy", None),
                agent=getattr(args, "agent", None),
                preferred_local_model=getattr(args, "preferred_local_model", None),
                mode="beginner" if getattr(args, "beginner", False) else getattr(args, "mode", None),
            ),
            interactive=(is_wizard or not getattr(args, "non_interactive", False)) and sys.stdin.isatty(),
        )
        hardware = probe_hardware()
        providers = detect_providers(load_local_credentials(target))
        routing = build_routing_plan(answers, hardware, providers)
        manifest = write_scaffold(target, answers, hardware, providers, routing)
        selected_tool = answers.agent or "opencode"
        install_results = _maybe_install_tools(selected_tool, args, is_wizard)
        addon_results = _maybe_install_addons(args, is_wizard, target)
        knowledge_result = _maybe_setup_knowledge(args, is_wizard, target, selected_tool)
        adapter = write_tool_adapter(target, selected_tool) if selected_tool != "manual" else None
        print(f"Wrote scaffold to {manifest.scaffold_dir}")
        if adapter:
            print(f"Wrote {len(adapter.files)} tool adapter file(s)")
        else:
            print("Skipped tool adapter generation.")
        for result in install_results:
            print(f"{result.tool}: {result.status} - {result.message}")
        for result in addon_results:
            print(f"{result.tool}: {result.status} - {result.message}")
        if knowledge_result:
            print(f"Wrote {len(knowledge_result.files)} knowledge file(s)")
            if knowledge_result.skipped:
                print(f"Skipped {len(knowledge_result.skipped)} existing knowledge file(s)")
        print(f"Selected weak model: {routing.weak_model or 'none'}")
        print(f"Selected strong model: {routing.strong_model or 'none'}")
        print("Next: read .coding-scaffold/GETTING_STARTED.md")
        return 0

    return 2


def _maybe_install_tools(
    selection: str,
    args: argparse.Namespace,
    is_wizard: bool,
):
    if selection == "manual":
        return []
    if getattr(args, "no_install_tools", False):
        return []
    should_offer = getattr(args, "install_tools", False) or (is_wizard and sys.stdin.isatty())
    if not should_offer:
        return []
    return install_missing_tools(
        selection,
        interactive=sys.stdin.isatty(),
        assume_yes=getattr(args, "install_tools", False),
    )


def _maybe_install_addons(
    args: argparse.Namespace,
    is_wizard: bool,
    target: Path,
):
    if getattr(args, "no_install_addons", False):
        return []
    selected = list(getattr(args, "addon", []) or [])
    if is_wizard and sys.stdin.isatty() and not selected:
        selected = _prompt_addons()
    if not selected:
        return []
    results = []
    for addon in selected:
        results.extend(
            install_missing_addons(
                addon,
                interactive=sys.stdin.isatty(),
                assume_yes=getattr(args, "install_addons", False),
                target=target,
            )
        )
    return results


def _prompt_addons() -> list[str]:
    answer = input(
        "Optional add-ons to validate/install "
        "(comma-separated: llmfit, routellm, open-multi-agent, obsidian, all; empty skips) []: "
    ).strip()
    if not answer:
        return []
    allowed = {"llmfit", "routellm", "open-multi-agent", "obsidian", "all"}
    return [part for part in (item.strip() for item in answer.split(",")) if part in allowed]


def _maybe_setup_knowledge(
    args: argparse.Namespace,
    is_wizard: bool,
    target: Path,
    selected_tool: str,
):
    if getattr(args, "no_knowledge", False):
        return None
    backend = getattr(args, "knowledge_backend", None)
    shared_remote = getattr(args, "knowledge_remote", None)
    if is_wizard and sys.stdin.isatty() and backend is None:
        backend = _prompt_choice(
            "Knowledge base backend (none/markdown/obsidian/mempalace)",
            "markdown",
            {"none", "markdown", "obsidian", "mempalace"},
        )
        if backend != "none" and shared_remote is None:
            shared_remote = _prompt_optional(
                "Shared knowledge Git remote URL (empty keeps knowledge project-local)"
            )
    if backend is None or backend == "none":
        return None
    adapter = "opencode" if selected_tool in {"opencode", "both"} else None
    return write_knowledge_base(target, backend, shared_remote or None, adapter)


def _prompt_choice(label: str, default: str, allowed: set[str]) -> str:
    answer = input(f"{label} [{default}]: ").strip().lower()
    if not answer:
        return default
    return answer if answer in allowed else default


def _prompt_optional(label: str) -> str:
    return input(f"{label}: ").strip()


def _print_probe(payload: dict[str, object]) -> None:
    hardware = payload["hardware"]
    providers = payload["providers"]
    assert isinstance(hardware, dict)
    print(f"OS: {hardware['os']} ({'WSL' if hardware['is_wsl'] else 'native'})")
    print(f"CPU cores: {hardware['cpu_count']}")
    print(f"RAM: {hardware['ram_gb']} GB")
    print(f"GPU: {hardware['gpu_name'] or 'not detected'}")
    print(f"VRAM: {hardware['vram_gb'] or 'unknown'} GB")
    print(f"llmfit: {'available' if hardware['llmfit_available'] else 'not found'}")
    print("Providers:")
    for provider in providers:
        print(f"  - {provider['name']}: {provider['status']}")


def _load_routing_or_probe(target: Path) -> RoutingPlan:
    plan = load_routing_plan(target)
    if plan:
        return plan
    return build_routing_plan(
        IntakeAnswers(privacy="local-first"),
        probe_hardware(),
        detect_providers(load_local_credentials(target)),
    )


def _print_model_selection(selection: dict[str, object]) -> None:
    print(f"Profile: {selection['prompt_profile']}")
    print(f"Route: {selection['route']}")
    print(f"Provider: {selection['provider']} ({selection['provider_kind']})")
    print(f"Model family: {selection['model_family'] or 'unknown'}")
    print(f"Model: {selection['model'] or 'configure-a-model'}")
    print(f"Confidence: {selection['confidence']}")
    print("Reasons:")
    for reason in selection["reasons"]:
        print(f"- {reason}")


def _print_doctor() -> None:
    hardware = probe_hardware()
    providers = detect_providers(load_local_credentials(Path.cwd()), include_copilot=True)
    print("CodingScaffold doctor")
    print(f"- Python package is runnable on {hardware.os_name}.")
    if not hardware.llmfit_available:
        print("- Install llmfit for deeper model sizing: brew install llmfit")
    if not any(p.name == "ollama" and p.available for p in providers):
        print("- Install or start Ollama if you want an easy local OpenAI-compatible path.")
    if not any(p.kind == "cloud" and p.available for p in providers):
        print("- No cloud credentials detected. That is fine for local-only use.")
