from __future__ import annotations

import argparse
from collections.abc import Callable
import json
import sys
from pathlib import Path

from .adapters import write_route_backend, write_tool_adapter, write_workflow_backend
from .cli_help import doc_for
from .cli_stability import marker_for
from .errors import CliError, format_error
from .context import (
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_MAX_CONTEXT_RATIO,
    DEFAULT_MAX_CONTEXT_TOKENS,
    compress_context,
    inspect_context_budget,
)
from .context_lint import LintReport, explain_context, lint_context
from .eval_harness import (
    EvalReport,
    load_eval_report,
    run_eval,
    write_eval_config,
)
from .mcp import (
    McpDiff,
    McpReport,
    diff_mcp,
    scan_mcp,
    snapshot_mcp,
    write_mcp_policy,
)
from .permissions import write_agent_permissions
from .memory import (
    MEMORY_CLASSES,
    MemoryAuditReport,
    MemoryReviewReport,
    audit_memory,
    capture_memory,
    expire_memory,
    promote_memory,
    review_memory,
    write_memory_config,
)
from .doctor import format_doctor_text, run_doctor
from .personas import PERSONAS as _PERSONAS, DEFAULT_PERSONA
from .pilot import format_pilot_text, run_pilot
from .tour import format_tour
from .pr_template import write_pr_template
from .session import (
    SessionStatusResult,
    SessionSummary,
    checkpoint_session,
    diff_session,
    init_session,
    rollback_session,
    start_session,
    status_session,
    summarize_session,
)
from .skills import (
    SkillLintReport,
    approve_skill,
    export_skill,
    lint_skills,
    new_skill,
)
from .credentials import load_local_credentials, write_local_credential_file
from .enablement import write_orchestration_plan, write_skill_template
from .hardware import probe_hardware
from .installers import install_missing_addons, install_missing_tools
from .intake import (
    CODING_TOOLS as _CODING_TOOLS_TUPLE,
    DEFAULT_TOOLS,
    IntakeAnswers,
    collect_intake,
    normalize_tools,
)
from .knowledge import (
    distill_knowledge,
    inspect_knowledge_status,
    lint_knowledge,
    list_knowledge,
    nominate_knowledge,
    promote_knowledge,
    write_knowledge_base,
)
from .model_selection import select_model_for_prompt
from .policy import write_policy_pack
from .providers import detect_providers
from .router import RoutingPlan, build_routing_plan
from .routing_io import load_routing_plan
from .scaffold_version import write_scaffold_version
from .team import (
    TeamResult,
    connect_team,
    doctor_team,
    inspect_team_doctor,
    preview_team,
    push_team,
    sync_team,
    write_team_manifest,
)
from .updater import refresh_scaffold
from .writers import write_scaffold

# argparse `choices=` expects a list; the canonical tuple lives in intake.py.
CODING_TOOLS = list(_CODING_TOOLS_TUPLE)
# Installable subset: every coding tool except the special `manual` value.
INSTALLABLE_TOOLS = [t for t in CODING_TOOLS if t != "manual"]
ADDONS = ["llmfit", "routellm", "open-multi-agent", "obsidian", "caveman-compression", "all"]
KNOWLEDGE_BACKENDS = ["markdown", "obsidian", "foam", "mempalace", "html"]
KNOWLEDGE_BACKENDS_WITH_NONE = ["none", *KNOWLEDGE_BACKENDS]


TOP_LEVEL_DESCRIPTION = """\
Local-first scaffold for AI-assisted coding teams. Generates reviewable
project-local guidance for hardware, providers, model selection, tool adapters,
skills, knowledge, policy, and sessions.

START HERE
  coding-scaffold doctor                         see what's set up + what's next
  coding-scaffold pilot --target . --tool opencode   print the 10-minute happy path
  coding-scaffold setup run --mode beginner      guided full setup

10-MINUTE PILOT (printed by `pilot` above; or run by hand)
  coding-scaffold setup run --target . --tool opencode --mode beginner
  coding-scaffold pr-template init --target .
  opencode      # inside the agent: /first-session, then /agentic-change

DAILY WORKFLOW
  coding-scaffold session init --task "..."      reversible session trace
  coding-scaffold context lint --target .        check agent-context files
  coding-scaffold eval run --target .            readiness benchmark

ADVANCED / GOVERNANCE (safe to ignore until your team needs them)
  policy, mcp, skills, memory, team, permissions, tools, knowledge distill

The full command list is below. Every command supports --help.
Markers next to each command name: [stable] [preview] [experimental].
  See https://jrs1986.github.io/CodingScaffold/wiki/Stability for what they promise.
Glossary of terms: https://jrs1986.github.io/CodingScaffold/wiki/Glossary
"""


def _add_target_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="Project directory.")


