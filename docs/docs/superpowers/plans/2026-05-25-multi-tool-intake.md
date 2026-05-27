# Multi-Tool Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `--tool` a list everywhere it's accepted so a project can configure (and a user can pilot) two coding tools — e.g., Codex + Claude Code — in a single `setup run`. Deprecate the legacy `--tool both` literal (which only ever meant `opencode + openclaude`) with a clear two-release path.

**Architecture:** One canonical normalizer (`normalize_tools`) in `intake.py` handles every form of `--tool` input (single str, list, comma-separated, `both` legacy, conflict detection). `IntakeAnswers.tools: list[str]` replaces `IntakeAnswers.tool` end-to-end across `intake.py`, `cli.py`, `writers.py`, `adapters.py`, `updater.py`, and `pilot.py`. JSON outputs (`project.json`, `routing.json`, pilot JSON) carry `tools` only — no singular `tool` back-compat. A small `_normalize_persisted_intake` helper back-fills legacy reads for one release window.

**Tech Stack:** Python 3.11+, stdlib only. Tests via `pytest`. Lint via `ruff`. Run gates `uv run ruff check src/ tests/` and `uv run pytest tests/ -q` clean after every commit.

**Spec reference:** [`docs/docs/superpowers/specs/2026-05-25-multi-tool-intake-design.md`](../specs/2026-05-25-multi-tool-intake-design.md)

**Branch:** Create a new branch `feat/multi-tool-intake` from `main`. One PR.

---

## Pre-flight

- [ ] **Step 0a: Branch and baseline**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/multi-tool-intake
source .venv/bin/activate
uv run pytest tests/ -q | tail -3      # establish 590 passing baseline
uv run ruff check src/ tests/          # establish clean baseline
```

Expected: 590 passed, ruff "All checks passed!". If either is dirty, fix before proceeding.

---

## Task 1 — `normalize_tools` helper (pure function, the foundation)

**Closes the input-shape concern for §4.3, §5.1, §6.1 of the spec.**

**Files:**
- Modify: `src/coding_scaffold/intake.py` (add helper + constants)
- Create: `tests/test_normalize_tools.py`

The helper accepts every form `--tool` can take across the codebase (string, list, comma-string, list with comma-strings inside, `None`) and returns a canonical deduped `list[str]`. It also: expands the deprecated `both` literal, prints a one-line stderr deprecation warning the first time it fires per process, and raises `CliError` for `manual + real-tool` mixes.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_normalize_tools.py`:

```python
"""Coverage for the canonical --tool normalizer (spec §4.3)."""

from __future__ import annotations

import io

import pytest

from coding_scaffold.errors import CliError
from coding_scaffold.intake import (
    DEFAULT_TOOLS,
    normalize_tools,
    reset_deprecation_state,
)


@pytest.fixture(autouse=True)
def _reset_deprecation():
    # The "both" warning only fires once per process; reset between tests.
    reset_deprecation_state()
    yield
    reset_deprecation_state()


def test_none_returns_default_tools() -> None:
    assert normalize_tools(None) == list(DEFAULT_TOOLS)


def test_empty_list_returns_default_tools() -> None:
    assert normalize_tools([]) == list(DEFAULT_TOOLS)


def test_single_string_returns_singleton_list() -> None:
    assert normalize_tools("codex") == ["codex"]


def test_list_of_strings_passes_through() -> None:
    assert normalize_tools(["codex", "claude-code"]) == ["codex", "claude-code"]


def test_comma_separated_string_is_split() -> None:
    assert normalize_tools("codex,claude-code") == ["codex", "claude-code"]


def test_mixed_repeats_and_commas_are_flattened() -> None:
    assert normalize_tools(["codex,opencode", "claude-code"]) == [
        "codex", "opencode", "claude-code",
    ]


def test_duplicates_are_removed_preserving_order() -> None:
    assert normalize_tools(["codex", "codex", "claude-code", "codex"]) == [
        "codex", "claude-code",
    ]


def test_both_expands_to_opencode_openclaude_and_warns(capsys: pytest.CaptureFixture[str]) -> None:
    result = normalize_tools(["both"])
    assert result == ["opencode", "openclaude"]
    err = capsys.readouterr().err
    assert "deprecated" in err.lower()
    assert "0.7.0" in err
    assert "opencode,openclaude" in err


def test_both_deprecation_warning_fires_once_per_process(
    capsys: pytest.CaptureFixture[str],
) -> None:
    normalize_tools(["both"])
    normalize_tools(["both"])
    err = capsys.readouterr().err
    # Single "deprecated" line even across two calls.
    assert err.count("deprecated") == 1


def test_manual_with_real_tool_raises_clierror() -> None:
    with pytest.raises(CliError) as excinfo:
        normalize_tools(["manual", "codex"])
    assert "manual" in excinfo.value.cause.lower()
    assert "next" in excinfo.value.next_step.lower() or "pick" in excinfo.value.next_step.lower()


def test_manual_alone_is_accepted() -> None:
    assert normalize_tools("manual") == ["manual"]


def test_whitespace_around_comma_is_trimmed() -> None:
    assert normalize_tools(" codex , claude-code ") == ["codex", "claude-code"]
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_normalize_tools.py -v
```

Expected: ImportError for `normalize_tools` / `DEFAULT_TOOLS` / `reset_deprecation_state` from `coding_scaffold.intake`.

- [ ] **Step 3: Implement the helper**

Add to `src/coding_scaffold/intake.py` (at top, just after the existing imports):

