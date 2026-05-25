"""Per-subcommand descriptions and worked examples for `coding-scaffold ... --help`.

argparse defaults to a bare flag list when the user runs e.g.
``coding-scaffold setup run --help``. This module is the single registry of what
each subcommand actually does and 1-3 example invocations that cover the common
cases, so the CLI is self-documenting without needing the wiki.

Add a new entry here whenever you add a subcommand; a test
(`tests/test_subcommand_help.py`) fails if any subcommand in `--help` lacks a
description.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandDoc:
    """What each subcommand explains in its --help block."""

    description: str
    examples: list[str] = field(default_factory=list)
    when_to_run: str = ""

    def epilog(self) -> str:
        parts: list[str] = []
        if self.when_to_run:
            parts.append("When to run:")
            parts.append(f"  {self.when_to_run}")
            parts.append("")
        if self.examples:
            parts.append("Examples:")
            for example in self.examples:
                parts.append(f"  {example}")
        if not parts:
            return ""
        parts.append("")
        parts.append("Glossary: https://jrs1986.github.io/CodingScaffold/wiki/Glossary")
        return "\n".join(parts)


# Path tuples are command names walked through the subparser tree, e.g.
# ("setup", "run") for `coding-scaffold setup run`.
HELP_REGISTRY: dict[tuple[str, ...], CommandDoc] = {
    # ----- top-level ------------------------------------------------------
    ("probe",): CommandDoc(
        description=(
            "Inspect hardware and provider availability. Read-only; reports what local "
            "runtimes (Ollama, LM Studio), credentials, and accelerators are usable."
        ),
        when_to_run="Before `setup run`, to see what the routing plan can choose from.",
        examples=[
            "coding-scaffold probe",
            "coding-scaffold probe --json",
        ],
    ),
    ("doctor",): CommandDoc(
        description=(
            "Survey scaffold artifacts in the target project and recommend the next "
            "1-3 commands. Read-only; never installs or writes files."
        ),
        when_to_run="Any time. The accessibility hub for new users.",
        examples=[
            "coding-scaffold doctor --target .",
            "coding-scaffold doctor --json",
        ],
    ),
    ("pilot",): CommandDoc(
        description=(
            "Print the safe 10-minute happy-path recipe tailored to this project. "
            "Read-only; the user runs the printed commands."
        ),
        when_to_run="After install; before the first agentic change.",
        examples=[
            "coding-scaffold pilot --target . --tool opencode",
            "coding-scaffold pilot --target . --tool claude-code --json",
        ],
    ),
    # ----- setup ----------------------------------------------------------
    ("setup",): CommandDoc(
        description="Run setup, install add-ons, configure knowledge, or refresh generated files.",
        examples=[
            "coding-scaffold setup run --target . --mode beginner",
            "coding-scaffold setup update --target .",
        ],
    ),
    ("setup", "run"): CommandDoc(
        description=(
            "Guided project setup. Detects hardware + providers, asks intake questions "
            "(or uses --non-interactive defaults), and writes routing.json, AGENTS.md, "
            "tool adapters, eval config, and the scaffold artifact set."
        ),
        when_to_run="Once per project, or after a major model/provider change.",
        examples=[
            "coding-scaffold setup run --target . --mode beginner",
            "coding-scaffold setup run --target . --tool opencode --non-interactive",
            "coding-scaffold setup run --target . --install-tools --addon llmfit",
        ],
    ),
    ("setup", "tool"): CommandDoc(
        description="Install or validate a coding tool (opencode, claude-code, codex, …).",
        examples=[
            "coding-scaffold setup tool --tool opencode",
            "coding-scaffold setup tool --tool claude-code --install",
        ],
    ),
    ("setup", "addon"): CommandDoc(
        description="Install or validate an optional add-on (llmfit, routellm, obsidian, …).",
        examples=[
            "coding-scaffold setup addon --addon llmfit",
            "coding-scaffold setup addon --addon all --install",
        ],
    ),
    ("setup", "knowledge"): CommandDoc(
        description="Configure shared team knowledge (Markdown, Obsidian, Foam, MemPalace, HTML).",
        examples=[
            "coding-scaffold setup knowledge --backend markdown",
            "coding-scaffold setup knowledge --backend obsidian --shared-remote git@example.com:team/knowledge.git",
        ],
    ),
    ("setup", "update"): CommandDoc(
        description=(
            "Refresh generated scaffold files without losing user edits. Unchanged "
            "files are rewritten; edited files get a `.new` sidecar to merge."
        ),
        when_to_run="After upgrading the scaffold version; review `.new` files before merging.",
        examples=[
            "coding-scaffold setup update --target .",
            "coding-scaffold setup update --target . --json",
        ],
    ),
    # ----- credentials / skill / knowledge --------------------------------
    ("credentials",): CommandDoc(
        description="Create ignored local credential templates (.env or credentials.json).",
        examples=[
            "coding-scaffold credentials --format env",
            "coding-scaffold credentials --format json",
        ],
    ),
    ("skill",): CommandDoc(
        description="Create a reusable project skill template under .coding-scaffold/skills/.",
        examples=[
            "coding-scaffold skill --name 'Release Review' --description 'pre-release checklist'",
        ],
    ),
    ("knowledge",): CommandDoc(
        description="Create or operate on a shared team knowledge base.",
        examples=[
            "coding-scaffold knowledge --backend markdown",
            "coding-scaffold knowledge status",
            "coding-scaffold knowledge lint --format json",
        ],
    ),
    ("knowledge", "create"): CommandDoc(
        description="Create or update the team knowledge base scaffold.",
        examples=[
            "coding-scaffold knowledge create --backend markdown",
            "coding-scaffold knowledge create --backend html",
        ],
    ),
    ("knowledge", "status"): CommandDoc(
        description="Report knowledge scope, maturity, and frontmatter warnings.",
        examples=[
            "coding-scaffold knowledge status",
            "coding-scaffold knowledge status --json",
        ],
    ),
    ("knowledge", "distill"): CommandDoc(
        description="Propose curated wiki updates from raw notes.",
        examples=[
            "coding-scaffold knowledge distill --source raw",
            "coding-scaffold knowledge distill --source raw --no-review",
        ],
    ),
    ("knowledge", "list"): CommandDoc(
        description="List knowledge notes by scope and maturity.",
        examples=[
            "coding-scaffold knowledge list --scope company",
            "coding-scaffold knowledge list --scope team --maturity stable --format json",
        ],
    ),
    ("knowledge", "lint"): CommandDoc(
        description=(
            "Validate knowledge ownership, review dates, link health, and orphans. "
            "Exits non-zero on any violation by default (use --warn-only to demote)."
        ),
        when_to_run="In CI; before promoting a note upward.",
        examples=[
            "coding-scaffold knowledge lint",
            "coding-scaffold knowledge lint --format json --scope company",
        ],
    ),
    ("knowledge", "promote"): CommandDoc(
        description=(
            "Promote a knowledge note across maturity or scope (raw→wiki, team→unit, …). "
            "Updates frontmatter, INDEX, and audit trail; does not auto-commit."
        ),
        examples=[
            "coding-scaffold knowledge promote my-note --from raw --to wiki",
            "coding-scaffold knowledge promote auth-decision --from team --to unit",
        ],
    ),
    ("knowledge", "nominate"): CommandDoc(
        description="Bundle a note for promotion to a parent scope (team → org).",
        examples=[
            "coding-scaffold knowledge nominate my-skill --to-scope company",
        ],
    ),
    # ----- context --------------------------------------------------------
    ("context",): CommandDoc(
        description="Inspect and compress agent-context files safely.",
        examples=[
            "coding-scaffold context budget --target .",
            "coding-scaffold context lint --target .",
        ],
    ),
    ("context", "budget"): CommandDoc(
        description="Estimate context size and safety budget for the target.",
        examples=[
            "coding-scaffold context budget --target .",
            "coding-scaffold context budget --max-tokens 100000 --json",
        ],
    ),
    ("context", "compress"): CommandDoc(
        description="Write compressed context sidecars for files near the budget.",
        examples=[
            "coding-scaffold context compress --target .",
        ],
    ),
    ("context", "lint"): CommandDoc(
        description="Check agent-context files against project conventions.",
        examples=[
            "coding-scaffold context lint --target .",
            "coding-scaffold context lint --target . --json",
        ],
    ),
    ("context", "explain"): CommandDoc(
        description="Explain the context-hygiene checks and current findings.",
        examples=[
            "coding-scaffold context explain --target .",
        ],
    ),
    # ----- session --------------------------------------------------------
    ("session",): CommandDoc(
        description="Create and summarize per-agentic-change session traces.",
        examples=[
            "coding-scaffold session init --task 'add login flow'",
            "coding-scaffold session status",
        ],
    ),
    ("session", "init"): CommandDoc(
        description="Create a new session-trace Markdown file under .coding-scaffold/sessions/.",
        when_to_run="Before each agentic change so the work is reviewable in git.",
        examples=[
            "coding-scaffold session init --task 'first agentic change'",
        ],
    ),
    ("session", "summarize"): CommandDoc(
        description="Summarize a session-trace file into the SESSIONS index.",
        examples=[
            "coding-scaffold session summarize --path .coding-scaffold/sessions/2026-05-25-agentic-change.md",
        ],
    ),
    ("session", "start"): CommandDoc(
        description="Begin a session in a worktree or branch with a baseline checkpoint.",
        examples=[
            "coding-scaffold session start --task 'refactor router'",
        ],
    ),
    ("session", "checkpoint"): CommandDoc(
        description="Snapshot the current session state for review or rollback.",
        examples=[
            "coding-scaffold session checkpoint",
        ],
    ),
    ("session", "diff"): CommandDoc(
        description="Show changes since the last session checkpoint.",
        examples=[
            "coding-scaffold session diff",
        ],
    ),
    ("session", "rollback"): CommandDoc(
        description="Rewind to the previous session checkpoint.",
        examples=[
            "coding-scaffold session rollback",
        ],
    ),
    ("session", "summary"): CommandDoc(
        description="Print or write a structured summary of the active session.",
        examples=[
            "coding-scaffold session summary",
        ],
    ),
    ("session", "status"): CommandDoc(
        description="Show the active session and recent traces.",
        examples=[
            "coding-scaffold session status",
        ],
    ),
    # ----- memory ---------------------------------------------------------
    ("memory",): CommandDoc(
        description="Reviewable team memory: capture, review, promote, expire, audit.",
        examples=[
            "coding-scaffold memory capture --text 'always run pytest before merge'",
            "coding-scaffold memory audit",
        ],
    ),
    ("memory", "capture"): CommandDoc(
        description=(
            "Record a new memory entry as a candidate. Class=`secret` is refused; "
            "class=`personal_data` requires --allow-personal."
        ),
        examples=[
            "coding-scaffold memory capture --text 'CI runs only on Linux' --class team",
        ],
    ),
    ("memory", "review"): CommandDoc(
        description="Move captured memory entries through accept/reject review.",
        examples=[
            "coding-scaffold memory review",
        ],
    ),
    ("memory", "promote"): CommandDoc(
        description="Promote an accepted memory between maturity classes.",
        examples=[
            "coding-scaffold memory promote --slug ci-on-linux --to team",
        ],
    ),
    ("memory", "expire"): CommandDoc(
        description="Expire stale memory entries that have passed their review date.",
        examples=[
            "coding-scaffold memory expire",
        ],
    ),
    ("memory", "audit"): CommandDoc(
        description="List memory entries currently in effect with provenance.",
        examples=[
            "coding-scaffold memory audit --json",
        ],
    ),
    ("memory", "init"): CommandDoc(
        description="Write the memory config and seed the review folders.",
        examples=[
            "coding-scaffold memory init",
        ],
    ),
    # ----- pr-template ----------------------------------------------------
    ("pr-template",): CommandDoc(
        description="Manage generated GitHub PR templates for agentic changes.",
        examples=[
            "coding-scaffold pr-template init --target .",
        ],
    ),
    ("pr-template", "init"): CommandDoc(
        description="Add .github/PULL_REQUEST_TEMPLATE/agentic-change.md to the target.",
        examples=[
            "coding-scaffold pr-template init --target .",
        ],
    ),
    # ----- permissions / mcp ---------------------------------------------
    ("permissions",): CommandDoc(
        description="Write machine-readable agent permission artifacts.",
        examples=[
            "coding-scaffold permissions write --target .",
        ],
    ),
    ("permissions", "write"): CommandDoc(
        description="Generate .coding-scaffold/agent-permissions.json (read-only by default).",
        examples=[
            "coding-scaffold permissions write --target . --mode read-only",
        ],
    ),
    ("mcp",): CommandDoc(
        description="Inspect and govern MCP (Model Context Protocol) server configuration.",
        examples=[
            "coding-scaffold mcp scan",
            "coding-scaffold mcp policy init",
        ],
    ),
    ("mcp", "policy"): CommandDoc(
        description="Manage the MCP policy (allow/deny rules).",
        examples=[
            "coding-scaffold mcp policy init --target .",
        ],
    ),
    ("mcp", "policy", "init"): CommandDoc(
        description="Write .coding-scaffold/mcp-policy.json with safe defaults.",
        examples=[
            "coding-scaffold mcp policy init --target .",
        ],
    ),
    ("mcp", "scan"): CommandDoc(
        description="Scan known MCP config locations and report findings.",
        examples=[
            "coding-scaffold mcp scan --target .",
        ],
    ),
    ("mcp", "snapshot"): CommandDoc(
        description="Record the current MCP server set as a baseline.",
        examples=[
            "coding-scaffold mcp snapshot --target .",
        ],
    ),
    ("mcp", "diff"): CommandDoc(
        description="Compare current MCP state with the saved snapshot.",
        examples=[
            "coding-scaffold mcp diff --target .",
        ],
    ),
    # ----- skills ---------------------------------------------------------
    ("skills",): CommandDoc(
        description="Manage reviewable skill packs under .coding-scaffold/skills/.",
        examples=[
            "coding-scaffold skills new --name release-review",
            "coding-scaffold skills lint",
        ],
    ),
    ("skills", "new"): CommandDoc(
        description="Scaffold a new skill directory with SKILL.md and helpers.",
        examples=[
            "coding-scaffold skills new --name release-review",
        ],
    ),
    ("skills", "lint"): CommandDoc(
        description="Lint every skill under .coding-scaffold/skills/.",
        examples=[
            "coding-scaffold skills lint",
        ],
    ),
    ("skills", "approve"): CommandDoc(
        description="Record the current CHECKSUM for a skill (signs it as reviewed).",
        examples=[
            "coding-scaffold skills approve --name release-review",
        ],
    ),
    ("skills", "export"): CommandDoc(
        description="Bundle a skill into a tar.gz archive for sharing.",
        examples=[
            "coding-scaffold skills export --name release-review --out release-review.tar.gz",
        ],
    ),
    # ----- eval -----------------------------------------------------------
    ("eval",): CommandDoc(
        description="Run the lightweight readiness benchmark (init, run, report).",
        examples=[
            "coding-scaffold eval init",
            "coding-scaffold eval run",
        ],
    ),
    ("eval", "init"): CommandDoc(
        description="Write .coding-scaffold/eval-config.json with safe defaults.",
        examples=[
            "coding-scaffold eval init --target .",
        ],
    ),
    ("eval", "run"): CommandDoc(
        description="Run the enabled readiness checks against the project.",
        examples=[
            "coding-scaffold eval run --target .",
        ],
    ),
    ("eval", "report"): CommandDoc(
        description="Render a Markdown or JSON summary of the most recent run.",
        examples=[
            "coding-scaffold eval report --format markdown",
        ],
    ),
    # ----- team -----------------------------------------------------------
    ("team",): CommandDoc(
        description="Manage experienced-team onboarding manifests (init/connect/sync/doctor/push).",
        examples=[
            "coding-scaffold team init",
            "coding-scaffold team sync",
        ],
    ),
    ("team", "init"): CommandDoc(
        description="Write a starter team-onboarding.json manifest.",
        examples=[
            "coding-scaffold team init --target .",
        ],
    ),
    ("team", "connect"): CommandDoc(
        description="Apply a team manifest into this project (one-time bootstrap).",
        examples=[
            "coding-scaffold team connect --manifest path/to/team-onboarding.json",
        ],
    ),
    ("team", "sync"): CommandDoc(
        description="Refresh team-imported assets from the manifest source(s).",
        examples=[
            "coding-scaffold team sync",
            "coding-scaffold team sync --to-ref a1b2c3d",
        ],
    ),
    ("team", "doctor"): CommandDoc(
        description="Diagnose the local team manifest and show effective config + provenance.",
        examples=[
            "coding-scaffold team doctor",
        ],
    ),
    ("team", "push"): CommandDoc(
        description="Nominate local artifacts back to the team manifest (dry-run by default).",
        examples=[
            "coding-scaffold team push --dry-run",
            "coding-scaffold team push --open-pr",
        ],
    ),
    # ----- policy / tools ------------------------------------------------
    ("policy",): CommandDoc(
        description="Create company/unit/team policy config under .coding-scaffold/policy/.",
        examples=[
            "coding-scaffold policy --layer team",
        ],
    ),
    ("tools",): CommandDoc(
        description="Generate adapters, routing backends, workflows, and model picks.",
        examples=[
            "coding-scaffold tools adapt --tool opencode",
            "coding-scaffold tools select-model --prompt 'rename foo to bar'",
        ],
    ),
    ("tools", "adapt"): CommandDoc(
        description="Generate native config for a coding tool (opencode/claude-code/codex/…).",
        examples=[
            "coding-scaffold tools adapt --target . --tool opencode",
            "coding-scaffold tools adapt --target . --tool claude-code",
        ],
    ),
    ("tools", "route"): CommandDoc(
        description="Generate optional routing backend docs/config (RouteLLM).",
        examples=[
            "coding-scaffold tools route --backend routellm",
        ],
    ),
    ("tools", "select-model"): CommandDoc(
        description="Recommend a model route for a prompt (weak vs. strong).",
        examples=[
            "coding-scaffold tools select-model --prompt 'refactor utils.py'",
        ],
    ),
    ("tools", "workflow"): CommandDoc(
        description="Generate optional workflow backend docs/config (Open Multi-Agent).",
        examples=[
            "coding-scaffold tools workflow --backend open-multi-agent",
        ],
    ),
    ("tools", "orchestrate"): CommandDoc(
        description="Create an agent orchestration plan from a high-level goal.",
        examples=[
            "coding-scaffold tools orchestrate --goal 'set up CI matrix'",
        ],
    ),
}


def doc_for(path: tuple[str, ...]) -> CommandDoc | None:
    return HELP_REGISTRY.get(path)