def _add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coding-scaffold",
        description=TOP_LEVEL_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    probe = sub.add_parser("probe", help="Inspect hardware and provider availability.")
    _add_json_arg(probe)
    _add_target_arg(probe)
    probe.add_argument(
        "--no-probe-cache",
        action="store_true",
        help="Bypass the hardware probe cache; re-probe live. Use after installing a new local runtime.",
    )

    setup = sub.add_parser("setup", help="Start here: run setup, install add-ons, or refresh generated files.")
    setup_sub = setup.add_subparsers(dest="setup_action", required=True, metavar="action")
    setup_run = setup_sub.add_parser("run", help="Run the guided project setup.")
    _add_setup_run_args(setup_run)
    setup_tool_canonical = setup_sub.add_parser("tool", help="Install or validate a coding tool.")
    _add_setup_tool_args(setup_tool_canonical)
    setup_addon_canonical = setup_sub.add_parser("addon", help="Install or validate an optional add-on.")
    _add_setup_addon_args(setup_addon_canonical)
    setup_knowledge_canonical = setup_sub.add_parser("knowledge", help="Configure shared team knowledge.")
    _add_setup_knowledge_args(setup_knowledge_canonical)
    setup_update = setup_sub.add_parser("update", help="Refresh generated scaffold files without losing edits.")
    _add_setup_update_args(setup_update)

    # NOTE: The parsers below are DEPRECATED flat aliases of the canonical
    # grouped commands (setup/knowledge/context/tools). Each one is built from
    # the same _add_*_args helper as its canonical form, so the two trees can
    # no longer drift (issue #48). They warn on use and will be REMOVED in
    # 0.9.0 — do not add new aliases here.
    init = sub.add_parser("init", help=argparse.SUPPRESS)
    _add_setup_run_args(init)

    wizard = sub.add_parser("wizard", help=argparse.SUPPRESS)
    _add_setup_run_args(wizard)

    credentials = sub.add_parser("credentials", help="Create ignored local credential files.")
    _add_target_arg(credentials)
    credentials.add_argument("--format", choices=["env", "json"], default="env")

    skill = sub.add_parser("skill", help="Create a reusable project skill template.")
    _add_target_arg(skill)
    skill.add_argument("--name", required=True, help="Skill name, e.g. Release Review.")
    skill.add_argument("--description", default="", help="Short description for when to use it.")
    skill.add_argument("--adapter", choices=["none", "opencode"], default="none")

    knowledge = sub.add_parser("knowledge", help="Create a shared team knowledge base.")
    _add_target_arg(knowledge)
    knowledge.add_argument("--backend", choices=KNOWLEDGE_BACKENDS, default="markdown")
    knowledge.add_argument("--shared-remote", help="Optional GitHub/GitLab repo URL for team memory.")
    knowledge.add_argument("--adapter", choices=["none", "opencode"], default="opencode")
    knowledge_sub = knowledge.add_subparsers(dest="knowledge_action", metavar="action")
    knowledge_create = knowledge_sub.add_parser("create", help="Create or update shared team knowledge.")
    _add_target_arg(knowledge_create)
    knowledge_create.add_argument("--backend", choices=KNOWLEDGE_BACKENDS, default="markdown")
    knowledge_create.add_argument("--shared-remote", help="Optional GitHub/GitLab repo URL for team memory.")
    knowledge_create.add_argument("--adapter", choices=["none", "opencode"], default="opencode")
    knowledge_status_canonical = knowledge_sub.add_parser("status", help="Report knowledge scope and maturity.")
    _add_knowledge_status_args(knowledge_status_canonical)
    knowledge_distill = knowledge_sub.add_parser("distill", help="Propose curated wiki updates from raw notes.")
    _add_target_arg(knowledge_distill)
    knowledge_distill.add_argument(
        "--source",
        default="raw",
        help="Raw knowledge source relative to .coding-scaffold/knowledge, or a project-relative path.",
    )
    knowledge_distill.add_argument(
        "--review",
        action="store_true",
        help="Write .new proposal files instead of modifying curated wiki pages.",
    )
    _add_json_arg(knowledge_distill)
    knowledge_list = knowledge_sub.add_parser("list", help="List knowledge notes by scope and maturity.")
    _add_target_arg(knowledge_list)
    knowledge_list.add_argument("--scope", choices=["team", "department", "unit", "company"])
    knowledge_list.add_argument("--maturity", choices=["draft", "validated", "recommended", "standard"])
    _add_json_arg(knowledge_list)
    knowledge_lint = knowledge_sub.add_parser("lint", help="Validate knowledge ownership, review dates, and links.")
    _add_target_arg(knowledge_lint)
    knowledge_lint.add_argument("--scope", "--layer", dest="scope", choices=["team", "department", "unit", "company"])
    knowledge_lint.add_argument("--format", choices=["text", "json"], default="text")
    knowledge_lint.add_argument("--fix", action="store_true", help="Apply cheap fixes such as missing last_reviewed.")
    knowledge_lint.add_argument("--warn-only", action="store_true", help="Print violations but exit 0.")
    knowledge_promote = knowledge_sub.add_parser("promote", help="Promote a knowledge note across layers.")
    knowledge_promote.add_argument("slug", help="Markdown filename stem or relative slug.")
    _add_target_arg(knowledge_promote)
    knowledge_promote.add_argument("--from", dest="from_layer", required=True)
    knowledge_promote.add_argument("--to", dest="to_layer", required=True)
    knowledge_promote.add_argument("--owner", help="Owner to set when the note does not already have one.")
    _add_json_arg(knowledge_promote)
    knowledge_nominate = knowledge_sub.add_parser("nominate", help="Bundle a note for promotion to a parent scope.")
    knowledge_nominate.add_argument("slug", help="Markdown filename stem or relative slug.")
    _add_target_arg(knowledge_nominate)
    knowledge_nominate.add_argument("--to-scope", required=True, choices=["department", "unit", "company"])
    knowledge_nominate.add_argument("--rationale", default="")
    _add_json_arg(knowledge_nominate)

    knowledge_status = sub.add_parser("knowledge-status", help=argparse.SUPPRESS)
    _add_knowledge_status_args(knowledge_status)

    context = sub.add_parser("context", help="Inspect and compress context safely.")
    context_sub = context.add_subparsers(dest="context_action", required=True, metavar="action")
    context_budget_canonical = context_sub.add_parser("budget", help="Estimate context size and safety budget.")
    _add_context_budget_args(context_budget_canonical)
    context_compress_canonical = context_sub.add_parser("compress", help="Write compressed context sidecars.")
    _add_context_compress_args(context_compress_canonical)
    context_lint_canonical = context_sub.add_parser(
        "lint",
        help="Lint agent-context files for vague, contradictory, or beginner-hostile rules.",
    )
    _add_context_lint_args(context_lint_canonical)
    context_explain_canonical = context_sub.add_parser(
        "explain",
        help="Summarize what's in the agent-context surface (rule counts, verifiers, length).",
    )
    _add_context_explain_args(context_explain_canonical)

    session = sub.add_parser("session", help="Create and summarize per-agentic-change session traces.")
    session_sub = session.add_subparsers(dest="session_action", required=True, metavar="action")
    session_init = session_sub.add_parser("init", help="Create a new session-trace Markdown file.")
    _add_target_arg(session_init)
    session_init.add_argument("--slug", default=None, help="Slug for the filename (default: agentic-change).")
    session_init.add_argument("--task", default=None, help="One-line task description to seed the template.")
    _add_json_arg(session_init)
    session_summarize = session_sub.add_parser("summarize", help="Summarize a session-trace file.")
    session_summarize.add_argument("path", type=Path, help="Path to a session-trace Markdown file.")
    _add_json_arg(session_summarize)
    session_start = session_sub.add_parser(
        "start",
        help="Begin a reversible agentic session (branch + optional worktree).",
    )
    _add_target_arg(session_start)
    session_start.add_argument("--slug", default=None)
    session_start.add_argument("--task", default=None)
    session_start.add_argument(
        "--worktree",
        action="store_true",
        help="Create a Git worktree at a sibling directory for full isolation.",
    )
    _add_json_arg(session_start)
    session_checkpoint = session_sub.add_parser(
        "checkpoint",
        help="Stage + commit current changes and record the commit in the session state.",
    )
    _add_target_arg(session_checkpoint)
    session_checkpoint.add_argument("--message", "-m", default=None,
                                    help="Commit message. Defaults to `checkpoint: <timestamp>`.")
    _add_json_arg(session_checkpoint)
    session_diff = session_sub.add_parser(
        "diff",
        help="Show the diff between the session's start commit and HEAD.",
    )
    _add_target_arg(session_diff)
    _add_json_arg(session_diff)
    session_rollback = session_sub.add_parser(
        "rollback",
        help="Restore the session's working tree to its start commit.",
    )
    _add_target_arg(session_rollback)
    session_rollback.add_argument("--confirm", action="store_true",
                                  help="Required to actually roll back; without it, preview only.")
    session_rollback.add_argument("--hard", action="store_true",
                                  help="Hard reset. Discards uncommitted changes. Requires --confirm.")
    _add_json_arg(session_rollback)
    session_summary = session_sub.add_parser(
        "summary",
        help="Overall picture of the active session: branch, baseline, checkpoints, diff size.",
    )
    _add_target_arg(session_summary)
    _add_json_arg(session_summary)

    memory = sub.add_parser("memory", help="Reviewable team memory (capture/review/promote/expire/audit).")
    memory_sub = memory.add_subparsers(dest="memory_action", required=True, metavar="action")
    memory_capture = memory_sub.add_parser("capture", help="Record a new memory entry.")
    _add_target_arg(memory_capture)
    memory_capture.add_argument("--class", dest="memory_class", required=True,
                                choices=list(MEMORY_CLASSES) + ["secret", "personal_data"],
                                help=(
                                    "Memory class. `secret` is always refused; `personal_data` "
                                    "requires --allow-personal."
                                ))
    memory_capture.add_argument("--content", required=True, help="Body of the memory entry.")
    memory_capture.add_argument("--owner", default=None, help="Owner handle (recommended).")
    memory_capture.add_argument("--source", default=None,
                                help="Path, URL, or other provenance reference.")
    memory_capture.add_argument("--expires", default=None,
                                help="ISO date (YYYY-MM-DD) when the entry should expire.")
    memory_capture.add_argument("--allow-personal", action="store_true",
                                help="Required to capture class=personal_data.")
    _add_json_arg(memory_capture)
    memory_review = memory_sub.add_parser("review",
                                          help="List active entries; flag unowned/expiring/expired.")
    _add_target_arg(memory_review)
    _add_json_arg(memory_review)
    memory_promote = memory_sub.add_parser("promote",
                                           help="Move an entry to a more durable class.")
    memory_promote.add_argument("entry_id", help="Entry id (e.g. 2026-05-18-my-note).")
    _add_target_arg(memory_promote)
    memory_promote.add_argument("--to", dest="new_class", required=True,
                                choices=list(MEMORY_CLASSES) + ["personal_data"],
                                help="Target class for the promoted entry.")
    memory_promote.add_argument("--owner", default=None,
                                help="Optional new owner for the promoted entry.")
    _add_json_arg(memory_promote)
    memory_expire = memory_sub.add_parser("expire",
                                          help="Move expired entries to _expired/.")
    _add_target_arg(memory_expire)
    _add_json_arg(memory_expire)
    memory_audit = memory_sub.add_parser("audit",
                                         help="Scan memory for content that looks like a secret or PII.")
    _add_target_arg(memory_audit)
    _add_json_arg(memory_audit)
    memory_init = memory_sub.add_parser("init",
                                        help="Write `.coding-scaffold/memory/config.json` (optional).")
    _add_target_arg(memory_init)
    memory_init.add_argument("--force", action="store_true")
    _add_json_arg(memory_init)

    pr_template = sub.add_parser("pr-template", help="Manage generated GitHub PR templates.")
    pr_template_sub = pr_template.add_subparsers(dest="pr_template_action", required=True, metavar="action")
    pr_template_init = pr_template_sub.add_parser(
        "init",
        help="Write .github/PULL_REQUEST_TEMPLATE/agentic-change.md if it doesn't exist.",
    )
    _add_target_arg(pr_template_init)
    _add_json_arg(pr_template_init)

    permissions = sub.add_parser(
        "permissions",
        help="Write machine-readable agent permission artifacts.",
    )
    permissions_sub = permissions.add_subparsers(
        dest="permissions_action", required=True, metavar="action",
    )
    permissions_write = permissions_sub.add_parser(
        "write",
        help="Write `.coding-scaffold/agent-permissions.json`.",
    )
    _add_target_arg(permissions_write)
    permissions_write.add_argument("--force", action="store_true",
                                   help="Overwrite an existing agent-permissions.json.")
    _add_json_arg(permissions_write)

    mcp = sub.add_parser("mcp", help="Inspect and govern MCP server configuration.")
    mcp_sub = mcp.add_subparsers(dest="mcp_action", required=True, metavar="action")
    mcp_policy = mcp_sub.add_parser(
        "policy",
        help="Manage the team MCP policy file.",
    )
    mcp_policy_sub = mcp_policy.add_subparsers(dest="mcp_policy_action", required=True, metavar="action")
    mcp_policy_init = mcp_policy_sub.add_parser(
        "init",
        help="Write `.coding-scaffold/mcp-policy.json` with defaults.",
    )
    _add_target_arg(mcp_policy_init)
    mcp_policy_init.add_argument("--force", action="store_true",
                                 help="Overwrite an existing policy file.")
    _add_json_arg(mcp_policy_init)
    mcp_scan = mcp_sub.add_parser("scan", help="Scan known MCP config locations and report findings.")
    _add_target_arg(mcp_scan)
    _add_json_arg(mcp_scan)
    mcp_snapshot = mcp_sub.add_parser("snapshot", help="Record the current MCP server set.")
    _add_target_arg(mcp_snapshot)
    _add_json_arg(mcp_snapshot)
    mcp_diff = mcp_sub.add_parser("diff", help="Compare current MCP state with the saved snapshot.")
    _add_target_arg(mcp_diff)
    _add_json_arg(mcp_diff)

    skills = sub.add_parser("skills", help="Manage reviewable skill packs.")
    skills_sub = skills.add_subparsers(dest="skills_action", required=True, metavar="action")
    skills_new = skills_sub.add_parser("new", help="Scaffold a new skill directory.")
    skills_new.add_argument("name", help="Skill name (slugified into the directory name).")
    _add_target_arg(skills_new)
    skills_new.add_argument("--owner", default=None, help="Skill owner handle for manifest.json.")
    _add_json_arg(skills_new)
    skills_lint = skills_sub.add_parser("lint", help="Lint every skill under .coding-scaffold/skills/.")
    _add_target_arg(skills_lint)
    _add_json_arg(skills_lint)
    skills_approve = skills_sub.add_parser("approve", help="Record the current CHECKSUM for a skill.")
    skills_approve.add_argument("name", help="Skill directory name.")
    _add_target_arg(skills_approve)
    _add_json_arg(skills_approve)
    skills_export = skills_sub.add_parser("export", help="Bundle a skill into a tar.gz archive.")
    skills_export.add_argument("name", help="Skill directory name.")
    _add_target_arg(skills_export)
    skills_export.add_argument("--output", type=Path, default=None,
                               help="Output archive path (default: <skill>.tar.gz in --target).")
    _add_json_arg(skills_export)

    eval_parser = sub.add_parser("eval", help="Run the lightweight readiness benchmark.")
    eval_sub = eval_parser.add_subparsers(dest="eval_action", required=True, metavar="action")
    eval_init = eval_sub.add_parser("init", help="Write `.coding-scaffold/eval-config.json`.")
    _add_target_arg(eval_init)
    eval_init.add_argument("--force", action="store_true")
    _add_json_arg(eval_init)
    eval_run = eval_sub.add_parser("run", help="Run the enabled readiness checks.")
    _add_target_arg(eval_run)
    _add_json_arg(eval_run)
    eval_report = eval_sub.add_parser(
        "report",
        help="Print the most recent eval report (re-runs by default).",
    )
    _add_target_arg(eval_report)
    eval_report.add_argument("--cached", action="store_true",
                             help="Use the saved report instead of re-running.")
    _add_json_arg(eval_report)

    context_budget = sub.add_parser("context-budget", help=argparse.SUPPRESS)
    _add_context_budget_args(context_budget)

    compress = sub.add_parser("compress-context", help=argparse.SUPPRESS)
    _add_context_compress_args(compress)

    orchestrate = sub.add_parser("orchestrate", help=argparse.SUPPRESS)
    _add_tools_orchestrate_args(orchestrate)

    setup_tool = sub.add_parser("setup-tool", help=argparse.SUPPRESS)
    _add_setup_tool_args(setup_tool)

    setup_addon = sub.add_parser("setup-addon", help=argparse.SUPPRESS)
    _add_setup_addon_args(setup_addon)

    setup_knowledge = sub.add_parser("setup-knowledge", help=argparse.SUPPRESS)
    _add_setup_knowledge_args(setup_knowledge)

    team = sub.add_parser("team", help="Manage experienced-team onboarding assets.")
    _add_target_arg(team)
    team_sub = team.add_subparsers(dest="team_action", required=True, metavar="action")

    team_init = team_sub.add_parser("init", help="Write a starter team-onboarding.json.")
    _add_target_arg(team_init)
    team_init.add_argument("--team", default="team", help="Team name for `team init`.")
    team_init.add_argument("--knowledge-remote", help="Shared knowledge Git remote for `team init`.")
    team_init.add_argument(
        "--knowledge-backend",
        choices=KNOWLEDGE_BACKENDS,
        default="markdown",
        help="Knowledge backend for `team init`.",
    )
    team_init.add_argument(
        "--tool",
        choices=CODING_TOOLS,
        default="opencode",
        help="Default coding tool for `team init`.",
    )

    team_connect = team_sub.add_parser("connect", help="Apply a team manifest into this project.")
    _add_target_arg(team_connect)
    team_connect.add_argument(
        "--manifest", help="Local manifest file or Git repo containing team-onboarding.json."
    )
    team_connect.add_argument(
        "--dry-run", action="store_true", help="Preview team imports without writing files."
    )
    team_connect.add_argument(
        "--yes", action="store_true", help="Apply team imports without an interactive prompt."
    )
    team_connect.add_argument(
        "--allow-local",
        action="store_true",
        help="Permit local-path or file:// remotes for team manifests.",
    )
    team_connect.add_argument("--to-version", help="Require a specific manifest_version.")
    team_connect.add_argument("--to-ref", help="Checkout a specific manifest source ref before connecting.")

    team_sync = team_sub.add_parser("sync", help="Refresh team-imported assets from the manifest.")
    _add_target_arg(team_sync)
    team_sync.add_argument(
        "--dry-run", action="store_true", help="Preview team imports without writing files."
    )
    team_sync.add_argument(
        "--yes", action="store_true", help="Apply team imports without an interactive prompt."
    )
    team_sync.add_argument(
        "--allow-local",
        action="store_true",
        help="Permit local-path or file:// remotes for team manifests.",
    )
    team_sync.add_argument("--to-version", help="Require a specific manifest_version.")
    team_sync.add_argument("--to-ref", help="Refresh from a specific connected manifest source ref.")

    team_doctor = team_sub.add_parser("doctor", help="Diagnose the local team manifest.")
    _add_target_arg(team_doctor)
    team_doctor.add_argument("--format", choices=["text", "json"], default="text")

    team_push = team_sub.add_parser("push", help="Nominate local artifacts back to the team manifest.")
    _add_target_arg(team_push)
    team_push.add_argument("--dry-run", action="store_true", help="List nomination candidates only.")
    team_push.add_argument("--open-pr", action="store_true", help="Open a draft PR against the manifest repo.")

    policy = sub.add_parser("policy", help="Create company/unit/team policy config.")
    _add_target_arg(policy)
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

    tools = sub.add_parser("tools", help="Generate adapters, routing backends, workflows, and model picks.")
    tools_sub = tools.add_subparsers(dest="tools_action", required=True, metavar="action")
    tools_adapt = tools_sub.add_parser("adapt", help="Generate native config for a coding tool.")
    _add_tools_adapt_args(tools_adapt)
    tools_route = tools_sub.add_parser("route", help="Generate optional routing backend docs/config.")
    _add_tools_route_args(tools_route)
    tools_select = tools_sub.add_parser("select-model", help="Recommend a model route for a prompt.")
    _add_tools_select_model_args(tools_select)
    tools_workflow = tools_sub.add_parser("workflow", help="Generate optional workflow backend docs/config.")
    _add_tools_workflow_args(tools_workflow)
    tools_orchestrate = tools_sub.add_parser("orchestrate", help="Create an agent orchestration plan.")
    _add_tools_orchestrate_args(tools_orchestrate)

    adapt = sub.add_parser("adapt", help=argparse.SUPPRESS)
    _add_tools_adapt_args(adapt)

    route = sub.add_parser("route", help=argparse.SUPPRESS)
    _add_tools_route_args(route)

    select = sub.add_parser("select-model", help=argparse.SUPPRESS)
    _add_tools_select_model_args(select)

    workflow = sub.add_parser("workflow", help=argparse.SUPPRESS)
    _add_tools_workflow_args(workflow)

    update = sub.add_parser("update", help=argparse.SUPPRESS)
    _add_setup_update_args(update)

    doctor = sub.add_parser(
        "doctor",
        help="Survey scaffold artifacts and recommend the next 1-3 commands.",
    )
    _add_target_arg(doctor)
    _add_json_arg(doctor)
    doctor.add_argument(
        "--verbose",
        action="store_true",
        help="Also print the legacy hardware/provider recommendation snapshot.",
    )
    doctor.add_argument(
        "--persona",
        choices=list(_PERSONAS),
        default=DEFAULT_PERSONA,
        help="Tailor the recommendations and ignore-list to a persona's focus area.",
    )
    doctor.add_argument(
        "--no-probe-cache",
        action="store_true",
        help="Bypass the hardware probe cache; re-probe live. Use after installing a new local runtime.",
    )

    pilot = sub.add_parser(
        "pilot",
        help="Print the safe 10-minute happy path tailored to this project.",
    )
    _add_target_arg(pilot)
    pilot.add_argument(
        "--tool",
        # `choices=` removed — comma-separated values would fail validation here;
        # normalize_tools validates against VALID_TOOLS instead.
        action="append",
        default=None,
        help="Coding tool(s) to weave into the recipe (default: opencode). "
             "Repeat or comma-separate for multi-tool projects.",
    )
    _add_json_arg(pilot)
    pilot.add_argument(
        "--persona",
        choices=list(_PERSONAS),
        default=DEFAULT_PERSONA,
        help="Tailor the printed recipe to a persona's focus area.",
    )
    pilot.add_argument(
        "--no-probe-cache",
        action="store_true",
        help="Bypass the hardware probe cache; re-probe live. Use after installing a new local runtime.",
    )

    tour = sub.add_parser(
        "tour",
        help="Read-only walkthrough of the tool: artifacts, the doctor loop, daily workflow.",
        description=(
            "Print a five-screen walkthrough explaining what CodingScaffold does, the "
            "scaffold artifact families, the doctor/pilot/setup loop, the daily "
            "session/eval/team workflow, and where to go next. Read-only and "
            "stateless: no files are written and no commands are executed. Designed "
            "to be the first thing a user runs right after install."
        ),
        epilog=(
            "Examples:\n"
            "  coding-scaffold tour\n"
            "  coding-scaffold tour --target .\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_target_arg(tour)
    _hide_suppressed_subcommands(sub)
    _annotate_stability(sub)
    _apply_help_registry(parser)
    return parser


def _hide_suppressed_subcommands(subparsers: argparse._SubParsersAction) -> None:
    subparsers._choices_actions = [  # noqa: SLF001 - argparse has no public hook for this.
        action for action in subparsers._choices_actions if action.help is not argparse.SUPPRESS
    ]


def _normalize_args_tools_in_place(args: argparse.Namespace) -> None:
    """If args carries ``tool`` from ``action='append'``, normalize it into a
    canonical ``tools`` list via :func:`normalize_tools`. Surfaces that don't
    accept ``--tool`` leave *args* untouched.

    On invalid input (unknown tool, ``manual`` mixed with a real tool) the
    ``CliError`` raised by :func:`normalize_tools` propagates to ``main``,
    which renders the three-line error block and returns its exit code.
    """
    if not hasattr(args, "tool"):
        return
    args.tools = normalize_tools(getattr(args, "tool", None))


def _apply_help_registry(parser: argparse.ArgumentParser) -> None:
    """Walk the subparser tree and apply description/epilog from cli_help.HELP_REGISTRY.

    Subparsers are defined inline as ``add_parser("name", help=...)`` for readability;
    the longer-form ``description=`` (what the command does) and ``epilog=`` (examples)
    come from this single registry so the cli.py file stays scannable. Hidden flat
    aliases (``init``, ``wizard``, …) inherit the canonical command's documentation.

    Tests assert every visible subcommand has a non-empty description after this pass.
    """

    for path, sub_action in _iter_subparser_actions(parser, ()):
        for name, subparser in sub_action.choices.items():
            full_path = path + (name,)
            doc = doc_for(full_path) or _fallback_doc(full_path)
            if doc is not None:
                if not getattr(subparser, "description", None):
                    subparser.description = doc.description
                if not getattr(subparser, "epilog", None):
                    subparser.epilog = doc.epilog()
                    if subparser.epilog:
                        subparser.formatter_class = argparse.RawDescriptionHelpFormatter


def _iter_subparser_actions(parser: argparse.ArgumentParser, path: tuple[str, ...]):
    for action in parser._actions:  # noqa: SLF001 — argparse has no public hook
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            yield path, action
            for name, subparser in action.choices.items():
                yield from _iter_subparser_actions(subparser, path + (name,))


# Map hidden flat aliases to the canonical command path so they reuse the
# canonical documentation.
_FLAT_ALIAS_CANONICAL: dict[str, tuple[str, ...]] = {
    "init": ("setup", "run"),
    "wizard": ("setup", "run"),
    "knowledge-status": ("knowledge", "status"),
    "context-budget": ("context", "budget"),
    "compress-context": ("context", "compress"),
    "orchestrate": ("tools", "orchestrate"),
    "setup-tool": ("setup", "tool"),
    "setup-addon": ("setup", "addon"),
    "setup-knowledge": ("setup", "knowledge"),
    "adapt": ("tools", "adapt"),
    "route": ("tools", "route"),
    "select-model": ("tools", "select-model"),
    "workflow": ("tools", "workflow"),
    "update": ("setup", "update"),
}


def _fallback_doc(path: tuple[str, ...]):
    """Look up documentation for hidden flat aliases by their canonical path."""

    if len(path) == 1 and path[0] in _FLAT_ALIAS_CANONICAL:
        return doc_for(_FLAT_ALIAS_CANONICAL[path[0]])
    return None


def _annotate_stability(subparsers: argparse._SubParsersAction) -> None:
    """Prefix each visible top-level command's help text with its stability marker.

    Only operates on the help-display objects (`_choices_actions`); the actual
    subparser objects in `choices` keep their original help so behavior, argument
    parsing, and `help=argparse.SUPPRESS` filtering all stay unchanged.
    """

    for action in subparsers._choices_actions:  # noqa: SLF001 - argparse has no public hook.
        if action.help is argparse.SUPPRESS:
            continue
        command = action.dest
        if not command:
            continue
        action.help = f"{marker_for(command)} {action.help or ''}".rstrip()


def _add_setup_run_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument("--language", help="Primary language, e.g. python, rust, typescript.")
    parser.add_argument("--project-target", help="Target kind, e.g. CLI, web app, library.")
    parser.add_argument("--existing-codebase", action="store_true", help="Project already has code.")
    parser.add_argument("--privacy", choices=["local-only", "local-first", "balanced"], default=None)
    parser.add_argument(
        "--tool",
        action="append",
        default=None,
        help="Coding tool to set up. Repeat or comma-separate for multi-tool projects.",
    )
    parser.add_argument(
        "--agent",
        action="append",
        dest="tool",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--coding-tool",
        action="append",
        dest="tool",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--preferred-local-model", help="Preferred local model name.")
    parser.add_argument("--mode", choices=["standard", "beginner"], default=None)
    parser.add_argument("--beginner", action="store_true", help="Include a first-project guide.")
    parser.add_argument("--non-interactive", action="store_true", help="Use defaults for missing values.")
    parser.add_argument("--install-tools", action="store_true", help="Install the selected coding tool if missing.")
    parser.add_argument("--no-install-tools", action="store_true", help="Do not offer coding tool installation.")
    parser.add_argument(
        "--addon",
        action="append",
        choices=ADDONS,
        default=[],
        help="Validate or install an optional add-on. Repeat for multiple add-ons.",
    )
    parser.add_argument("--install-addons", action="store_true", help="Install selected add-ons if missing.")
    parser.add_argument("--no-install-addons", action="store_true", help="Do not offer optional add-on setup.")
    parser.add_argument(
        "--knowledge-backend",
        choices=KNOWLEDGE_BACKENDS_WITH_NONE,
        default=None,
        help="Configure shared knowledge during setup.",
    )
    parser.add_argument("--knowledge-remote", help="GitHub/GitLab remote URL for shared knowledge.")
    parser.add_argument("--no-knowledge", action="store_true", help="Do not offer knowledge setup.")


def _add_setup_tool_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tool",
        action="append",
        default=None,
        help="Coding tool to set up. Repeat or comma-separate for multi-tool projects.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install missing tools without an extra prompt when stdin is not interactive.",
    )


def _add_setup_addon_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument("--addon", choices=ADDONS, default="llmfit")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install missing add-ons without an extra prompt when stdin is not interactive.",
    )


def _add_setup_knowledge_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument(
        "--backend",
        choices=KNOWLEDGE_BACKENDS,
        default="markdown",
        help="Knowledge backend to generate.",
    )
    parser.add_argument("--shared-remote", help="GitHub/GitLab repo URL for shared knowledge.")
    parser.add_argument("--adapter", choices=["none", "opencode"], default="opencode")


def _add_context_budget_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument(
        "--source",
        default="knowledge",
        help="Source to inspect: knowledge, team, or a path relative to target.",
    )
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_CONTEXT_TOKENS)
    parser.add_argument("--context-window", type=int, default=DEFAULT_CONTEXT_WINDOW)
    parser.add_argument("--max-ratio", type=float, default=DEFAULT_MAX_CONTEXT_RATIO)
    parser.add_argument(
        "--prefer",
        choices=["original", "compressed", "both"],
        default="original",
        help="Estimate original files, compressed sidecars when present, or both.",
    )
    _add_json_arg(parser)