```python
import sys

from .errors import CliError

DEFAULT_TOOLS: tuple[str, ...] = ("opencode",)
# Legacy `--tool both` literal expansion. Removed in 0.7.0 alongside the value
# itself; see docs/docs/wiki/Upgrading.md.
_BOTH_EXPANSION: tuple[str, ...] = ("opencode", "openclaude")

# Single-fire deprecation warning state. Reset between tests via
# `reset_deprecation_state()`.
_BOTH_WARNING_FIRED: bool = False


def reset_deprecation_state() -> None:
    """Reset the once-per-process deprecation warning latch. Test-only."""

    global _BOTH_WARNING_FIRED
    _BOTH_WARNING_FIRED = False


def normalize_tools(value: str | list[str] | None) -> list[str]:
    """Return a canonical deduped tool list from any accepted input shape.

    Accepts: None, "", "codex", "codex,claude-code", ["codex"],
    ["codex", "claude-code"], ["codex,opencode", "claude-code"], ["both"].

    Expands the deprecated `both` literal to `opencode,openclaude` with a
    one-line stderr warning that fires at most once per process.

    Raises `CliError` when `manual` appears alongside any real tool — `manual`
    means "no adapter," which is incompatible with also picking a real one.
    """

    if value is None or value == "":
        return list(DEFAULT_TOOLS)
    if isinstance(value, str):
        raw_parts = [value]
    else:
        raw_parts = list(value)
    if not raw_parts:
        return list(DEFAULT_TOOLS)

    # Flatten commas + trim whitespace.
    flat: list[str] = []
    for part in raw_parts:
        for chunk in str(part).split(","):
            chunk = chunk.strip()
            if chunk:
                flat.append(chunk)
    if not flat:
        return list(DEFAULT_TOOLS)

    # Expand `both` with a one-fire deprecation warning.
    global _BOTH_WARNING_FIRED
    expanded: list[str] = []
    for chunk in flat:
        if chunk == "both":
            if not _BOTH_WARNING_FIRED:
                print(
                    "warning: '--tool both' is deprecated; "
                    "using '--tool opencode,openclaude' instead.\n"
                    "         Will be removed in 0.7.0. "
                    "See https://jrs1986.github.io/CodingScaffold/wiki/Upgrading.",
                    file=sys.stderr,
                )
                _BOTH_WARNING_FIRED = True
            expanded.extend(_BOTH_EXPANSION)
            continue
        expanded.append(chunk)

    # Dedupe, preserve first-seen order.
    seen: set[str] = set()
    canonical: list[str] = []
    for chunk in expanded:
        if chunk in seen:
            continue
        seen.add(chunk)
        canonical.append(chunk)

    # `manual` is exclusive — it means "no adapter."
    if "manual" in canonical and len(canonical) > 1:
        others = [t for t in canonical if t != "manual"]
        raise CliError(
            cause=f"`--tool manual` excludes other tools; got manual + {', '.join(others)}",
            next_step="pick one of: `--tool manual` OR `--tool <real-tool>...`",
            link="https://jrs1986.github.io/CodingScaffold/wiki/Glossary",
        )

    return canonical
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_normalize_tools.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Run the full suite + ruff**

```bash
uv run pytest tests/ -q | tail -3
uv run ruff check src/ tests/
```

Expected: 602 passed (was 590, +12); ruff clean.

- [ ] **Step 6: Commit**

```bash
git add src/coding_scaffold/intake.py tests/test_normalize_tools.py
git commit -m "Add normalize_tools helper for multi-tool intake (spec §4.3)"
```

---

## Task 2 — `IntakeAnswers.tools` field + persisted-form back-fill

**Closes §5.1, §5.2 of the spec.**

**Files:**
- Modify: `src/coding_scaffold/intake.py` (replace `tool: str | None` with `tools: list[str]`; add `_normalize_persisted_intake`)
- Modify: `tests/test_intake.py`

The Python attribute `IntakeAnswers.tool` is removed; `IntakeAnswers.tools: list[str]` is the only canonical field. `collect_intake` already calls into `_value`; that becomes `normalize_tools(_value(...))`. The `agent` property remains and returns the first tool (it's used by adapter selection elsewhere; keeping the property avoids cascading edits in this task — the next task migrates callers).

The persisted-form back-fill lets `coding-scaffold setup update` read an older `.coding-scaffold/project.json` that still has `tool: "opencode"` (no `tools` field) and silently translate it into `tools: ["opencode"]` in memory. Removed in 0.7.0.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_intake.py` (at the bottom):

```python
import json
from pathlib import Path

from coding_scaffold.intake import (
    IntakeAnswers,
    _normalize_persisted_intake,
)


def test_intake_answers_carries_tools_list() -> None:
    answers = IntakeAnswers(tools=["codex", "claude-code"])
    assert answers.tools == ["codex", "claude-code"]
    # Agent property still returns the first tool.
    assert answers.agent == "codex"


def test_intake_answers_to_dict_emits_tools_only() -> None:
    answers = IntakeAnswers(tools=["codex"])
    payload = answers.to_dict()
    assert payload["tools"] == ["codex"]
    assert "tool" not in payload, "singular `tool` must be gone from persisted form"


def test_normalize_persisted_intake_back_fills_legacy_tool_key() -> None:
    legacy = {"language": "python", "tool": "opencode"}
    normalized = _normalize_persisted_intake(legacy)
    assert normalized["tools"] == ["opencode"]
    assert "tool" not in normalized, "back-fill must strip the legacy key after migrating"


def test_normalize_persisted_intake_passes_through_modern_payload() -> None:
    modern = {"language": "python", "tools": ["codex", "claude-code"]}
    assert _normalize_persisted_intake(modern) == modern


def test_normalize_persisted_intake_handles_missing_tool(tmp_path: Path) -> None:
    # Some very old project.json files may have neither `tool` nor `tools`.
    no_tool = {"language": "python"}
    normalized = _normalize_persisted_intake(no_tool)
    assert normalized["tools"] == ["opencode"]


def test_intake_answers_default_tools_is_opencode() -> None:
    answers = IntakeAnswers()
    assert answers.tools == ["opencode"]
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_intake.py::test_intake_answers_carries_tools_list -v
```

Expected: `TypeError: __init__() got an unexpected keyword argument 'tools'` (or similar).

- [ ] **Step 3: Update `IntakeAnswers` + add the back-fill helper**

In `src/coding_scaffold/intake.py`, replace the dataclass body and add the helper. The full updated dataclass + helper:

```python
@dataclass(frozen=True)
class IntakeAnswers:
    language: str | None = None
    project_target: str | None = None
    existing_codebase: bool | None = None
    privacy: str | None = None
    tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOLS))
    preferred_local_model: str | None = None
    mode: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        return payload

    @property
    def agent(self) -> str | None:
        """First tool, or None if the list is empty.

        Adapter selection elsewhere reads `.agent`; preserving the property keeps
        those call-sites stable while the migration to `.tools` lands across the
        rest of the codebase.
        """

        return self.tools[0] if self.tools else None


def _normalize_persisted_intake(payload: dict[str, object]) -> dict[str, object]:
    """Migrate a persisted intake payload to the canonical `tools` shape.

    Legacy `.coding-scaffold/project.json` files written before 0.6.0 carry
    `tool: "opencode"` (singular). New files carry `tools: ["opencode", ...]`.
    This helper accepts either and returns a payload with only `tools` populated.

    Removed in 0.7.0 once the migration window closes; see Upgrading.md.
    """

    result = dict(payload)
    legacy = result.pop("tool", None)
    if "tools" in result:
        return result
    if legacy:
        result["tools"] = [str(legacy)]
    else:
        result["tools"] = list(DEFAULT_TOOLS)
    return result
```

