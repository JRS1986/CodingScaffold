# Multi-Tool Intake — Design

**Status:** approved (brainstorming → design).
**Author:** brainstorm with @jrs1986, 2026-05-25.
**Related:** none open. Closes the "one repo, two coding tools" gap that's been
quietly worked around (this very repo ships both `AGENTS.md` and `CLAUDE.md`).
**Target release:** 0.6.0 (deprecation), 0.7.0 (removal of `both`).

## 1. Problem

`coding-scaffold setup run --tool <X>` accepts a single tool name. Projects that
use two coding tools at once (e.g., Codex + Claude Code on the same repo) have
no first-class path: they run `setup run` twice, or they hand-edit one of
`AGENTS.md` / `CLAUDE.md` to stay in sync. The existing `--tool both` literal
sounds like it solves this, but it expands to `opencode + openclaude` only —
not Codex + Claude Code, not Claude Code + OpenCode, not any other pair.

Concrete pain (observed in this repo):

- `AGENTS.md` (Codex's project rules) and `CLAUDE.md` (Claude Code's project
  rules) both committed, written at different times, drift risk if either is
  hand-edited later.
- The `IntakeAnswers.tool: str` field bakes one tool into `routing.json`, which
  affects downstream model-selection guidance and the `setup update`
  reconciliation flow.

## 2. Goals

1. `coding-scaffold setup run --tool codex --tool claude-code` works in one
   pass and writes both tools' adapters.
2. `coding-scaffold pilot --tool codex,claude-code` prints one shared setup
   recipe plus a per-tool agent step.
3. Existing single-value invocations (`--tool codex`) keep working unchanged.
4. `--tool both` deprecation has a sane two-release path so existing scripts
   keep working in 0.6.0 and fail with a clear next-step in 0.7.0.

## 3. Non-goals

- Cross-tool canonical rules file (approach B from the brainstorm). AGENTS.md
  and CLAUDE.md remain independently rendered from the same intake; drift
  between them after hand-edit is not solved here.
- Per-tool policy enforcement (approach C). Policy/MCP/permissions still target
  one tool's surface at a time.
- New tool support. The known tool set
  (`opencode | claude-code | codex | openclaude | hermes | pi`) is unchanged.

## 4. CLI surface

### 4.1 New shape

```bash
# repeatable
coding-scaffold setup run --tool codex --tool claude-code

# comma-separated (equivalent)
coding-scaffold setup run --tool codex,claude-code

# unchanged — single value still works
coding-scaffold setup run --tool codex

# pilot accepts the same shape, prints a per-tool recipe
coding-scaffold pilot --target . --tool codex,claude-code

# tools adapt — already loops internally; now driven by --tool list
coding-scaffold tools adapt --tool codex,claude-code

# setup tool --install — installs each tool in the list
coding-scaffold setup tool --tool codex,claude-code --install
```

### 4.2 Affected subparsers

The list-typed `--tool` lands on every CLI surface where setup-time tool
choice is meaningful:

- `setup run` (canonical)
- `init` (hidden alias of `setup run`)
- `wizard` (hidden alias of `setup run`)
- `setup tool` (install / validate)
- `setup-tool` (hidden flat alias)
- `tools adapt`
- `pilot` (new — was single-valued)

`doctor` is unchanged; it surveys the artifact registry which already lists
both `AGENTS.md` and `CLAUDE.md`.

### 4.3 Argparse pattern

```python
parser.add_argument(
    "--tool",
    choices=CODING_TOOLS,   # `both` stays here through 0.6.x; removed in 0.7.0
    action="append",
    dest="tool_raw",
    default=None,
)
# After parse:
args.tools = normalize_tools(args.tool_raw)   # list[str], deduped, expanded
args.tool = args.tools[0]                     # back-compat single value
```

`normalize_tools` lives in `cli.py` and is shared by every surface that takes
`--tool`. It:

1. Returns `["opencode"]` when input is `None` or `[]` (today's default).
2. Splits any comma-separated value (`["codex,claude-code"] → ["codex", "claude-code"]`).
3. Expands the deprecated `both` literal to `["opencode", "openclaude"]` and
   prints the deprecation warning to stderr exactly once per invocation.
4. Dedupes while preserving first-seen order.
5. Rejects `manual` combined with any real tool — raises via the shared
   `fail_with` error helper with cause `\`--tool manual\` excludes other tools`
   and next-step `pick one of: \`--tool manual\` OR \`--tool <real-tool>...\``.

## 5. Data model

### 5.1 `IntakeAnswers` (in `intake.py`)

```python
@dataclass
class IntakeAnswers:
    ...
    tools: list[str]            # NEW — canonical, ordered, deduped, never empty
                                # (always contains at least one entry, even if "manual")

    @property
    def tool(self) -> str:      # back-compat — first entry, never raises
        return self.tools[0]
```

Persisted form in `.coding-scaffold/project.json`:

```json
{
  "tools": ["codex", "claude-code"],
  "tool": "codex"
}
```

The singular `tool` key is duplicated into JSON so older code reading the file
(scripts, tests, external consumers) still works. New consumers should read
`tools`.

### 5.2 `routing.json`

```json
{
  "tools": ["codex", "claude-code"],
  "tool": "codex",
  "weak_model": "...",
  "strong_model": "...",
  ...
}
```

Same pattern: both keys present.

### 5.3 Interactive intake prompt

```
Coding tools to set up (comma-separated, e.g. `codex,claude-code`)
Default: opencode
> codex,claude-code
```

Validation matches the CLI normalizer — same `manual`-with-others rejection,
same comma split, same dedup.

## 6. Writers

### 6.1 `write_tool_adapter` (in `adapters.py`)

Signature widens to accept either a string or a list:

```python
def write_tool_adapter(target: Path, tool: str | list[str]) -> AdapterResult:
    tools = _normalize_tools(tool)   # same helper as CLI; called for safety
    for selected in tools:
        ... existing per-tool branches unchanged ...
```

The existing `tool == "both"` branch (`["opencode", "openclaude"]`) is removed
when `both` itself is removed in 0.7.0. In 0.6.0 it's untouched — the
deprecation happens in the CLI normalizer, so by the time the adapter writer
sees the list, `both` is already expanded.

### 6.2 `write_scaffold` (in `writers.py`)

The tool-agnostic file set is unchanged. The only edit is in `routing.json`
generation (and the `opencode.json` / `openclaude.json` / `hermes.json` /
`pi.json` config dumps, which already emit independently of which tool is
"primary").

### 6.3 `setup` orchestration (in `cli.py`)

```python
intake = collect_intake(args)                       # has intake.tools
adapter_result = write_tool_adapter(target, intake.tools)
write_scaffold(target, intake, hardware, providers, routing)
```

Adapter results aggregate across all tools — the printed
"Wrote N adapter file(s)" summary becomes "Wrote N adapter file(s) across
M tool(s): <comma-list>".

## 7. Pilot multi-tool output

### 7.1 Text output

```
CodingScaffold pilot — 10-minute happy path for /path/to/project

Tools: codex, claude-code
Environment OK: yes

Environment check:
  - Python: 3.11.9
  - OS: macOS
  - git on PATH: yes
  - codex (codex) installed: yes
  - claude-code (claude) installed: no
  - Credentials in env: ANTHROPIC_API_KEY
  - Local runtime CLI: ollama

Warnings:
  - `claude` is not on PATH. The setup step below offers --install-tools to add
    it; this pilot wrapper never installs anything itself.

Run these once (covers all selected tools):
  1. coding-scaffold setup run --target . --tool codex,claude-code --mode beginner --install-tools
  2. coding-scaffold pr-template init --target .

Then start a session with whichever tool you reach for today:
  codex   # inside the agent: /first-session, then /agentic-change
  claude  # inside the agent: /first-session, then /agentic-change

After the steps:
  - Review the diff before merging.
  - Run `coding-scaffold doctor` for the next thing to do.
```

Notes:

- `--install-tools` appears on step 1 iff at least one of the selected tools is
  not on PATH (existing logic, generalized).
- The agent step lists each tool's binary name (from `TOOL_BINARY_NAMES`) once.
- `environment_ok = all(tool_installed[t] for t in selected_tools) and python_ok and git_ok and has_creds_or_runtime`.

### 7.2 JSON output

```json
{
  "target": "/path",
  "tools": ["codex", "claude-code"],
  "tool": "codex",
  "persona": "beginner",
  "environment_ok": true,
  "environment": {
    "python": "3.11.9",
    "os": "macOS",
    "git": true,
    "tools": [
      {"name": "codex", "binary": "codex", "installed": true},
      {"name": "claude-code", "binary": "claude", "installed": false}
    ],
    "tool": {"name": "codex", "binary": "codex", "installed": true},
    "credentials_in_env": ["ANTHROPIC_API_KEY"],
    "local_runtime_cli": ["ollama"]
  },
  "steps": [...],
  "warnings": [...],
  "ignore_for_now": [...]
}
```

`environment.tool` is the back-compat (first-tool) entry. `environment.tools` is
the full per-tool list. Same shape used in `PilotReport.to_dict()`.

### 7.3 Single-tool pilot stays identical

When `--tool` receives a single value, the output is bit-for-bit the same as
today (`Tools:` line elided, no "Then start a session with whichever tool"
header, agent step inlined as `3.` like today's recipe). This preserves the
golden tests in `test_cli_ux.py` and `test_pilot.py`.

## 8. Deprecation of `both`

### 8.1 Release 0.6.0 — soft deprecation

- `both` remains a valid value in `CODING_TOOLS` and `INSTALLABLE_TOOLS`.
- The CLI normalizer expands it to `["opencode", "openclaude"]` and emits a
  one-line warning to stderr:

  ```
  warning: '--tool both' is deprecated; using '--tool opencode,openclaude' instead.
           Will be removed in 0.7.0. See https://jrs1986.github.io/CodingScaffold/wiki/Upgrading.
  ```

- The warning fires once per CLI invocation regardless of how many surfaces saw
  `both` (single-shot flag inside the normalizer).
- CHANGELOG `Deprecated` section names this and points at the upgrade path.

### 8.2 Release 0.7.0 — removal

- `both` removed from `CODING_TOOLS` and `INSTALLABLE_TOOLS`.
- Two enforcement paths:
  - CLI users hit argparse's standard "invalid choice" message at parse time
    (before the normalizer runs).
  - Programmatic callers (Python code still passing `"both"` to
    `write_tool_adapter` or `normalize_tools`) hit the normalizer's explicit
    check and get the three-line error:

    ```
    error: '--tool both' was removed in 0.7.0.
      next: use '--tool opencode,openclaude' instead.
      see: https://jrs1986.github.io/CodingScaffold/wiki/Upgrading
    ```

- CHANGELOG `Removed` section + Upgrading.md "Breaking changes in 0.7.0"
  block.

## 9. Tests

### 9.1 Updates to existing files

| File | Update |
|------|--------|
| `tests/test_intake.py` | `tools` list in `IntakeAnswers`; `tool` property returns first; round-trip through `to_dict`. |
| `tests/test_cli.py` | `--tool codex --tool claude-code` populates `args.tools`. `--tool both` triggers deprecation warning + expansion. `manual + real-tool` rejects via fail_with. |
| `tests/test_writers.py` | `routing.json` carries both `tools` and `tool`. Single-tool case unchanged. |
| `tests/test_adapters.py` | `write_tool_adapter(target, ["codex", "claude-code"])` writes both adapter sets. Backward: `write_tool_adapter(target, "codex")` still works. |
| `tests/test_pilot.py` | Single-tool output unchanged (golden). Multi-tool output has `Tools:` header, per-tool environment lines, shared setup step, per-tool agent steps. `environment_ok` is AND across tools. |
| `tests/test_cli_ux.py` | Pilot CLI accepts comma-separated `--tool`. |

### 9.2 New file

`tests/test_multi_tool.py` — end-to-end coverage:

- `setup run --tool codex --tool claude-code` writes both `AGENTS.md` and
  `CLAUDE.md` in one pass.
- `tools adapt --tool codex,claude-code` is idempotent on re-run (skipped count
  reflects both tools).
- `pilot --tool codex,claude-code --json` returns the expected multi-tool
  shape.
- `--tool both` produces the deprecation warning on stderr and the same files
  as `--tool opencode,openclaude`.
- `--tool manual,codex` exits non-zero with the three-line error.

## 10. Docs & CHANGELOG

- **CHANGELOG `[Unreleased]`:**
  - Added: multi-tool `--tool` support across setup / tools adapt / pilot.
  - Deprecated: `--tool both`; will be removed in 0.7.0.
- **Glossary entry:** "multi-tool project — a project with more than one
  coding tool configured. Generated via `setup run --tool <a> --tool <b>`."
- **Getting-Started.md:** add a "Two tools in one repo" subsection under
  "Smallest Useful Path" showing the canonical invocation and what's written.
- **Upgrading.md:** add a "0.7.0 Breaking" block (drafted now, lands when the
  removal lands) describing the `both` removal and replacement command.
- **Tool-Adapters.md:** mention multi-tool in the capability matrix preamble.

## 11. Open questions

None at design time. Confirmed in brainstorm:

- ✅ Pilot honors multi-tool (`--tool a,b` prints both).
- ✅ `both` deprecated in 0.6.0, removed in 0.7.0.
- ✅ `manual + real-tool` is invalid (rejected at parse time).
- ✅ Default behavior when `--tool` is omitted entirely is unchanged
  (`opencode`).

## 12. Estimated scope

| Area | Lines | Notes |
|------|-------|-------|
| `intake.py` | ~40 | list field + interactive prompt + validation |
| `cli.py` | ~50 | `action="append"` + shared normalizer + four surfaces |
| `writers.py` | ~10 | `routing.json` records `tools` and `tool` |
| `adapters.py` | ~20 | widen signature; preserve back-compat |
| `pilot.py` | ~80 | multi-tool recipe + per-tool env check + JSON shape |
| `tests/test_multi_tool.py` | ~120 | end-to-end coverage |
| existing test files | ~80 | updates per the table in §9.1 |
| docs (CHANGELOG + Glossary + Getting-Started + Upgrading + Tool-Adapters) | ~50 | small additions, no new wiki pages |

**Total ≈ 450 lines across one PR.** Single-day implementation expected.