def _add_context_compress_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument(
        "--source",
        default="knowledge",
        help="Source to compress: knowledge, team, or a path relative to target.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Rewrite existing .caveman sidecars.")
    parser.add_argument(
        "--engine",
        choices=["builtin", "caveman", "auto"],
        default="builtin",
        help="Compression engine. `caveman` uses the optional cloned upstream tool when available.",
    )


def _add_context_lint_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument(
        "--path",
        action="append",
        default=None,
        help=(
            "Path (relative to --target) of an extra context file to lint. Repeat for multiple "
            "files; replaces the default set when supplied."
        ),
    )
    _add_json_arg(parser)


def _add_context_explain_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument(
        "--path",
        action="append",
        default=None,
        help="Optional path (relative to --target) to include; replaces the default set when supplied.",
    )
    _add_json_arg(parser)


def _add_setup_update_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    _add_json_arg(parser)
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Bypass the min_supported_scaffold_version compatibility check. "
            "Use when the installed scaffold is older than the project's recorded floor "
            "and you've read https://jrs1986.github.io/CodingScaffold/wiki/Upgrading."
        ),
    )


def _add_knowledge_status_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    _add_json_arg(parser)


def _add_tools_adapt_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument(
        "--tool",
        action="append",
        default=None,
        help="Coding tool to set up. Repeat or comma-separate for multi-tool projects.",
    )