You'll also need to add `field` to the existing `from dataclasses import` line:

```python
from dataclasses import asdict, dataclass, field
```

- [ ] **Step 4: Update `collect_intake` to populate `tools`**

In `src/coding_scaffold/intake.py`, replace the existing `collect_intake` body. The `tool=` line becomes:

```python
def collect_intake(target: Path, provided: IntakeAnswers, interactive: bool) -> IntakeAnswers:
    detected_language = _detect_language(target) if provided.language is None else None
    # `provided.tools` is the upstream-supplied list (from CLI or programmatic call).
    # If absent (default factory empty? — no, the dataclass default is ["opencode"]),
    # the interactive prompt can edit it.
    raw_tool_answer = _value(
        ",".join(provided.tools) if provided.tools else None,
        "Coding tools to set up (comma-separated, e.g. `codex,claude-code`)",
        "opencode",
        interactive,
    )
    return IntakeAnswers(
        language=_value(
            provided.language,
            "Primary language",
            detected_language or "python",
            interactive,
        ),
        project_target=_value(provided.project_target, "Project target", "CLI/tooling", interactive),
        existing_codebase=(
            provided.existing_codebase
            if provided.existing_codebase is not None
            else _bool_value("Existing codebase", _has_code(target), interactive)
        ),
        privacy=_value(provided.privacy, "Privacy mode", "local-first", interactive),
        tools=normalize_tools(raw_tool_answer),
        preferred_local_model=_value(
            provided.preferred_local_model,
            "Preferred local model",
            "auto",
            interactive,
        ),
        mode=_value(provided.mode, "Guidance mode", "standard", interactive),
    )
```

- [ ] **Step 5: Run the new tests to verify they pass**

```bash
uv run pytest tests/test_intake.py -v
```

Expected: every test in the file PASSes. (The legacy tests in this file used `IntakeAnswers(tool=...)`; if any do, update them to `tools=[...]` — the assertion error message will name them.)

- [ ] **Step 6: Run the full suite + ruff**

```bash
uv run pytest tests/ -q | tail -10
uv run ruff check src/ tests/
```

Expected: failures only from `intake.tool` references in `writers.py` / `updater.py` (we migrate those in Task 3) plus any test that constructed `IntakeAnswers(tool=...)`. **Do not "fix" the writers/updater here** — that's Task 3. Confirm the failure pattern matches before committing.

If only intake/writers/updater-related tests fail, proceed. Otherwise revisit Step 4.

- [ ] **Step 7: Commit (intentionally red — Task 3 turns it green)**

```bash
git add src/coding_scaffold/intake.py tests/test_intake.py
git commit -m "Add IntakeAnswers.tools list + persisted-form back-fill (spec §5)"
```

---

## Task 3 — Migrate in-src callers to `intake.tools[0]`

**Closes the data-model migration named in spec §5.1.**

**Files:**
- Modify: `src/coding_scaffold/writers.py:282` and `:295`
- Modify: `src/coding_scaffold/updater.py:54-55`
- Modify: `tests/test_writers.py`, `tests/test_updater.py` if they reference `.tool`

Every reference to `intake.tool` becomes `intake.tools[0]`. The `agent` property keeps working unchanged (still returns first tool).

- [ ] **Step 1: Update `writers.py`**

In `src/coding_scaffold/writers.py`, the two `intake.tool` references inside `_getting_started_md`:

```python
def _getting_started_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    selected_tool = intake.tools[0] if intake.tools else "opencode"
    setup_hint = (
        "Validate or install the selected coding environment with "
        f"`coding-scaffold setup tool --tool {selected_tool}`."
        if selected_tool != "manual"
        else "Use your manually selected coding environment and keep its config next to this scaffold."
    )
    return render_template(
        "writers/getting-started.md",
        setup_hint=setup_hint,
        language=intake.language,
        project_target=intake.project_target,
        privacy=intake.privacy,
        tool=selected_tool,
        mode=intake.mode,
        weak_model=routing.weak_model,
        strong_model=routing.strong_model,
    )
```

- [ ] **Step 2: Update `updater.py`**

In `src/coding_scaffold/updater.py`, lines 53-56:

```python
        manifest = write_scaffold(temp_root, intake, hardware, providers, routing)
        primary_tool = intake.tools[0] if intake.tools else "manual"
        adapter = (
            write_tool_adapter(temp_root, intake.tools)
            if primary_tool and primary_tool != "manual"
            else None
        )
```

Note: passes `intake.tools` (list) to `write_tool_adapter`. The adapter writer learns to accept a list in Task 5; until then this is a deliberately-red intermediate state.

- [ ] **Step 3: Update `_load_project_intake` to use the back-fill helper**

In `src/coding_scaffold/cli.py` (around line 2167), replace the body so it routes through `_normalize_persisted_intake` and constructs `IntakeAnswers` with `tools=` instead of `tool=`:

```python
def _load_project_intake(target: Path) -> IntakeAnswers:
    from .intake import _normalize_persisted_intake

    path = target / ".coding-scaffold" / "project.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return collect_intake(target, IntakeAnswers(), interactive=False)
    if not isinstance(payload, dict):
        return collect_intake(target, IntakeAnswers(), interactive=False)
    # Back-fill: legacy `tool` becomes modern `tools`; modern files pass through.
    payload = _normalize_persisted_intake(payload)
    # Also accept the historical `agent` alias for `tool`.
    tools_value = payload.get("tools") or (
        [_string_or_none(payload.get("agent"))] if payload.get("agent") else None
    )
    return collect_intake(
        target,
        IntakeAnswers(
            language=_string_or_none(payload.get("language")),
            project_target=_string_or_none(payload.get("project_target")),
            existing_codebase=_bool_or_none(payload.get("existing_codebase")),
            privacy=_string_or_none(payload.get("privacy")),
            tools=[t for t in (tools_value or []) if t] or list(DEFAULT_TOOLS),
            preferred_local_model=_string_or_none(payload.get("preferred_local_model")),
            mode=_string_or_none(payload.get("mode")),
        ),
        interactive=False,
    )
```

Also add `DEFAULT_TOOLS` to the existing `from .intake import ...` line at the top of `cli.py`.

- [ ] **Step 4: Update test constructions**

Search and update:

```bash
grep -rn "IntakeAnswers(tool=\|IntakeAnswers(.*\btool=" tests/ src/
```

For each hit, change `tool="X"` to `tools=["X"]`. Expected files: at least `tests/test_writers.py`, `tests/test_intake.py` (test fixtures), possibly `tests/conftest.py` factories.

- [ ] **Step 5: Run the suite**

