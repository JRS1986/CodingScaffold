"""`coding-scaffold tour` — the 'first 10 minutes' walkthrough (issue #91).

Closes the gap between \"I just installed coding-scaffold\" and \"I have files on
disk that explain what to do\". The tour:

- Runs on a fresh repo with no scaffold artifacts.
- Walks through five screens explaining what the tool does, the artifact
  families, the doctor/pilot/setup loop, the session/eval/team trio, and
  where the wiki lives.
- Ends with a single recommended command.
- Is read-only and stateless: no files are written, no commands are executed.

The tour is intentionally short and pure text so it works offline, in CI, and
right after install. The wiki has the deeper version; the tour exists so a new
user does not have to leave the terminal to find their footing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .artifacts import ARTIFACTS

WIKI_BASE = "https://jrs1986.github.io/CodingScaffold/wiki"


@dataclass(frozen=True)
class TourScreen:
    title: str
    body: str
    wiki: str


def screens() -> list[TourScreen]:
    """The fixed tour content. Pure data so tests can enumerate it."""

    return [
        TourScreen(
            title="1. What CodingScaffold does",
            body=(
                "CodingScaffold prepares the repo around your coding agent (OpenCode,\n"
                "Claude Code, Codex, …). It writes project-local rules, model routing,\n"
                "review templates, and reviewable session traces — so the agent behaves\n"
                "consistently and the work is shippable through normal PRs.\n\n"
                "It does NOT replace the agent, does NOT run the agent, and never sends\n"
                "prompts to a model. Setup is local Python; the first model call happens\n"
                "later, inside your coding tool."
            ),
            wiki=f"{WIKI_BASE}/index",
        ),
        TourScreen(
            title="2. The artifact families",
            body=(
                "Everything CodingScaffold writes is one of these artifact families:\n"
                f"{_artifact_summary()}"
            ),
            wiki=f"{WIKI_BASE}/Core-Concepts",
        ),
        TourScreen(
            title="3. The doctor → pilot → setup loop",
            body=(
                "Three commands carry the whole new-user journey:\n"
                "  doctor   — see what's set up and what's recommended next (read-only)\n"
                "  pilot    — print the 10-minute happy path for this repo (read-only)\n"
                "  setup    — actually run the guided setup\n\n"
                "Run them in that order. Each one is safe to re-run; setup is the only\n"
                "one that writes files."
            ),
            wiki=f"{WIKI_BASE}/Getting-Started",
        ),
        TourScreen(
            title="4. Daily workflow: session, eval, team",
            body=(
                "Once setup is done, your day-to-day shape is:\n"
                "  session  — wrap every agentic change in a reviewable trace + rollback\n"
                "  eval     — readiness benchmark that the scaffold is set up correctly\n"
                "  team     — share manifests, knowledge, skills across the team\n\n"
                "Everything else (policy, mcp, permissions, tools route/workflow) is\n"
                "advanced — safe to ignore until the basics are working."
            ),
            wiki=f"{WIKI_BASE}/Getting-Started",
        ),
        TourScreen(
            title="5. Where to go next",
            body=(
                "Recommended next command:\n"
                "  coding-scaffold doctor --target .\n\n"
                "Then follow whatever doctor recommends. The wiki has deeper pages\n"
                "for each area; --help on every command has a description + examples.\n"
                "When in doubt, run doctor again."
            ),
            wiki=f"{WIKI_BASE}/Glossary",
        ),
    ]


def _artifact_summary() -> str:
    """One-line summary per artifact, used in screen 2."""

    lines = []
    for artifact in ARTIFACTS:
        lines.append(f"  - {artifact.key}: {artifact.why}")
    return "\n".join(lines)


def format_tour(target: Path | None = None) -> str:
    """Render the tour as a single human-readable text block.

    ``target`` is accepted for API symmetry with ``doctor`` and ``pilot``;
    currently unused because the tour is stateless. Kept so callers can pass
    the same flag and we don't break compatibility later when the tour starts
    tailoring screen 4 to repo content.
    """

    _ = target  # reserved for future per-repo tailoring
    blocks: list[str] = []
    blocks.append("CodingScaffold tour — your first 10 minutes\n")
    for screen in screens():
        blocks.append(f"--- {screen.title} ---")
        blocks.append(screen.body)
        blocks.append(f"More: {screen.wiki}")
        blocks.append("")
    blocks.append(
        "Tour end. Run `coding-scaffold doctor --target .` next.\n"
        f"Glossary: {WIKI_BASE}/Glossary"
    )
    return "\n".join(blocks)