def _add_tools_route_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument("--backend", choices=["routellm"], default="routellm")


def _add_tools_select_model_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument("--prompt", help="Prompt or task description to classify.")
    parser.add_argument("--mode", choices=["recommend", "auto"], default="recommend")
    _add_json_arg(parser)


def _add_tools_workflow_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument("--backend", choices=["open-multi-agent"], default="open-multi-agent")


def _add_tools_orchestrate_args(parser: argparse.ArgumentParser) -> None:
    _add_target_arg(parser)
    parser.add_argument("--profile", choices=["solo", "pair", "team"], default="pair")
    parser.add_argument("--adapter", choices=["none", "opencode"], default="opencode")


def _normalize_grouped_command(args: argparse.Namespace) -> None:
    if args.command == "setup":
        mapping = {
            "run": "wizard",
            "tool": "setup-tool",
            "addon": "setup-addon",
            "knowledge": "setup-knowledge",
            "update": "update",
        }
        args.command = mapping[args.setup_action]
        return
    if args.command == "knowledge":
        action = getattr(args, "knowledge_action", None)
        if action == "status":
            args.command = "knowledge-status"
        elif action == "distill":
            args.command = "knowledge-distill"
        elif action == "list":
            args.command = "knowledge-list"
        elif action == "lint":
            args.command = "knowledge-lint"
        elif action == "promote":
            args.command = "knowledge-promote"
        elif action == "nominate":
            args.command = "knowledge-nominate"
        return
    if args.command == "context":
        args.command = {
            "budget": "context-budget",
            "compress": "compress-context",
            "lint": "context-lint",
            "explain": "context-explain",
        }[args.context_action]
        return
    if args.command == "session":
        args.command = {
            "init": "session-init",
            "summarize": "session-summarize",
            "start": "session-start",
            "checkpoint": "session-checkpoint",
            "diff": "session-diff",
            "rollback": "session-rollback",
            "summary": "session-summary",
        }[args.session_action]
        return
    if args.command == "memory":
        args.command = {
            "capture": "memory-capture",
            "review": "memory-review",
            "promote": "memory-promote",
            "expire": "memory-expire",
            "audit": "memory-audit",
            "init": "memory-init",
        }[args.memory_action]
        return
    if args.command == "pr-template":
        args.command = {
            "init": "pr-template-init",
        }[args.pr_template_action]
        return
    if args.command == "permissions":
        args.command = {
            "write": "permissions-write",
        }[args.permissions_action]
        return
    if args.command == "mcp":
        if args.mcp_action == "policy":
            args.command = {
                "init": "mcp-policy-init",
            }[args.mcp_policy_action]
        else:
            args.command = {
                "scan": "mcp-scan",
                "snapshot": "mcp-snapshot",
                "diff": "mcp-diff",
            }[args.mcp_action]
        return
    if args.command == "skills":
        args.command = {
            "new": "skills-new",
            "lint": "skills-lint",
            "approve": "skills-approve",
            "export": "skills-export",
        }[args.skills_action]
        return
    if args.command == "eval":
        args.command = {
            "init": "eval-init",
            "run": "eval-run",
            "report": "eval-report",
        }[args.eval_action]
        return
    if args.command == "tools":
        args.command = {
            "adapt": "adapt",
            "route": "route",
            "select-model": "select-model",
            "workflow": "workflow",
            "orchestrate": "orchestrate",
        }[args.tools_action]