```bash
uv run pytest tests/ -q | tail -10
```

Expected: still some failures in `test_adapters.py` (Task 5 migrates the adapter signature) and possibly `test_cli.py` (Task 6 migrates the parser). Confirm those are the only remaining failures, then proceed.

- [ ] **Step 6: Commit**

```bash
git add src/coding_scaffold/writers.py src/coding_scaffold/updater.py src/coding_scaffold/cli.py tests/
git commit -m "Migrate writers/updater/_load_project_intake/test fixtures to intake.tools"
```

---

## Task 4 — `routing.json` emits `tools` only

**Closes §5.2 of the spec.**

**Files:**
- Modify: `src/coding_scaffold/router.py` (the `to_dict` on `RoutingPlan`)
- Modify: `tests/test_router.py` (or wherever `routing.json` shape is asserted)

- [ ] **Step 1: Locate the routing.json emitter**

```bash
grep -n "to_dict\|tools\|tool" src/coding_scaffold/router.py | head -20
```

You're looking for the `RoutingPlan.to_dict()` method around line 28.

- [ ] **Step 2: Write the failing test**

Add to `tests/test_router.py`:

```python
def test_routing_plan_to_dict_includes_tools_list_only() -> None:
    from coding_scaffold.intake import IntakeAnswers
    from coding_scaffold.hardware import HardwareProfile
    from coding_scaffold.providers import Provider
    from coding_scaffold.router import build_routing_plan

    intake = IntakeAnswers(tools=["codex", "claude-code"], language="python")
    hardware = HardwareProfile(
        os_name="macos", arch="arm64", cpu="apple", ram_gb=16,
        gpu=None, accelerators=[], is_wsl=False, llmfit_available=False,
    )
    providers: list[Provider] = []
    plan = build_routing_plan(intake, hardware, providers)
    payload = plan.to_dict()
    assert payload["tools"] == ["codex", "claude-code"]
    assert "tool" not in payload, "singular `tool` must be gone from routing.json"
```

(Check `HardwareProfile` actual constructor signature first — match it.)

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run pytest tests/test_router.py -v -k tools
```

Expected: KeyError or AssertionError because `"tools"` is missing.

- [ ] **Step 4: Update `RoutingPlan` so it carries tools**

In `src/coding_scaffold/router.py`:

1. Add `tools: list[str]` to the `RoutingPlan` dataclass (or wherever it's defined).
2. In `build_routing_plan`, pass `intake.tools` to the constructor.
3. In `to_dict`, add `"tools": list(self.tools)` and ensure no `"tool"` key is emitted.

Exact patch shape (verify against your actual file):

```python
@dataclass(frozen=True)
class RoutingPlan:
    ...
    tools: list[str]
    ...

    def to_dict(self) -> dict[str, object]:
        return {
            ...
            "tools": list(self.tools),
            ...
        }


def build_routing_plan(intake, hardware, providers) -> RoutingPlan:
    return RoutingPlan(
        ...
        tools=list(intake.tools),
        ...
    )
```

- [ ] **Step 5: Verify the test passes + full suite**

```bash
uv run pytest tests/test_router.py -v
uv run pytest tests/ -q | tail -10
uv run ruff check src/ tests/
```

Expected: router tests pass; remaining failures only in `test_adapters.py` / `test_cli.py` / `test_pilot.py`.

- [ ] **Step 6: Commit**

```bash
git add src/coding_scaffold/router.py tests/test_router.py
git commit -m "routing.json carries tools list, drops singular tool key (spec §5.2)"
```

---

## Task 5 — `write_tool_adapter` accepts list

**Closes §6.1 of the spec.**

**Files:**
- Modify: `src/coding_scaffold/adapters.py:23-26`
- Modify: `tests/test_adapters.py`

`write_tool_adapter` already has a `tool == "both"` branch that loops over `["opencode", "openclaude"]`. Generalize so it accepts either a string (back-compat for ad-hoc callers) or a list. The legacy `both` branch is retained until Task 9 (deprecation), at which point `normalize_tools` handles it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_adapters.py`:

```python
def test_write_tool_adapter_accepts_list_of_tools(tmp_path: Path) -> None:
    from coding_scaffold.adapters import write_tool_adapter
    from coding_scaffold.writers import write_scaffold
    from coding_scaffold.intake import IntakeAnswers
    # ... bootstrap a scaffold dir with routing.json so adapters can read it
    # Use the existing fixture/factory if present; otherwise inline:
    intake = IntakeAnswers(tools=["codex", "claude-code"], language="python")
    # write_scaffold needs hardware, providers, routing — reuse a factory if
    # tests/conftest.py defines one. Otherwise:
    from tests.conftest import sample_hardware, sample_routing  # adapt to actual fixture names
    write_scaffold(tmp_path, intake, sample_hardware(), [], sample_routing(intake))

    result = write_tool_adapter(tmp_path, ["codex", "claude-code"])
    written_paths = {p.name for p in result.files}
    # Codex writes AGENTS.md at root + codex template files; Claude writes CLAUDE.md + .claude/
    assert "AGENTS.md" in written_paths
    assert "CLAUDE.md" in written_paths


def test_write_tool_adapter_string_argument_still_works(tmp_path: Path) -> None:
    """Backward-compat: existing ad-hoc callers still pass a string."""

    from coding_scaffold.adapters import write_tool_adapter
    # ... bootstrap as above ...
    result = write_tool_adapter(tmp_path, "codex")
    assert any(p.name == "AGENTS.md" for p in result.files)
```

(Adapt fixture imports to whatever `tests/conftest.py` actually exposes.)

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_adapters.py::test_write_tool_adapter_accepts_list_of_tools -v
```

Expected: TypeError or similar — the function doesn't accept a list yet.

- [ ] **Step 3: Generalize `write_tool_adapter`**

In `src/coding_scaffold/adapters.py` replace the top of the function:

```python
def write_tool_adapter(target: Path, tool: str | list[str]) -> AdapterResult:
    from .intake import normalize_tools

    root = target.expanduser().resolve()
    files: list[Path] = []
    skipped: list[Path] = []
    routing = load_routing_payload(root)
    tools = normalize_tools(tool)   # accepts str | list, deduped, with `both` expansion
    for selected in tools:
        if selected == "opencode":
            result = _write_opencode(root, routing)
        elif selected == "claude-code":
            result = _write_claude_code(root, routing)
        elif selected == "codex":
            result = _write_codex(root, routing)
        elif selected == "openclaude":
            result = _write_openclaude(root, routing)
        elif selected == "hermes":
            ...   # keep existing branches
