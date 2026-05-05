from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .credentials import load_local_credentials, write_local_credential_file
from .enablement import write_orchestration_plan, write_skill_template
from .hardware import probe_hardware
from .intake import IntakeAnswers, collect_intake
from .providers import detect_providers
from .router import build_routing_plan
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
    init.add_argument("--agent", choices=["opencode", "openclaude", "both"], default=None)
    init.add_argument("--preferred-local-model", help="Preferred local model name.")
    init.add_argument("--mode", choices=["standard", "beginner"], default=None)
    init.add_argument("--non-interactive", action="store_true", help="Use defaults for missing values.")

    wizard = sub.add_parser("wizard", help="Guided setup wizard for a project.")
    wizard.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    wizard.add_argument("--beginner", action="store_true", help="Include a first-project guide.")

    credentials = sub.add_parser("credentials", help="Create ignored local credential files.")
    credentials.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    credentials.add_argument("--format", choices=["env", "json"], default="env")

    skill = sub.add_parser("skill", help="Create a reusable project skill template.")
    skill.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    skill.add_argument("--name", required=True, help="Skill name, e.g. Release Review.")
    skill.add_argument("--description", default="", help="Short description for when to use it.")

    orchestrate = sub.add_parser("orchestrate", help="Create an agent orchestration plan.")
    orchestrate.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")
    orchestrate.add_argument("--profile", choices=["solo", "pair", "team"], default="pair")

    sub.add_parser("doctor", help="Print setup recommendations.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "probe":
        target = args.target.expanduser().resolve()
        hardware = probe_hardware()
        providers = detect_providers(load_local_credentials(target))
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
        path = write_skill_template(args.target, args.name, args.description)
        print(f"Wrote project skill template to {path}")
        return 0

    if args.command == "orchestrate":
        path = write_orchestration_plan(args.target, args.profile)
        print(f"Wrote agent orchestration plan to {path}")
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
        print(f"Wrote scaffold to {manifest.scaffold_dir}")
        print(f"Selected weak model: {routing.weak_model or 'none'}")
        print(f"Selected strong model: {routing.strong_model or 'none'}")
        print("Next: read .coding-scaffold/GETTING_STARTED.md")
        return 0

    return 2


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


def _print_doctor() -> None:
    hardware = probe_hardware()
    providers = detect_providers(load_local_credentials(Path.cwd()))
    print("CodingScaffold doctor")
    print(f"- Python package is runnable on {hardware.os_name}.")
    if not hardware.llmfit_available:
        print("- Install llmfit for deeper model sizing: brew install llmfit")
    if not any(p.name == "ollama" and p.available for p in providers):
        print("- Install or start Ollama if you want an easy local OpenAI-compatible path.")
    if not any(p.kind == "cloud" and p.available for p in providers):
        print("- No cloud credentials detected. That is fine for local-only use.")