def _cmd_probe(args: argparse.Namespace) -> int:
    target = args.target.expanduser().resolve()
    use_cache = not getattr(args, "no_probe_cache", False)
    hardware = probe_hardware(use_cache=use_cache)
    providers = detect_providers(load_local_credentials(target), include_copilot=True)
    payload = {"hardware": hardware.to_dict(), "providers": [p.to_dict() for p in providers]}
    if args.json:
        _print_json(payload)
    else:
        _print_probe(payload)
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    target = getattr(args, "target", None) or Path.cwd()
    persona = getattr(args, "persona", DEFAULT_PERSONA)
    use_cache = not getattr(args, "no_probe_cache", False)
    report = run_doctor(target, persona=persona, use_cache=use_cache)
    if getattr(args, "json", False):
        _print_json(report.to_dict())
    else:
        print(format_doctor_text(report))
        if getattr(args, "verbose", False):
            print()
            _print_doctor()
    return 0


def _cmd_pilot(args: argparse.Namespace) -> int:
    use_cache = not getattr(args, "no_probe_cache", False)
    report = run_pilot(
        args.target,
        tools=getattr(args, "tools", None),
        persona=getattr(args, "persona", DEFAULT_PERSONA),
        use_cache=use_cache,
    )
    if args.json:
        _print_json(report.to_dict())
    else:
        print(format_pilot_text(report))
    return 0


def _cmd_tour(args: argparse.Namespace) -> int:
    print(format_tour(getattr(args, "target", None)))
    return 0


def _cmd_credentials(args: argparse.Namespace) -> int:
    path = write_local_credential_file(args.target, args.format)
    print(f"Wrote local credential template to {path}")
    print("Fill values locally. Do not commit this file.")
    return 0


def _cmd_skill(args: argparse.Namespace) -> int:
    adapter = None if args.adapter == "none" else args.adapter
    path = write_skill_template(args.target, args.name, args.description, adapter)
    print(f"Wrote project skill template to {path}")
    return 0


def _cmd_knowledge(args: argparse.Namespace) -> int:
    adapter = None if args.adapter == "none" else args.adapter
    result = write_knowledge_base(args.target, args.backend, args.shared_remote, adapter)
    print(f"Wrote {len(result.files)} knowledge file(s).")
    if result.skipped:
        print(f"Skipped {len(result.skipped)} existing knowledge file(s).")
    return 0


def _cmd_knowledge_status(args: argparse.Namespace) -> int:
    status = inspect_knowledge_status(args.target)
    if args.json:
        _print_json(status.to_dict())
    else:
        for scope, maturities in sorted(status.counts.items()):
            summary = ", ".join(f"{maturity}: {count}" for maturity, count in sorted(maturities.items()))
            print(f"{scope}: {summary}")
        for warning in status.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 1 if status.warnings and not status.counts else 0


def _cmd_knowledge_distill(args: argparse.Namespace) -> int:
    result = distill_knowledge(args.target, args.source, review=args.review)
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"Created {len(result.created)} knowledge proposal file(s).")
        print(f"Updated {len(result.updated)} knowledge proposal file(s).")
        print(f"Skipped {len(result.skipped)} raw note(s).")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 1 if result.warnings and not (result.created or result.updated) else 0


def _cmd_knowledge_list(args: argparse.Namespace) -> int:
    entries = list_knowledge(args.target, scope=args.scope, maturity=args.maturity)
    if args.json:
        _print_json([entry.to_dict() for entry in entries])
    else:
        for entry in entries:
            print(f"{entry.scope}\t{entry.maturity}\t{entry.owner or '-'}\t{entry.path}")
    return 0


def _cmd_knowledge_lint(args: argparse.Namespace) -> int:
    result = lint_knowledge(args.target, scope=args.scope, format=args.format, fix=args.fix)
    if args.format == "json":
        _print_json(result.to_dict())
    else:
        for path in result.fixed:
            print(f"Fixed: {path}")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        for violation in result.violations:
            print(f"{violation.severity}: {violation.path}: {violation.message}", file=sys.stderr)
    return 1 if result.violations and not args.warn_only else 0


def _cmd_knowledge_promote(args: argparse.Namespace) -> int:
    result = promote_knowledge(
        args.target,
        args.slug,
        from_layer=args.from_layer,
        to_layer=args.to_layer,
        owner=args.owner,
    )
    if args.json:
        _print_json(result.to_dict())
    else:
        for action in result.actions:
            print(action)
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 1 if result.warnings else 0


def _cmd_knowledge_nominate(args: argparse.Namespace) -> int:
    result = nominate_knowledge(
        args.target,
        args.slug,
        to_scope=args.to_scope,
        rationale=args.rationale,
    )
    if args.json:
        _print_json(result.to_dict())
    else:
        for action in result.actions:
            print(action)
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 1 if result.warnings else 0


def _cmd_context_budget(args: argparse.Namespace) -> int:
    budget = inspect_context_budget(
        args.target,
        source=args.source,
        prefer=args.prefer,
        max_tokens=args.max_tokens,
        context_window=args.context_window,
        max_ratio=args.max_ratio,
    )
    if args.json:
        _print_json(budget.to_dict())
    else:
        _print_context_budget(budget.to_dict())
    return 1 if budget.warnings else 0


def _cmd_compress_context(args: argparse.Namespace) -> int:
    result = compress_context(
        args.target,
        source=args.source,
        overwrite=args.overwrite,
        engine=args.engine,
    )
    print(f"Wrote {len(result.files)} compressed context sidecar(s).")
    if result.skipped:
        print(f"Skipped {len(result.skipped)} existing sidecar(s).")
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _cmd_context_lint(args: argparse.Namespace) -> int:
    report = lint_context(args.target, paths=args.path)
    if args.json:
        _print_json(report.to_dict())
    else:
        _print_context_lint(report)
    for warning in report.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    # Exit non-zero on errors so the lint can gate CI.
    return 1 if report.error_count else 0


def _cmd_context_explain(args: argparse.Namespace) -> int:
    payload = explain_context(args.target, paths=args.path)
    if args.json:
        _print_json(payload)
    else:
        _print_context_explain(payload)
    return 0


def _cmd_session_init(args: argparse.Namespace) -> int:
    result = init_session(args.target, slug=args.slug, task=args.task)
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"Wrote session trace: {result.path}")
        print("Fill in the structured sections as you work; run `coding-scaffold session "
              "summarize` to read them back.")
    return 0


def _cmd_session_summarize(args: argparse.Namespace) -> int:
    summary = summarize_session(args.path)
    if args.json:
        _print_json(summary.to_dict())
    else:
        _print_session_summary(summary)
    for warning in summary.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    return 1 if summary.warnings else 0


def _cmd_session_start(args: argparse.Namespace) -> int:
    result = start_session(
        args.target,
        slug=args.slug,
        task=args.task,
        worktree=args.worktree,
    )
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"Branch:        {result.branch}")
        print(f"Start commit:  {result.start_commit[:12]}")
        if result.worktree_path:
            print(f"Worktree:      {result.worktree_path}")
        print(f"Trace:         {result.trace_path}")
        print(f"State:         {result.state_path}")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _cmd_session_checkpoint(args: argparse.Namespace) -> int:
    result = checkpoint_session(args.target, message=args.message)
    if args.json:
        _print_json(result.to_dict())
    else:
        if result.commit:
            print(f"Checkpoint: {result.commit[:12]} ({result.files_changed} file(s))")
            print(f"Message:    {result.message}")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 0 if result.commit or not result.warnings else 1


def _cmd_session_diff(args: argparse.Namespace) -> int:
    result = diff_session(args.target)
    if args.json:
        _print_json(result.to_dict())
    else:
        head = result.head_commit[:12] if result.head_commit else "?"
        start = result.start_commit[:12] if result.start_commit else "?"
        print(f"Diff {start} .. {head}")
        if result.diff_summary:
            print(result.diff_summary)
        else:
            print("(no changes)")
    return 0


def _cmd_session_rollback(args: argparse.Namespace) -> int:
    result = rollback_session(args.target, confirm=args.confirm, hard=args.hard)
    if args.json:
        _print_json(result.to_dict())
    else:
        if result.mode == "preview":
            print(f"Preview: {len(result.files_at_risk)} file(s) would be touched.")
            for path in result.files_at_risk[:20]:
                print(f"  {path}")
            if len(result.files_at_risk) > 20:
                print(f"  ... and {len(result.files_at_risk) - 20} more")
            for warning in result.warnings:
                print(warning)
        else:
            print(f"Rolled back ({result.mode}). Start commit: {result.start_commit[:12] if result.start_commit else '?'}")
    return 0


def _cmd_session_summary(args: argparse.Namespace) -> int:
    result = status_session(args.target)
    if args.json:
        _print_json(result.to_dict())
    else:
        _print_session_status(result)
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0 if result.status != "unknown" else 1


def _cmd_memory_init(args: argparse.Namespace) -> int:
    outcome = write_memory_config(args.target, force=args.force)
    if args.json:
        _print_json(outcome)
    else:
        if outcome.get("created"):
            print(f"Wrote memory config: {outcome['path']}")
        elif outcome.get("skipped"):
            print(f"Skipped existing config: {outcome['path']} (use --force to overwrite)")
    return 0


def _cmd_memory_capture(args: argparse.Namespace) -> int:
    result = capture_memory(
        args.target,
        class_=args.memory_class,
        content=args.content,
        owner=args.owner,
        source=args.source,
        expires=args.expires,
        allow_personal=args.allow_personal,
    )
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"Captured memory: {result.entry.id}")
        print(f"  class:   {result.entry.class_}")
        print(f"  path:    {result.entry.path}")
        print(f"  expires: {result.entry.expires or '(no expiry)'}")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _cmd_memory_review(args: argparse.Namespace) -> int:
    report = review_memory(args.target)
    if args.json:
        _print_json(report.to_dict())
    else:
        _print_memory_review(report)
    return 0