```

Delete the original `tools = ["opencode", "openclaude"] if tool == "both" else [tool]` line — `normalize_tools` covers it.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_adapters.py -v
```

Expected: all adapter tests pass (the existing `--tool both` test still passes because `normalize_tools` expands it).

- [ ] **Step 5: Run full suite + ruff**

```bash
uv run pytest tests/ -q | tail -5
uv run ruff check src/ tests/
```

Expected: `test_cli.py` / `test_pilot.py` failures remain; everything else green.

- [ ] **Step 6: Commit**

```bash
git add src/coding_scaffold/adapters.py tests/test_adapters.py
git commit -m "write_tool_adapter accepts list of tools via normalize_tools (spec §6.1)"
```

---

## Task 6 — CLI parser changes (`--tool` becomes `action="append"`)

**Closes §4.1, §4.2, §4.3 of the spec.**

**Files:**
- Modify: `src/coding_scaffold/cli.py` (six subparser definitions + post-parse normalization)
- Modify: `tests/test_cli.py`

Switch `--tool` to `action="append"` on every relevant surface: `setup run`, `init` (hidden), `wizard` (hidden), `setup tool`, `setup-tool` (hidden), `tools adapt`. **Pilot is NOT touched in this task** — its multi-tool output is more involved and lands in Task 7.

After argparse, every command-handler that consumes `args.tool` (now `args.tool_raw` after rename) normalizes via `normalize_tools` and writes back `args.tools`. To keep the diff small, do this in `main()` immediately after `parse_args`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
def test_cli_setup_run_accepts_repeatable_tool_flag() -> None:
    from coding_scaffold.cli import build_parser
    args = build_parser().parse_args(
        ["setup", "run", "--tool", "codex", "--tool", "claude-code"]
    )
    # action="append" puts each value into a list; normalization happens later.
    assert args.tool_raw == ["codex", "claude-code"]


def test_cli_setup_run_accepts_comma_separated_tool() -> None:
    from coding_scaffold.cli import build_parser
    args = build_parser().parse_args(
        ["setup", "run", "--tool", "codex,claude-code"]
    )
    assert args.tool_raw == ["codex,claude-code"]


def test_cli_main_normalizes_tools_into_args_tools(
    tmp_path, monkeypatch, capsys
) -> None:
    """`main()` runs normalize_tools on args.tool_raw and stashes args.tools."""

    from coding_scaffold.cli import build_parser, main
    # Use a flag-only command that doesn't actually do filesystem work, e.g.,
    # `setup tool` with a list — or assert via a custom dispatch fixture if
    # appropriate. Simplest path: invoke through main with `--help`-like
    # dry-run support, or test the normalization wrapper directly:
    from coding_scaffold.cli import _normalize_args_tools_in_place
    import argparse
    ns = argparse.Namespace(tool_raw=["codex,claude-code"])
    _normalize_args_tools_in_place(ns)
    assert ns.tools == ["codex", "claude-code"]


def test_cli_setup_tool_install_accepts_list_of_tools() -> None:
    from coding_scaffold.cli import build_parser
    args = build_parser().parse_args(
        ["setup", "tool", "--tool", "codex", "--tool", "claude-code", "--install"]
    )
    assert args.tool_raw == ["codex", "claude-code"]


def test_cli_tools_adapt_accepts_repeatable_tool_flag() -> None:
    from coding_scaffold.cli import build_parser
    args = build_parser().parse_args(
        ["tools", "adapt", "--tool", "codex", "--tool", "claude-code"]
    )
    assert args.tool_raw == ["codex", "claude-code"]


def test_cli_main_rejects_manual_with_real_tool(capsys) -> None:
    from coding_scaffold.cli import main
    rc = main(["setup", "run", "--tool", "manual", "--tool", "codex", "--target", "."])
    err = capsys.readouterr().err
    assert rc == 1
    assert "manual" in err.lower()
    assert "next:" in err
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/test_cli.py -v -k "tool_raw or tools"
```

Expected: AttributeError for `tool_raw` / `_normalize_args_tools_in_place`.

- [ ] **Step 3: Update the six subparsers**

For each subparser that currently has `--tool` (the list from spec §4.2 — find them with `grep -n '"--tool"' src/coding_scaffold/cli.py`), change:

Before:
```python
parser.add_argument("--tool", choices=CODING_TOOLS, ...)
```

After:
```python
parser.add_argument(
    "--tool",
    choices=CODING_TOOLS,
    action="append",
    dest="tool_raw",
    default=None,
    help="Coding tool to set up. Repeat or comma-separate for multi-tool projects.",
)
```

Also update the existing `--agent` and `--coding-tool` hidden aliases to point at `dest="tool_raw"` (they currently point at `dest="tool"`).

**Important:** the existing `tool=intake.tool` plumbing inside setup-orchestration code paths must switch to reading `args.tools` (the normalized list). Search:

```bash
grep -n "args.tool\b" src/coding_scaffold/cli.py
```

For each hit, change to `args.tools` (now a list) and pass through accordingly.

- [ ] **Step 4: Add the post-parse normalizer**

Add to `src/coding_scaffold/cli.py` (near `_hide_suppressed_subcommands`):

```python
def _normalize_args_tools_in_place(args: argparse.Namespace) -> None:
    """If args carries a `tool_raw` from `action="append"`, normalize it into
    a canonical `tools` list. Surfaces that don't use --tool leave args
    untouched.
    """

    raw = getattr(args, "tool_raw", None)
    if raw is None and not hasattr(args, "tools"):
        # Nothing to do for surfaces that don't take --tool.
        return
    try:
        from .intake import normalize_tools
        args.tools = normalize_tools(raw)
    except CliError as exc:
        from .errors import fail_with
        fail_with(cause=exc.cause, next_step=exc.next_step, link=exc.link)
```

(Add `from .errors import CliError` near the top of cli.py if it isn't already imported.)

In `main()`, call this immediately after `args = parser.parse_args(argv)`:

```python
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _normalize_args_tools_in_place(args)
    ...
```

- [ ] **Step 5: Verify all tests pass**

```bash
uv run pytest tests/ -q | tail -10
uv run ruff check src/ tests/
```

Expected: tests for cli, writers, updater, adapters, router, intake all pass. `test_pilot.py` failures still expected; Task 7 fixes them.

- [ ] **Step 6: Commit**

```bash
git add src/coding_scaffold/cli.py tests/test_cli.py
git commit -m "CLI: --tool becomes action=append across 6 surfaces (spec §4)"
```

---

## Task 7 — Pilot multi-tool output

**Closes §7.1, §7.2, §7.3 of the spec.**

**Files:**
- Modify: `src/coding_scaffold/pilot.py` (whole `run_pilot` + `format_pilot_text` + `PilotReport`)
- Modify: `tests/test_pilot.py`
- Modify: `tests/test_cli_ux.py` (pilot CLI tests)

The `pilot` subparser also switches to `action="append"` (so it now accepts `--tool codex,claude-code`). `run_pilot` accepts `tools: list[str]`. The `tool: str` parameter stays as a deprecated kwarg that calls `normalize_tools` so any in-process Python callers (and a few tests) keep working without edit.

Output shape per spec §7.1 (single-tool unchanged; multi-tool adds the `Tools:` header and per-tool agent steps).

JSON shape per spec §7.2 (only `tools`, no singular `tool`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_pilot.py`:

```python
def test_pilot_accepts_multi_tool_list(tmp_path: Path) -> None:
    from coding_scaffold.pilot import run_pilot
    report = run_pilot(tmp_path, tools=["codex", "claude-code"])
    assert report.tools == ["codex", "claude-code"]
    # Setup step is shared
    assert "--tool codex,claude-code" in report.steps[0]
    # One agent step per tool at the tail
    agent_steps = [s for s in report.steps if "/first-session" in s]
    assert len(agent_steps) == 2


def test_pilot_environment_ok_requires_all_tools_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AND across selected tools — if any is missing, environment_ok is False."""

    import coding_scaffold.pilot as pilot_module
    monkeypatch.setattr(pilot_module.shutil, "which", lambda name: f"/usr/bin/{name}" if name in {"git", "codex", "ollama"} else None)
    from coding_scaffold.pilot import run_pilot
    report = run_pilot(tmp_path, tools=["codex", "claude-code"])
    assert report.environment_ok is False
    # Per-tool entries record individual status
    per_tool = report.environment["tools"]
    by_name = {entry["name"]: entry["installed"] for entry in per_tool}
    assert by_name["codex"] is True
    assert by_name["claude-code"] is False


def test_pilot_json_emits_tools_list_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from coding_scaffold.cli import main
    rc = main(["pilot", "--target", str(tmp_path), "--tool", "codex,claude-code", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tools"] == ["codex", "claude-code"]
    assert "tool" not in payload, "pilot JSON must not carry singular tool"
    assert "tool" not in payload["environment"], "environment must not carry singular tool"
    assert len(payload["environment"]["tools"]) == 2


def test_pilot_single_tool_output_is_unchanged(tmp_path: Path) -> None:
    """Golden: single-tool pilot keeps today's text format bit-for-bit."""

    from coding_scaffold.pilot import format_pilot_text, run_pilot
    text = format_pilot_text(run_pilot(tmp_path, tool="opencode"))
    # Today's format has no "Tools:" header for single-tool.
    assert "Tools:" not in text or "Tools: opencode" in text  # Either omit or single line OK
    assert "Run these next" in text
    # Three numbered steps as before.
    assert "  1. " in text and "  2. " in text and "  3. " in text


def test_pilot_text_multi_tool_has_tools_header_and_shared_setup(tmp_path: Path) -> None:
    from coding_scaffold.pilot import format_pilot_text, run_pilot
    text = format_pilot_text(run_pilot(tmp_path, tools=["codex", "claude-code"]))
    assert "Tools: codex, claude-code" in text
    # Shared setup step lives in "Run these once"
    assert "Run these once" in text
    # Per-tool agent steps live in "Then start a session"
    assert "Then start a session" in text
    assert "codex" in text and "claude" in text
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/test_pilot.py -v -k "multi_tool or json_emits"
```

Expected: TypeError on the `tools=` kwarg, or AssertionError on missing fields.

- [ ] **Step 3: Update `PilotReport` to carry `tools`**

In `src/coding_scaffold/pilot.py`, replace the `tool: str` field with `tools: list[str]`. The current `tool` attribute is removed. `to_dict()` emits `tools` only.

```python
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
```

- [ ] **Step 4: Update `run_pilot` signature**

```python
def run_pilot(
    target: Path | None = None,
    *,
    tool: str | None = None,           # back-compat shim (kwarg)
    tools: list[str] | None = None,
    persona: str = DEFAULT_PERSONA,
) -> PilotReport:
    """Build a structured PilotReport.

    Pass `tools=[...]` for the canonical multi-tool path. The `tool=` kwarg
    is preserved for backward-compatible callers; it is normalized via
    `normalize_tools` (so legacy passes like `tool="opencode"` keep working).
    """

    from .intake import normalize_tools
    if tools is not None:
        canonical = normalize_tools(tools)
    else:
        canonical = normalize_tools(tool if tool is not None else "opencode")
    ...
```

The rest of the function loops over `canonical` for the per-tool environment probes (build `env_info["tools"]: list[dict]` with `{name, binary, installed}` per tool), computes `environment_ok = ... and all(per_tool installed)`, and produces `steps` per spec §7.1.

- [ ] **Step 5: Update `format_pilot_text` for the multi-tool branch**

When `len(report.tools) == 1`, render today's format unchanged (preserve golden tests). When `len(report.tools) > 1`, add the `Tools:` header, per-tool environment lines, swap "Run these next (in order):" for "Run these once (covers all selected tools):", and append "Then start a session with whichever tool you reach for today:" with one line per tool.

(The full template lives in spec §7.1 — copy it verbatim.)

- [ ] **Step 6: Update the pilot subparser in `cli.py`**

```python
pilot.add_argument(
    "--tool",
    choices=list(PILOT_SUPPORTED_TOOLS),
    action="append",
    dest="tool_raw",
    default=None,
    help="Coding tool(s) to weave into the recipe (default: opencode). "
         "Repeat or comma-separate for multi-tool projects.",
)
```

Update `_cmd_pilot` in cli.py:

```python
def _cmd_pilot(args: argparse.Namespace) -> int:
    try:
        report = run_pilot(
            args.target,
            tools=getattr(args, "tools", None),
            persona=getattr(args, "persona", DEFAULT_PERSONA),
        )
    except ValueError as exc:
        ...
```

- [ ] **Step 7: Run all the pilot tests**

```bash
uv run pytest tests/test_pilot.py tests/test_cli_ux.py -v
```

Expected: all pass. If single-tool golden tests fail, the `len(report.tools) == 1` branch in `format_pilot_text` is rendering differently — fix until bit-for-bit equivalent.

- [ ] **Step 8: Run full suite + ruff**

```bash
uv run pytest tests/ -q | tail -5
uv run ruff check src/ tests/
```

Expected: all 602+ tests pass; ruff clean.

- [ ] **Step 9: Commit**