def _cmd_memory_promote(args: argparse.Namespace) -> int:
    result = promote_memory(
        args.target,
        entry_id=args.entry_id,
        new_class=args.new_class,
        new_owner=args.owner,
    )
    if args.json:
        _print_json(result.to_dict())
    else:
        if result.new_entry:
            print(f"Promoted {result.source_entry.id if result.source_entry else '?'} "
                  f"-> {result.new_entry.id} (class={result.new_entry.class_})")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _cmd_memory_expire(args: argparse.Namespace) -> int:
    result = expire_memory(args.target)
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"Expired {len(result.expired_entries)} entry/entries.")
        for entry_id in result.expired_entries:
            print(f"  -> {result.moved_to.get(entry_id, '(moved)')}")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _cmd_memory_audit(args: argparse.Namespace) -> int:
    report = audit_memory(args.target)
    if args.json:
        _print_json(report.to_dict())
    else:
        _print_memory_audit(report)
    # Audit findings of `error` severity gate CI.
    return 1 if report.error_count else 0


def _cmd_pr_template_init(args: argparse.Namespace) -> int:
    result = write_pr_template(args.target)
    if args.json:
        _print_json(result.to_dict())
    else:
        if result.files:
            print(f"Wrote {len(result.files)} PR template file(s).")
            for path in result.files:
                print(f"  {path}")
        if result.skipped:
            print(f"Skipped {len(result.skipped)} existing file(s).")
            for path in result.skipped:
                print(f"  {path}")
    return 0


def _cmd_permissions_write(args: argparse.Namespace) -> int:
    result = write_agent_permissions(args.target, force=args.force)
    if args.json:
        _print_json(result.to_dict())
    else:
        for path in result.files:
            print(f"Wrote {path}")
        for path in result.skipped:
            print(f"Skipped {path} (use --force to regenerate).")
    return 0


def _cmd_mcp_policy_init(args: argparse.Namespace) -> int:
    outcome = write_mcp_policy(args.target, force=args.force)
    if args.json:
        _print_json(outcome)
    else:
        if outcome.get("created"):
            print(f"Wrote MCP policy: {outcome['path']}")
        elif outcome.get("skipped"):
            print(f"Skipped existing MCP policy: {outcome['path']} (use --force to overwrite)")
    return 0


def _cmd_mcp_scan(args: argparse.Namespace) -> int:
    report = scan_mcp(args.target)
    if args.json:
        _print_json(report.to_dict())
    else:
        _print_mcp_scan(report)
    return 1 if report.error_count else 0


def _cmd_mcp_snapshot(args: argparse.Namespace) -> int:
    outcome = snapshot_mcp(args.target)
    if args.json:
        _print_json(outcome)
    else:
        print(f"Wrote MCP snapshot: {outcome['path']}")
        print(f"Recorded {outcome['servers']} server(s) from {len(outcome['scanned_sources'])} config(s).")
    return 0


def _cmd_mcp_diff(args: argparse.Namespace) -> int:
    diff = diff_mcp(args.target)
    if args.json:
        _print_json(diff.to_dict())
    else:
        _print_mcp_diff(diff)
    for warning in diff.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    # Non-zero when there's drift so this can gate CI.
    return 1 if (diff.added or diff.removed or diff.changed) else 0


def _cmd_skills_new(args: argparse.Namespace) -> int:
    result = new_skill(args.target, args.name, owner=args.owner)
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"Skill scaffolded at: {result.path}")
        for path in result.files:
            print(f"  +{path.relative_to(args.target.expanduser().resolve())}")
        for path in result.skipped:
            print(f"  ={path.relative_to(args.target.expanduser().resolve())} (skipped)")
    return 0


def _cmd_skills_lint(args: argparse.Namespace) -> int:
    report = lint_skills(args.target)
    if args.json:
        _print_json(report.to_dict())
    else:
        _print_skills_lint(report)
    return 1 if report.error_count else 0


def _cmd_skills_approve(args: argparse.Namespace) -> int:
    outcome = approve_skill(args.target, args.name)
    if args.json:
        _print_json(outcome)
    else:
        if outcome.get("approved"):
            print(f"Approved skill {outcome['skill']}: checksum {outcome['checksum'][:16]}…")
        else:
            print(f"Warning: {outcome.get('warning', 'approval failed')}", file=sys.stderr)
    return 0 if outcome.get("approved") else 1


def _cmd_skills_export(args: argparse.Namespace) -> int:
    outcome = export_skill(args.target, args.name, output=args.output)
    if args.json:
        _print_json(outcome)
    else:
        if outcome.get("exported"):
            print(f"Exported {outcome['skill']} -> {outcome['archive']}")
        else:
            print(f"Warning: {outcome.get('warning', 'export failed')}", file=sys.stderr)
    return 0 if outcome.get("exported") else 1


def _cmd_eval_init(args: argparse.Namespace) -> int:
    outcome = write_eval_config(args.target, force=args.force)
    if args.json:
        _print_json(outcome)
    else:
        if outcome.get("created"):
            print(f"Wrote eval config: {outcome['path']}")
        elif outcome.get("skipped"):
            print(f"Skipped existing config: {outcome['path']} (use --force to overwrite)")
    return 0


def _cmd_eval_run(args: argparse.Namespace) -> int:
    report = run_eval(args.target)
    if args.json:
        _print_json(report.to_dict())
    else:
        _print_eval_report(report)
    return 0 if report.passed_count == report.total_count else 1


def _cmd_eval_report(args: argparse.Namespace) -> int:
    if args.cached:
        cached = load_eval_report(args.target)
        if cached is None:
            print("No cached eval report found. Run `coding-scaffold eval run` first.",
                  file=sys.stderr)
            return 1
        report = cached
    else:
        report = run_eval(args.target)
    if args.json:
        _print_json(report.to_dict())
    else:
        _print_eval_report(report)
    return 0 if report.passed_count == report.total_count else 1


def _cmd_orchestrate(args: argparse.Namespace) -> int:
    adapter = None if args.adapter == "none" else args.adapter
    path = write_orchestration_plan(args.target, args.profile, adapter)
    print(f"Wrote agent orchestration plan to {path}")
    return 0


def _cmd_setup_tool(args: argparse.Namespace) -> int:
    all_results = []
    for tool in args.tools:
        all_results.extend(
            install_missing_tools(
                tool,
                interactive=sys.stdin.isatty(),
                assume_yes=args.install,
            )
        )
    for result in all_results:
        print(f"{result.tool}: {result.status} - {result.message}")
    return 1 if any(result.status == "failed" for result in all_results) else 0


def _cmd_setup_addon(args: argparse.Namespace) -> int:
    results = install_missing_addons(
        args.addon,
        interactive=sys.stdin.isatty(),
        assume_yes=args.install,
        target=args.target,
    )
    for result in results:
        print(f"{result.tool}: {result.status} - {result.message}")
    return 1 if any(result.status == "failed" for result in results) else 0


def _cmd_setup_knowledge(args: argparse.Namespace) -> int:
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


def _cmd_team(args: argparse.Namespace) -> int:
    if args.team_action == "init":
        path = write_team_manifest(
            args.target,
            team=args.team,
            knowledge_remote=args.knowledge_remote,
            knowledge_backend=args.knowledge_backend,
            default_tool=args.tool,
        )
        print(f"Wrote team onboarding manifest to {path}")
        return 0
    if args.team_action == "connect":
        if args.dry_run:
            result = preview_team(
                args.target,
                args.manifest,
                allow_local=args.allow_local,
                to_version=args.to_version,
                to_ref=args.to_ref,
            )
        elif not args.yes and not sys.stdin.isatty():
            result = TeamResult([], ["Refusing non-interactive team connect without --yes. Run --dry-run first."])
        elif not args.yes and not _confirm_team_import(
            preview_team(
                args.target,
                args.manifest,
                allow_local=args.allow_local,
                to_version=args.to_version,
                to_ref=args.to_ref,
            )
        ):
            result = TeamResult([], ["Skipped team connect."])
        else:
            result = connect_team(
                args.target,
                args.manifest,
                allow_local=args.allow_local,
                to_version=args.to_version,
                to_ref=args.to_ref,
            )
    elif args.team_action == "sync":
        if args.dry_run:
            result = sync_team(
                args.target,
                dry_run=True,
                allow_local=args.allow_local,
                to_version=args.to_version,
                to_ref=args.to_ref,
            )
        elif not args.yes and not sys.stdin.isatty():
            result = TeamResult([], ["Refusing non-interactive team sync without --yes. Run --dry-run first."])
        elif not args.yes and not _confirm_team_import(
            sync_team(
                args.target,
                dry_run=True,
                allow_local=args.allow_local,
                to_version=args.to_version,
                to_ref=args.to_ref,
            )
        ):
            result = TeamResult([], ["Skipped team sync."])
        else:
            result = sync_team(
                args.target,
                allow_local=args.allow_local,
                to_version=args.to_version,
                to_ref=args.to_ref,
            )
    elif args.team_action == "doctor":
        if args.format == "json":
            report = inspect_team_doctor(args.target)
            _print_json(report.to_dict())
            return 1 if report.warnings and not report.actions else 0
        result = doctor_team(args.target)
    elif args.team_action == "push":
        result = push_team(args.target, dry_run=args.dry_run, open_pr=args.open_pr)
    else:
        raise AssertionError(f"Unknown team action: {args.team_action}")
    for action in result.actions:
        print(action)
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    return 1 if result.warnings and not result.actions else 0


def _cmd_policy(args: argparse.Namespace) -> int:
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