```bash
git add src/coding_scaffold/pilot.py src/coding_scaffold/cli.py tests/test_pilot.py tests/test_cli_ux.py
git commit -m "Pilot: multi-tool output, environment AND, JSON shape (spec §7)"
```

---

## Task 8 — End-to-end `test_multi_tool.py`

**Closes the "end-to-end coverage" line in spec §9.2.**

**Files:**
- Create: `tests/test_multi_tool.py`

One file, ~120 lines, exercising the canonical user-facing flows.

- [ ] **Step 1: Write the file**

Create `tests/test_multi_tool.py`:

```python
"""End-to-end coverage for multi-tool intake (spec §9.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coding_scaffold.cli import main


def test_setup_run_two_tools_writes_both_adapter_sets(tmp_path: Path) -> None:
    """One setup run with --tool codex --tool claude-code produces both
    AGENTS.md (codex) and CLAUDE.md (claude-code)."""

    rc = main([
        "setup", "run",
        "--target", str(tmp_path),
        "--tool", "codex",
        "--tool", "claude-code",
        "--non-interactive",
    ])
    assert rc == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    # routing.json carries the tools list, not a singular tool.
    routing = json.loads((tmp_path / ".coding-scaffold" / "routing.json").read_text())
    assert routing["tools"] == ["codex", "claude-code"]
    assert "tool" not in routing


def test_tools_adapt_with_comma_separated_tool_writes_both(tmp_path: Path) -> None:
    # Bootstrap routing.json first by running setup with one tool.
    main(["setup", "run", "--target", str(tmp_path), "--tool", "codex", "--non-interactive"])
    # Then `tools adapt` with comma-separated value.
    rc = main([
        "tools", "adapt",
        "--target", str(tmp_path),
        "--tool", "codex,claude-code",
    ])
    assert rc == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()


def test_tools_adapt_is_idempotent_on_rerun(tmp_path: Path) -> None:
    main(["setup", "run", "--target", str(tmp_path), "--tool", "codex,claude-code", "--non-interactive"])
    # Re-running should skip every file (no new writes), report skipped count.
    rc = main(["tools", "adapt", "--target", str(tmp_path), "--tool", "codex,claude-code"])
    assert rc == 0


def test_pilot_json_multi_tool_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main([
        "pilot", "--target", str(tmp_path),
        "--tool", "codex,claude-code", "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tools"] == ["codex", "claude-code"]
    assert "tool" not in payload
    tools_env = payload["environment"]["tools"]
    assert len(tools_env) == 2
    assert {entry["name"] for entry in tools_env} == {"codex", "claude-code"}


def test_both_alias_still_works_with_deprecation_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main([
        "setup", "run",
        "--target", str(tmp_path),
        "--tool", "both",
        "--non-interactive",
    ])
    assert rc == 0
    err = capsys.readouterr().err
    assert "deprecated" in err.lower()
    assert "0.7.0" in err
    routing = json.loads((tmp_path / ".coding-scaffold" / "routing.json").read_text())
    assert routing["tools"] == ["opencode", "openclaude"]


def test_manual_plus_real_tool_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main([
        "setup", "run",
        "--target", str(tmp_path),
        "--tool", "manual",
        "--tool", "codex",
        "--non-interactive",
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "manual" in err.lower()
    assert "next:" in err
    assert "see:" in err


def test_legacy_project_json_with_singular_tool_still_updates(tmp_path: Path) -> None:
    """A `project.json` written by 0.5.x (with `tool` instead of `tools`)
    must be readable by `setup update`."""

    # Bootstrap modern, then mutate the file back to legacy shape.
    main(["setup", "run", "--target", str(tmp_path), "--tool", "codex", "--non-interactive"])
    project_json = tmp_path / ".coding-scaffold" / "project.json"
    payload = json.loads(project_json.read_text())
    del payload["tools"]
    payload["tool"] = "codex"
    project_json.write_text(json.dumps(payload))
    # setup update should silently back-fill and run.
    rc = main(["setup", "update", "--target", str(tmp_path)])
    assert rc == 0
    # After the update, the file is rewritten in the modern shape.
    new_payload = json.loads(project_json.read_text())
    assert "tools" in new_payload
    assert new_payload["tools"] == ["codex"]
```

- [ ] **Step 2: Run the new file**

```bash
uv run pytest tests/test_multi_tool.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 3: Run full suite + ruff one more time**

```bash
uv run pytest tests/ -q | tail -3
uv run ruff check src/ tests/
```

Expected: ~609 passed (590 baseline + 12 normalize + 6 intake + 5 cli + 4 pilot + 1 router + 7 end-to-end; exact count may vary), ruff clean.

- [ ] **Step 4: Commit**

```bash
git add tests/test_multi_tool.py
git commit -m "End-to-end tests for multi-tool intake"
```

---

## Task 9 — Docs + CHANGELOG + doc-audit grep

**Closes §10 of the spec.**

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/docs/wiki/Glossary.md`
- Modify: `docs/docs/wiki/Getting-Started.md`
- Modify: `docs/docs/wiki/Upgrading.md`
- Modify: `docs/docs/wiki/Tool-Adapters.md`

- [ ] **Step 1: CHANGELOG entry**

In `CHANGELOG.md`, under `[Unreleased]`, add (or extend if `Added` / `Changed` / `Deprecated` headings already exist):

```markdown
### Added

- **Multi-tool projects: `--tool` accepts a list.** `coding-scaffold setup run
  --tool codex --tool claude-code` (or `--tool codex,claude-code`) generates
  both tools' adapters in a single pass. Supported on `setup run`,
  `tools adapt`, `setup tool`, and `pilot`. `pilot` prints a shared setup
  step plus one per-tool agent step.

### Changed

- **Breaking (single-key removal): `routing.json`, `project.json`, and pilot
  JSON output now carry `tools` (a list) only.** The singular `tool` key is
  gone. Read `tools[0]` if you need a single value. Legacy `project.json`
  files with `tool` are back-filled on read for one release window
  (removed in 0.7.0). See [Upgrading](docs/docs/wiki/Upgrading.md).

### Deprecated

- **`--tool both`** is deprecated and will be removed in 0.7.0. Use
  `--tool opencode,openclaude` instead.
```

- [ ] **Step 2: Glossary entry**

In `docs/docs/wiki/Glossary.md`, alphabetically (between `memory` and `orchestration` if those exist):

```markdown
## multi-tool project

A project configured with more than one coding tool — e.g., Codex + Claude
Code in the same repo. Generated via `coding-scaffold setup run --tool codex
--tool claude-code` (or comma-separated). Each tool gets its native adapter
files (e.g., `AGENTS.md` for Codex, `CLAUDE.md` for Claude Code) generated
side-by-side; the scaffold's `setup update` keeps them in sync going
forward.
```