def _cmd_update(args: argparse.Namespace) -> int:
    target = args.target.expanduser().resolve()

    # Compatibility gate: refuse to update if the installed scaffold is older
    # than the project's recorded `min_supported_scaffold_version`. The .new
    # workflow assumes the project structure the writers produce matches what
    # `setup update` knows how to compare against; a downgrade can write files
    # in a shape the old code doesn't recognize and silently clobber edits.
    from . import __version__
    from .scaffold_version import compare_versions, read_min_supported_version

    min_required = read_min_supported_version(target)
    if min_required and not getattr(args, "force", False):
        if compare_versions(__version__, min_required) < 0:
            print(
                f"error: this project was last updated with CodingScaffold {min_required}, "
                f"but {__version__} is installed.",
                file=sys.stderr,
            )
            print(
                "  next: upgrade the scaffold "
                "(`pip install -U coding-scaffold` or `uv tool upgrade coding-scaffold`), "
                "or rerun with `--force` after reading the migration note.",
                file=sys.stderr,
            )
            print(
                "  see: https://jrs1986.github.io/CodingScaffold/wiki/Upgrading",
                file=sys.stderr,
            )
            return 1

    intake = _load_project_intake(target)
    hardware = probe_hardware()
    providers = detect_providers(load_local_credentials(target))
    routing = build_routing_plan(intake, hardware, providers)
    result = refresh_scaffold(target, intake, hardware, providers, routing)
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"Updated {len(result.updated)} generated file(s).")
        print(f"Staged {len(result.staged)} edited file update(s) as .new.")
        print(f"Skipped {len(result.skipped)} already-current file(s).")
        if result.staged:
            print()
            print("Reconcile .new files — copy-pasteable next steps:")
            print("  1. Diff each pair so you can see what changed upstream:")
            for path in result.staged:
                original = str(path)[: -len(".new")] if str(path).endswith(".new") else str(path)
                print(f"     diff -u {original} {path}")
            print("  2. Merge the upstream changes into your edited file (resolve by hand).")
            print("  3. Delete the .new sidecar once you're done:")
            for path in result.staged:
                print(f"     rm {path}")
            print("  4. Re-run `coding-scaffold eval run --target .` to confirm the project is healthy.")
            print()
            print("Full upgrade guide: https://jrs1986.github.io/CodingScaffold/wiki/Upgrading")
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _cmd_adapt(args: argparse.Namespace) -> int:
    result = write_tool_adapter(args.target, args.tools)
    print(f"Wrote {len(result.files)} adapter file(s).")
    if result.skipped:
        print(f"Skipped {len(result.skipped)} existing file(s).")
    return 0


def _cmd_route(args: argparse.Namespace) -> int:
    result = write_route_backend(args.target, args.backend)
    print(f"Wrote {len(result.files)} routing backend file(s).")
    return 0


def _cmd_select_model(args: argparse.Namespace) -> int:
    target = args.target.expanduser().resolve()
    prompt = args.prompt
    if prompt is None and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    if not prompt:
        raise CliError(
            "No task prompt provided.",
            "Provide --prompt or pipe a task description into stdin.",
            exit_code=2,
        )
    routing = _load_routing_or_probe(target)
    providers = detect_providers(load_local_credentials(target))
    selection = select_model_for_prompt(prompt, routing, providers, args.mode)
    if args.json:
        _print_json(selection.to_dict())
    else:
        _print_model_selection(selection.to_dict())
    return 0


def _cmd_workflow(args: argparse.Namespace) -> int:
    result = write_workflow_backend(args.target, args.backend)
    print(f"Wrote {len(result.files)} workflow backend file(s).")
    return 0


def _cmd_init_or_wizard(args: argparse.Namespace) -> int:
    target = args.target.expanduser().resolve()
    is_wizard = args.command == "wizard"
    # args.tools is already normalized by _normalize_args_tools_in_place in main().
    answers = collect_intake(
        target=target,
        provided=IntakeAnswers(
            language=getattr(args, "language", None),
            project_target=getattr(args, "project_target", None),
            existing_codebase=getattr(args, "existing_codebase", False) or None,
            privacy=getattr(args, "privacy", None),
            tools=getattr(args, "tools", None),
            preferred_local_model=getattr(args, "preferred_local_model", None),
            mode="beginner" if getattr(args, "beginner", False) else getattr(args, "mode", None),
        ),
        interactive=(is_wizard or not getattr(args, "non_interactive", False)) and sys.stdin.isatty(),
    )
    hardware = probe_hardware()
    providers = detect_providers(load_local_credentials(target))
    routing = build_routing_plan(answers, hardware, providers)
    manifest = write_scaffold(target, answers, hardware, providers, routing)
    primary_tool = answers.tools[0] if answers.tools else "opencode"
    # Install every selected tool, not just the primary. The pilot recipe
    # explicitly tells multi-tool users `setup run ... --install-tools` will
    # install both — single-tool delegation broke that promise (see review
    # of Bundle 7).
    install_results = []
    for tool_choice in answers.tools or [primary_tool]:
        install_results.extend(_maybe_install_tools(tool_choice, args, is_wizard))
    addon_results = _maybe_install_addons(args, is_wizard, target)
    knowledge_result = _maybe_setup_knowledge(args, is_wizard, target, primary_tool)
    adapter = write_tool_adapter(target, answers.tools) if primary_tool != "manual" else None
    if adapter:
        write_scaffold_version(target, [*manifest.files, *adapter.files])
    print(f"Wrote scaffold to {manifest.scaffold_dir}")
    if adapter:
        # Spec §6.3: surface the multi-tool count in the summary when applicable.
        non_manual_tools = [t for t in answers.tools if t != "manual"]
        if len(non_manual_tools) > 1:
            print(
                f"Wrote {len(adapter.files)} tool adapter file(s) across "
                f"{len(non_manual_tools)} tool(s): {', '.join(non_manual_tools)}"
            )
        else:
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

COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "probe": _cmd_probe,
    "doctor": _cmd_doctor,
    "pilot": _cmd_pilot,
    "tour": _cmd_tour,
    "credentials": _cmd_credentials,
    "skill": _cmd_skill,
    "knowledge": _cmd_knowledge,
    "knowledge-status": _cmd_knowledge_status,
    "knowledge-distill": _cmd_knowledge_distill,
    "knowledge-list": _cmd_knowledge_list,
    "knowledge-lint": _cmd_knowledge_lint,
    "knowledge-promote": _cmd_knowledge_promote,
    "knowledge-nominate": _cmd_knowledge_nominate,
    "context-budget": _cmd_context_budget,
    "compress-context": _cmd_compress_context,
    "context-lint": _cmd_context_lint,
    "context-explain": _cmd_context_explain,
    "session-init": _cmd_session_init,
    "session-summarize": _cmd_session_summarize,
    "session-start": _cmd_session_start,
    "session-checkpoint": _cmd_session_checkpoint,
    "session-diff": _cmd_session_diff,
    "session-rollback": _cmd_session_rollback,
    "session-summary": _cmd_session_summary,
    "memory-init": _cmd_memory_init,
    "memory-capture": _cmd_memory_capture,
    "memory-review": _cmd_memory_review,
    "memory-promote": _cmd_memory_promote,
    "memory-expire": _cmd_memory_expire,
    "memory-audit": _cmd_memory_audit,
    "pr-template-init": _cmd_pr_template_init,
    "permissions-write": _cmd_permissions_write,
    "mcp-policy-init": _cmd_mcp_policy_init,
    "mcp-scan": _cmd_mcp_scan,
    "mcp-snapshot": _cmd_mcp_snapshot,
    "mcp-diff": _cmd_mcp_diff,
    "skills-new": _cmd_skills_new,
    "skills-lint": _cmd_skills_lint,
    "skills-approve": _cmd_skills_approve,
    "skills-export": _cmd_skills_export,
    "eval-init": _cmd_eval_init,
    "eval-run": _cmd_eval_run,
    "eval-report": _cmd_eval_report,
    "orchestrate": _cmd_orchestrate,
    "setup-tool": _cmd_setup_tool,
    "setup-addon": _cmd_setup_addon,
    "setup-knowledge": _cmd_setup_knowledge,
    "team": _cmd_team,
    "policy": _cmd_policy,
    "update": _cmd_update,
    "adapt": _cmd_adapt,
    "route": _cmd_route,
    "select-model": _cmd_select_model,
    "workflow": _cmd_workflow,
    "init": _cmd_init_or_wizard,
    "wizard": _cmd_init_or_wizard,
}

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in _FLAT_ALIAS_CANONICAL:
        replacement = " ".join(("coding-scaffold",) + _FLAT_ALIAS_CANONICAL[args.command])
        print(
            f"Warning: `{args.command}` is a deprecated alias and will be removed in 0.9.0. "
            f"Use `{replacement}` instead.",
            file=sys.stderr,
        )
    _normalize_grouped_command(args)
    handler = COMMANDS.get(args.command)
    try:
        _normalize_args_tools_in_place(args)
        return handler(args) if handler else 2
    except CliError as exc:
        print(format_error(exc), file=sys.stderr)
        return exc.exit_code


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
        "(comma-separated: llmfit, routellm, open-multi-agent, obsidian, "
        "caveman-compression, all; empty skips) []: "
    ).strip()
    if not answer:
        return []
    allowed = {"llmfit", "routellm", "open-multi-agent", "obsidian", "caveman-compression", "all"}
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
            "Knowledge base backend (none/markdown/obsidian/foam/mempalace)",
            "markdown",
            {"none", "markdown", "obsidian", "foam", "mempalace"},
        )
        if backend != "none" and shared_remote is None:
            shared_remote = _prompt_optional(
                "Shared knowledge Git remote URL (empty keeps knowledge project-local)"
            )
    if backend is None or backend == "none":
        return None
    # `"both"` literal was removed in 0.7.0; selected_tool is always a single
    # canonical tool name. Only `opencode` currently wires a knowledge adapter.
    adapter = "opencode" if selected_tool == "opencode" else None
    return write_knowledge_base(target, backend, shared_remote or None, adapter)


def _prompt_choice(label: str, default: str, allowed: set[str]) -> str:
    answer = input(f"{label} [{default}]: ").strip().lower()
    if not answer:
        return default
    return answer if answer in allowed else default


def _prompt_optional(label: str) -> str:
    return input(f"{label}: ").strip()


def _confirm_team_import(preview: TeamResult) -> bool:
    for action in preview.actions:
        print(action)
    for warning in preview.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if preview.warnings and not preview.actions:
        return False
    answer = input(f"Apply these {len(preview.actions)} team onboarding action(s)? [y/N]: ").strip()
    return answer.lower() in {"y", "yes"}


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


def _load_project_intake(target: Path) -> IntakeAnswers:
    path = target / ".coding-scaffold" / "project.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return collect_intake(target, IntakeAnswers(), interactive=False)
    if not isinstance(payload, dict):
        return collect_intake(target, IntakeAnswers(), interactive=False)
    raw_tools = payload.get("tools")
    if not isinstance(raw_tools, list):
        raw_tools = []
    tools = [t for t in raw_tools if isinstance(t, str) and t] or list(DEFAULT_TOOLS)
    return collect_intake(
        target,
        IntakeAnswers(
            language=_string_or_none(payload.get("language")),
            project_target=_string_or_none(payload.get("project_target")),
            existing_codebase=_bool_or_none(payload.get("existing_codebase")),
            privacy=_string_or_none(payload.get("privacy")),
            tools=tools,
            preferred_local_model=_string_or_none(payload.get("preferred_local_model")),
            mode=_string_or_none(payload.get("mode")),
        ),
        interactive=False,
    )


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


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


def _print_context_budget(budget: dict[str, object]) -> None:
    print(f"Source: {budget['source']}")
    print(f"Preference: {budget['prefer']}")
    print(f"Files: {budget['file_count']}")
    print(f"Estimated tokens: {budget['tokens_estimate']}")
    print(f"Context window use: {float(budget['window_ratio']):.0%}")
    print(f"Recommendation: {budget['recommendation']}")
    for warning in budget["warnings"]:
        print(f"Warning: {warning}", file=sys.stderr)


def _print_context_lint(report: LintReport) -> None:
    if not report.findings:
        print(f"context lint: 0 findings across {len(report.scanned_files)} file(s).")
        if report.skipped_files:
            print(f"Skipped {len(report.skipped_files)} missing file(s).")
        return
    print(
        f"context lint: {report.error_count} error / {report.warning_count} warning / "
        f"{report.info_count} info across {len(report.scanned_files)} file(s)."
    )
    print()
    for finding in report.findings:
        location = finding.file if finding.line is None else f"{finding.file}:{finding.line}"
        print(f"{finding.severity.upper():<8} {finding.rule:<32} {location}")
        print(f"         {finding.message}")
        print(f"         Fix: {finding.suggested_fix}")
        print()


def _print_context_explain(payload: dict[str, object]) -> None:
    files = payload.get("files", [])
    if not isinstance(files, list) or not files:
        print("No agent-context files found in the expected locations.")
        return
    totals = payload.get("totals", {})
    project_type = payload.get("project_type") or "unknown"
    print(f"Project type signal: {project_type}")
    print(
        f"Totals: {totals.get('files', 0)} file(s), ~{totals.get('approx_tokens', 0)} tokens, "
        f"{totals.get('rule_lines', 0)} rule lines."
    )
    print()
    for entry in files:
        print(f"- {entry['file']}")
        print(
            f"    ~{entry['approx_tokens']} tokens, {entry['rule_lines']} rule lines, "
            f"{entry['chars']} chars"
        )
        if entry["verification_tokens"]:
            print(f"    verifiers: {', '.join(entry['verification_tokens'])}")
        else:
            print("    verifiers: (none detected)")
        if entry["mentions_advanced_concepts"]:
            print(
                "    advanced concepts: "
                f"{', '.join(entry['mentions_advanced_concepts'])}"
            )


def _print_mcp_scan(report: McpReport) -> None:
    print(
        f"mcp scan: {len(report.servers)} server(s) across "
        f"{len(report.scanned_sources)} config(s); "
        f"{report.error_count} error / {report.warning_count} warning."
    )
    if report.servers:
        print()
        print("Servers:")
        for server in report.servers:
            location = server.url or f"{server.command or '?'} {' '.join(server.args)}".strip()
            pin = f"@{server.package_version}" if server.package_version else " (unpinned)"
            pkg = f" [{server.package}{pin}]" if server.package else ""
            caps = f" capabilities: {', '.join(server.capabilities)}" if server.capabilities else ""
            print(f"  - {server.name} ({server.kind}, from {server.source}){pkg}{caps}")
            print(f"      {location}")
    if report.findings:
        print()
        print("Findings:")
        for f in report.findings:
            head = f"  {f.severity.upper():<8} {f.rule:<32}"
            location = f"{f.source or '?'}:{f.server or '?'}"
            print(f"{head} {location}")
            print(f"         {f.message}")
            print(f"         Fix: {f.suggested_fix}")


def _print_mcp_diff(diff: McpDiff) -> None:
    if not (diff.added or diff.removed or diff.changed):
        print("mcp diff: no changes since the last snapshot.")
        return
    print(
        f"mcp diff: +{len(diff.added)} added, -{len(diff.removed)} removed, "
        f"~{len(diff.changed)} changed."
    )
    for server in diff.added:
        print(f"  + {server.name} ({server.kind}, from {server.source})")
    for previous in diff.removed:
        print(f"  - {previous.get('name', '?')} (was in {previous.get('source', '?')})")
    for current, previous in diff.changed:
        prev_fp = str(previous.get("fingerprint", ""))
        cur_fp = current.fingerprint
        print(
            f"  ~ {current.name}: fingerprint {prev_fp[:12]}… -> {cur_fp[:12]}… "
            f"({current.source})"
        )


def _print_skills_lint(report: SkillLintReport) -> None:
    if not report.skills_scanned:
        print("skills lint: no skills found under `.coding-scaffold/skills/`.")
        return
    print(
        f"skills lint: scanned {len(report.skills_scanned)} skill(s); "
        f"{report.error_count} error / {report.warning_count} warning."
    )
    for f in report.findings:
        head = f"  {f.severity.upper():<8} {f.rule:<32}"
        loc_parts = [f.skill or "?"]
        if f.file:
            loc_parts.append(f.file + (f":{f.line}" if f.line else ""))
        print(f"{head} {'/'.join(loc_parts)}")
        print(f"         {f.message}")
        print(f"         Fix: {f.suggested_fix}")


def _print_eval_report(report: EvalReport) -> None:
    score_pct = int(round(report.score * 100))
    print(
        f"eval report: {report.passed_count}/{report.total_count} checks passed "
        f"({score_pct}%)"
    )
    print()
    by_category: dict[str, list] = {}
    for check in report.checks:
        by_category.setdefault(check.category, []).append(check)
    for category in sorted(by_category):
        print(f"  {category}:")
        for check in by_category[category]:
            mark = "PASS" if check.passed else "FAIL"
            print(f"    [{mark}] {check.name}")
            print(f"           {check.message}")
    if report.warnings:
        print()
        for warning in report.warnings:
            print(f"Warning: {warning}", file=sys.stderr)


def _print_session_status(result: SessionStatusResult) -> None:
    print("Session status")
    print(f"  status:        {result.status}")
    print(f"  branch:        {result.branch or '(none)'}")
    if result.start_commit:
        print(f"  start:         {result.start_commit[:12]}")
    if result.head_commit:
        print(f"  head:          {result.head_commit[:12]}")
    if result.worktree_path:
        print(f"  worktree:      {result.worktree_path}")
    print(f"  checkpoints:   {result.checkpoint_count}")
    print(f"  files changed: {result.files_changed}")


def _print_memory_review(report: MemoryReviewReport) -> None:
    print(f"memory review: {len(report.entries)} entry/entries")
    by_class: dict[str, list] = {}
    for entry in report.entries:
        by_class.setdefault(entry.class_, []).append(entry)
    for class_name in sorted(by_class):
        print(f"  {class_name}:")
        for entry in by_class[class_name]:
            owner = entry.owner if entry.owner.strip() else "(no owner)"
            extras = []
            if entry.expires:
                extras.append(f"expires {entry.expires}")
            if entry.status != "active":
                extras.append(entry.status)
            tail = f" [{', '.join(extras)}]" if extras else ""
            print(f"    - {entry.id} ({owner}){tail}")
    if any(report.flagged.values()):
        print()
        for key in ("unowned", "expiring_soon", "expired"):
            ids = report.flagged.get(key, [])
            if ids:
                print(f"  {key}: {', '.join(ids)}")


def _print_memory_audit(report: MemoryAuditReport) -> None:
    if not report.findings:
        print(f"memory audit: 0 findings across {report.entries_scanned} entry/entries.")
        return
    counts = report.to_dict()["counts"]
    if not isinstance(counts, dict):
        counts = {}
    print(
        f"memory audit: {counts.get('errors', 0)} error / "
        f"{counts.get('warnings', 0)} warning / {counts.get('info', 0)} info across "
        f"{report.entries_scanned} entry/entries."
    )
    print()
    for finding in report.findings:
        print(f"  {finding.severity.upper():<8} {finding.rule:<24} {finding.file}:{finding.line}")
        print(f"           {finding.pattern_label}")
        print(f"           Fix: {finding.suggested_fix}")


def _print_session_summary(summary: SessionSummary) -> None:
    print(f"Session: {summary.path}")
    print(f"  Task:               {summary.task or '(not filled in)'}")
    print(f"  Files inspected:    {summary.files_inspected}")
    print(f"  Files changed:      {summary.files_changed}")
    print(f"  Commands run:       {summary.commands_run}")
    if summary.tests_passed is not None or summary.tests_failed is not None:
        passed = summary.tests_passed if summary.tests_passed is not None else "?"
        failed = summary.tests_failed if summary.tests_failed is not None else "?"
        print(f"  Tests:              passed={passed} failed={failed}")
    else:
        print("  Tests:              (not filled in)")
    print(f"  Risks:              {summary.risks}")
    print(f"  Follow-ups:         {summary.follow_ups}")
    print(f"  Knowledge to promote: {summary.knowledge_to_promote}")


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