- [ ] **Step 3: Getting-Started subsection**

Add to `docs/docs/wiki/Getting-Started.md` under "Smallest Useful Path":

```markdown
### Two tools in one repo

If you use more than one coding tool on the same project (e.g., Codex + Claude
Code), pass `--tool` for each one in a single setup run:

```bash
coding-scaffold setup run --target . --tool codex --tool claude-code --mode beginner
# or equivalently:
coding-scaffold setup run --target . --tool codex,claude-code --mode beginner
```

`AGENTS.md` (Codex's project rules) and `CLAUDE.md` (Claude Code's project
rules) are both generated; the scaffold's `setup update` keeps them in sync.

`coding-scaffold pilot --target . --tool codex,claude-code` prints one shared
setup step plus a per-tool agent step at the bottom.
```

- [ ] **Step 4: Upgrading.md — 0.6.0 + 0.7.0 Breaking blocks**

Add to `docs/docs/wiki/Upgrading.md`, before the "When `setup update` is not the right tool" section:

```markdown
## Breaking change in 0.6.0 — singular `tool` JSON key removed

`routing.json`, `project.json`, and the pilot JSON output used to carry a
singular `tool` key. These are gone — only `tools` (a list) remains. The
migration is a one-line change for any script that read them:

```python
# Before
config["tool"]            # "codex"

# After
config["tools"][0]        # "codex"
```

Legacy `project.json` files written by 0.5.x (with `tool` instead of `tools`)
are back-filled when `setup update` reads them, so existing projects upgrade
cleanly. The back-fill is removed in 0.7.0.

## Breaking change planned for 0.7.0 — `--tool both` removed

`--tool both` is currently a deprecated alias for `--tool opencode,openclaude`
and prints a warning when used. In 0.7.0 it is removed entirely; argparse
will reject it with an "invalid choice" error.

Update any scripts or CI invocations now:

```bash
# Before
coding-scaffold setup run --tool both

# After
coding-scaffold setup run --tool opencode,openclaude
```

The `_normalize_persisted_intake` back-fill helper also lands its sunset
in 0.7.0; any `project.json` file still on the legacy `tool` shape must be
upgraded by running `setup update` in 0.6.x first.
```

- [ ] **Step 5: Tool-Adapters.md preamble + example**

Find the capability matrix preamble in `docs/docs/wiki/Tool-Adapters.md` and add:

```markdown
**Multi-tool projects:** every adapter listed here can be generated alongside
another via `setup run --tool <a> --tool <b>` (or `--tool a,b`). Codex + Claude
Code in the same repo is the most common pair; see
[Getting-Started](./Getting-Started.md#two-tools-in-one-repo).
```

- [ ] **Step 6: Doc audit grep (mandatory; spec §10)**

Run:

```bash
grep -rn '"tool":\|`tool` key\|routing\.tool\b' docs/docs/wiki/ docs/docs/superpowers/ README.md AGENTS.md 2>&1 \
  | grep -v "tools" | grep -v "setup-tool" | grep -v "tool-" | grep -v "tools-" \
  | grep -v "spec.*2026-05-25-multi-tool"
```

Expected: empty output. Any remaining hit is a doc that still references the singular `tool` JSON key — fix inline before merging.

- [ ] **Step 7: Build docs locally to catch dead links**

```bash
cd docs && npx rspress build 2>&1 | tail -5
```

Expected: exit 0; no `Dead link` or `Error` messages. Return to repo root with `cd ..`.

- [ ] **Step 8: Final full test + ruff + commit**

```bash
uv run pytest tests/ -q | tail -3
uv run ruff check src/ tests/
git add CHANGELOG.md docs/
git commit -m "Docs: multi-tool intake (CHANGELOG, Glossary, Getting-Started, Upgrading, Tool-Adapters)"
```

- [ ] **Step 9: Push and open the PR**

```bash
git push -u origin feat/multi-tool-intake
gh pr create \
  --title "Multi-tool intake: --tool accepts a list across setup, tools adapt, pilot (spec)" \
  --body "$(cat <<'EOF'
## Summary

One PR implementing the [Multi-Tool Intake design](docs/docs/superpowers/specs/2026-05-25-multi-tool-intake-design.md). `--tool` now accepts a list everywhere it's accepted, so projects with two coding tools (e.g., Codex + Claude Code) can be configured in one `setup run`.

**Breaking** (one release): `routing.json`, `project.json`, pilot JSON, and the `IntakeAnswers.tool` Python attribute drop the singular `tool` key/field in favor of `tools` (a list). Back-fill for legacy `project.json` is in place for one release window; removed in 0.7.0 alongside the `--tool both` alias.

**Deprecated**: `--tool both` warns now, removed in 0.7.0.

## Test plan
- [x] \`uv run pytest -q\` — all tests pass.
- [x] \`uv run ruff check src/ tests/\` — clean.
- [x] \`cd docs && npx rspress build\` — exits 0, no dead-link warnings.
- [x] \`coding-scaffold setup run --target /tmp/scratch --tool codex --tool claude-code\` writes both AGENTS.md and CLAUDE.md.
- [x] \`coding-scaffold pilot --target . --tool codex,claude-code\` prints the multi-tool recipe.
- [x] \`--tool both\` still works in 0.6.x with a deprecation warning.
- [x] \`--tool manual --tool codex\` exits 1 with a three-line error.
EOF
)"
```

---

## Self-review checklist (run after writing the plan; before handing off)

- [ ] Every section in the spec maps to at least one task (cross-reference §4 → Tasks 1 & 6, §5 → Tasks 2 & 4 & 7, §6 → Task 5, §7 → Task 7, §8 → Task 1 & 9, §9 → Tasks 1-8, §10 → Task 9).
- [ ] No "TBD" / "TODO" / "implement later" in any task body — every step has either complete code or a complete command.
- [ ] Names used across tasks are stable: `normalize_tools`, `_normalize_persisted_intake`, `_normalize_args_tools_in_place`, `IntakeAnswers.tools`, `PilotReport.tools`, `args.tool_raw`, `args.tools` — same spellings everywhere.
- [ ] Order of tasks supports TDD: each task lands tests + code together and ends with `pytest + ruff` green or with explicitly-named expected failures (clearly marked, Task 2 → Task 3 is the only such handoff).
- [ ] Frequent commits — every task ends with one or two `git commit`.
- [ ] Single PR shape preserved (one branch, one PR at Task 9 step 9).
