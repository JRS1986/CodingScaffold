# CodingScaffold

Local-first scaffolding for agentic coding teams.

CodingScaffold prepares an existing project for AI-assisted development without tying the team to
one model, one provider, or one coding agent. It creates project-local guidance for hardware fit,
provider credentials, model selection, coding-tool adapters, skills, agent orchestration, and shared
team knowledge.

GitHub Copilot is great at helping you type the next lines. Agentic coding can do more: inspect a
repo, build context, plan a change, edit bounded files, run verification, review the result, and
turn the best team workflows into reusable skills. This scaffold helps a team make that jump in a
controlled, reviewable way.

## Bootstrap Contract

CodingScaffold does not need an LLM to start. Guided setup, hardware probe, provider detection,
credential templates, adapter generation, and `tools select-model` recommendations are local Python
workflows. `tools select-model` reads the task text with a deterministic classifier and recommends a
route; it does not send the prompt to a model.

An LLM is needed only when a coding agent actually starts working, for example when OpenCode runs
`/first-session` or `/agentic-change`. At that point the selected tool must already have a usable
path to a model through Ollama, LM Studio, llama-server, GitHub Copilot, OpenAI, Anthropic, Azure,
OpenRouter, GitHub Models, or another compatible provider.

## Install

```bash
git clone https://github.com/JRS1986/CodingScaffold.git
cd CodingScaffold
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

For WSL/Linux the commands are the same. On Windows PowerShell outside WSL:

```powershell
.venv\Scripts\Activate.ps1
```

## First Run

Run guided setup inside a real project. It asks which coding environment you want to use, with
OpenCode as the default, OpenClaude as an option, and `manual` when you want to wire the tool
yourself.

```bash
coding-scaffold setup run --target ~/dev/my-project
cd ~/dev/my-project
```

Setup can run before any model is configured. It validates the selected coding tool and, when
stdin is interactive, asks before installing a missing tool. OpenCode uses the official install
script; OpenClaude uses the npm package. It can also configure the knowledge backend and optional
shared Git remote during setup. Nothing is installed silently.

If you already have `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, Azure variables, `GITHUB_TOKEN`, or a
local runtime installed, the scaffold will detect that. To keep credentials project-local, create an
ignored template and fill it on your machine:

```bash
coding-scaffold credentials --target . --format env
```

You can also validate or install the coding tool directly:

```bash
coding-scaffold setup tool --tool opencode
coding-scaffold setup tool --tool opencode --install
```

Optional add-ons use the same pattern:

```bash
coding-scaffold setup addon --target . --addon llmfit
coding-scaffold setup addon --target . --addon routellm
coding-scaffold setup addon --target . --addon open-multi-agent
coding-scaffold setup addon --target . --addon obsidian
coding-scaffold setup addon --target . --addon caveman-compression  # optional external compression engine
```

Shared knowledge can also be configured as part of setup:

```bash
coding-scaffold setup knowledge --target . \
  --backend obsidian \
  --shared-remote https://github.com/acme/team-ai-knowledge.git
```

When CodingScaffold improves later, refresh generated files without losing local edits:

```bash
coding-scaffold setup update --target .
```

Files that still match their generated checksum are updated in place. Files you edited are preserved
and the new generated version is staged next to them as `.new`.

If you join an experienced team, connect to its onboarding manifest instead. This pulls the common
knowledge base and exposes approved skills, agents, policy, and config locally:

```bash
coding-scaffold team connect --target . \
  --manifest https://github.com/acme/platform-ai-onboarding.git
coding-scaffold team sync --target .
coding-scaffold team doctor --target .
```

Then start the first session:

```bash
opencode
```

Inside OpenCode:

```text
/first-session
```

That command asks the agent to inspect before editing, identify run and test commands, map the main
code paths, and propose one safe improvement. This is the first step that requires OpenCode to be
connected to a working model. Then run a small agentic loop:

```text
/agentic-change
```

This is the difference from autocomplete: the tool is not just suggesting code, it is running a
small engineering workflow that you can inspect, verify, and improve.

## Everyday Flow

1. Probe the machine and provider setup:

   ```bash
   coding-scaffold probe --target ~/dev/my-project
   ```

2. Configure local-only credentials if needed:

   ```bash
   coding-scaffold credentials --target ~/dev/my-project --format env
   ```

3. Generate native OpenCode files:

   ```bash
   coding-scaffold tools adapt --target ~/dev/my-project --tool opencode
   ```

4. Ask for a model recommendation when the route is unclear:

   ```bash
   coding-scaffold tools select-model --target ~/dev/my-project \
     --prompt "Review this authentication refactor for security regressions."
   ```

5. Capture repeatable workflows as skills:

   ```bash
   coding-scaffold skill --target ~/dev/my-project \
     --adapter opencode \
     --name "Release Review"
   ```

6. Capture decisions, useful prompts, skills, and agent patterns in team memory:

   ```bash
   coding-scaffold setup knowledge --target ~/dev/my-project \
     --backend obsidian \
     --shared-remote https://github.com/acme/team-ai-knowledge.git
   ```

7. Connect to team onboarding when a shared manifest exists:

   ```bash
   coding-scaffold team connect --target ~/dev/my-project \
     --manifest https://github.com/acme/platform-ai-onboarding.git
   ```

8. Apply local policy defaults when your team has provider, sharing, or MCP rules:

   ```bash
   coding-scaffold policy --target ~/dev/my-project \
     --scope company \
     --enable-provider ollama \
     --disable-provider openai \
     --disable-mcp-server jira
   ```

9. Add advanced routing or workflow automation only when the team has a real need:

   ```bash
   coding-scaffold tools route --target ~/dev/my-project --backend routellm
   coding-scaffold tools workflow --target ~/dev/my-project --backend open-multi-agent
   ```

## Core Concepts

**Local-first routing:** The scaffold prefers local models when possible and only uses cloud
providers when credentials or authenticated CLIs are available. Provider and model family are kept
separate, so Azure can be the endpoint while the deployed model family is OpenAI, Anthropic, or
something else.

**Model selection:** `tools select-model` reads a prompt and recommends `routine` or `heavy-lift`. It
does not call a model; it explains the route, provider, model family, model or deployment,
confidence, and reasons.

**Skills:** Skills are reusable playbooks for work the team repeats: release reviews, dependency
upgrades, frontend QA, API contract changes, incident analysis, migration checks, and project
specific workflows.

**Agent orchestration:** The scaffold supports `solo`, `pair`, and `team` profiles. By default it
generates OpenCode-native agents and commands instead of inventing a parallel runtime.

**Team knowledge:** Decisions, project vocabulary, useful prompts, trusted agents, and validated
skills belong in reviewed Markdown, not in one person’s chat history. Knowledge can use scope
(`team`, `department`, `unit`, `company`) and maturity (`draft`, `validated`, `recommended`,
`standard`) frontmatter; `knowledge status` reports what exists and flags missing metadata.

**Team onboarding:** Experienced teams can publish a non-secret onboarding manifest that points to
shared knowledge, approved skills, approved agents, policy, config, default tool choices, and
required add-ons. New joiners run `coding-scaffold team connect` and get the team setup copied into
the project with provenance.

**Policy packs:** Company, unit, department, or team defaults can be generated as reviewable local
policy. For OpenCode this can disable conversation sharing, keep project MCP empty by default,
disable named MCP servers, constrain provider ids, and ask before edit/bash actions.

## Coding Tool Adapters

OpenCode is the recommended default for most teams today. It has official install paths,
terminal/desktop/IDE surfaces, LSP awareness, multi-session workflows, broad provider support,
local-model support, and GitHub Copilot sign-in.

```bash
coding-scaffold setup tool --tool opencode
coding-scaffold tools adapt --target ~/dev/my-project --tool opencode
```

OpenClaude is worth tracking if your team wants a fast-moving, Claude-Code-like community workflow
across OpenAI-compatible APIs, Ollama, GitHub Models, MCP, slash commands, and provider profiles.
Treat it as experimental and review provenance, licensing, and security before standardizing on it.

```bash
coding-scaffold setup tool --tool openclaude
coding-scaffold tools adapt --target ~/dev/my-project --tool openclaude
```

## Knowledge Base

The knowledge base is Markdown-first so it works in GitHub, GitLab, local editors, OpenCode,
Obsidian, and optional memory tools.

Plain Markdown:

```bash
coding-scaffold knowledge create --target ~/dev/my-project
```

Shared GitHub or GitLab memory:

```bash
coding-scaffold knowledge create --target ~/dev/my-project \
  --shared-remote https://github.com/acme/team-ai-knowledge.git
```

Obsidian vault mode:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon obsidian
coding-scaffold knowledge create --target ~/dev/my-project --backend obsidian
```

This creates Obsidian-friendly folders, backlinks, frontmatter templates, and `.obsidian/` settings
while keeping Markdown as the source of truth.

Optional MemPalace index:

```bash
coding-scaffold knowledge create --target ~/dev/my-project --backend mempalace
```

Use Obsidian when humans want better navigation and graph-style reading. Use MemPalace when the
Markdown corpus grows large enough to benefit from semantic retrieval or MCP memory workflows.

Hierarchical sharing is an optional organization pattern. Start with one repo and folder scopes when
everyone has the same access. Use multiple Git remotes only when company, unit, department, or team
knowledge needs different permissions. Promote mature notes upward by pull request instead of
automatic sync, and use `coding-scaffold knowledge status --target .` to check scope/maturity
metadata.

## Context Hygiene

Long context is powerful, but it is not free. Agents can miss important facts in the middle of a
large prompt, stale notes can steer a session, and compressed summaries can accidentally hide the
detail a change needs. CodingScaffold treats context as something to budget and curate, not
something to shovel into a model until the meter turns red.

Check the project knowledge budget:

```bash
coding-scaffold context budget --target ~/dev/my-project --source knowledge
```

The default guardrail warns above 100,000 estimated tokens or 40% of the configured context window.
Those thresholds are intentionally conservative. They tell the developer to narrow retrieval,
compress supporting notes, or start a fresh session before old context starts bending the task.

Create compressed sidecars for Markdown knowledge:

```bash
coding-scaffold context compress --target ~/dev/my-project --source knowledge
```

This writes `.caveman.md` sidecars next to the original files. Originals stay the reviewed source
of truth; sidecars are optional agent input. Use compression for reference notes, session logs, and
large knowledge articles. Keep policies, security rules, requirements, and active code uncompressed
unless a human explicitly reviews the compressed version. For that reason,
`context compress --source team` skips `.coding-scaffold/policy` by default.

The default compressor is built in and works offline. If you want to experiment with the upstream
Caveman Compression project, install it as an optional engine and call it explicitly:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon caveman-compression
coding-scaffold context compress --target ~/dev/my-project --source knowledge --engine caveman
```

After compression, `context budget` still estimates original files by default so budgets do not
double-count source notes and sidecars. Use `--prefer compressed` to estimate a sidecar-first agent
session, or `--prefer both` when you intentionally want to measure the full stored corpus.

## Policy Packs

Policy packs let teams carry local AI-coding defaults into generated tool config:

```bash
coding-scaffold policy --target ~/dev/my-project --scope company
```

This writes `.coding-scaffold/policy/` and, for OpenCode, updates `opencode.json` with conservative
defaults:

- `share: disabled`
- policy instructions loaded from `.coding-scaffold/policy/*.md`
- edit/bash permissions set to `ask`
- optional provider allow/deny lists
- optional named MCP server disable entries

The generated config is not a security boundary by itself. Treat it as project-local guardrails and
combine it with reviewed credentials, CI checks, identity policy, and network controls.

## Advanced Options

RouteLLM can provide one OpenAI-compatible endpoint that routes actual requests between a
weak/routine model and a strong/heavy-lift model:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon routellm
coding-scaffold tools route --target ~/dev/my-project --backend routellm
```

Open Multi-Agent can turn a validated human-in-the-loop workflow into repeatable TypeScript
automation:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon open-multi-agent
coding-scaffold tools workflow --target ~/dev/my-project --backend open-multi-agent
```

The intended path is: validate interactively in OpenCode, capture the useful behavior as a skill,
then graduate it into workflow automation only after the team trusts the process.

Caveman Compression is an experimental optional engine for token-constrained contexts. The built-in
compressor does not require it; install the add-on only when you want to compare the upstream
compressor against the scaffold default:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon caveman-compression
coding-scaffold context budget --target ~/dev/my-project --source team
coding-scaffold context compress --target ~/dev/my-project --source knowledge --engine caveman
```

Use it when the knowledge base is useful but too wordy for repeated agent sessions. Avoid using it
as a substitute for better retrieval, smaller task boundaries, or fresh sessions.

## What It Creates

`coding-scaffold setup run` writes `.coding-scaffold/` in the target project:

- `.gitignore`: keeps generated local credential files out of Git.
- `.env.example` and `credentials.example.json`: local credential templates.
- `CREDENTIALS.md`: local credential setup guide.
- `providers.json`: detected local and cloud providers without secret values.
- `hardware.json`: CPU, RAM, OS, WSL status, GPU/VRAM, and llmfit availability.
- `routing.json`: selected local-first routing policy.
- `model-selection.json` and `MODEL_SELECTION.md`: routine/heavy-lift model guidance.
- `TOOLS.md`: OpenCode/OpenClaude adapter guidance.
- `ORCHESTRATION.md` and `orchestration.json`: agent-role guidance.
- `skills/README.md` and `SKILLS.md`: project skill guidance.
- `KNOWLEDGE.md`, `knowledge.json`, and `knowledge/`: optional team memory.
- `.coding-scaffold/policy/`: optional company/unit/department/team policy packs.
- `.coding-scaffold/team-onboarding.json` and `team-provenance.json`: optional experienced-team onboarding.
- `GETTING_STARTED.md` and `FIRST_SESSION.md`: first-use walkthroughs.
- `AGENTS.md`: project-specific operating notes for coding agents.
- `scaffold-version.json`: checksums that let `coding-scaffold setup update` refresh generated files safely.

Optional commands can also generate:

- `opencode.json`, `.opencode/agents/`, and `.opencode/commands/`.
- `.coding-scaffold/ROUTELLM.md` and `routellm.config.yaml`.
- `.coding-scaffold/OPEN_MULTI_AGENT.md`, `open-multi-agent.team.json`, and a TypeScript example.
- Obsidian vault files under `.coding-scaffold/knowledge/.obsidian/`.
- `.coding-scaffold/tools/caveman-compression/` and `.caveman.md` context sidecars.

## Commands

```bash
coding-scaffold probe --json
coding-scaffold setup run --target ~/dev/my-project
coding-scaffold credentials --target ~/dev/my-project --format env
coding-scaffold setup tool --tool opencode
coding-scaffold setup addon --target ~/dev/my-project --addon llmfit
coding-scaffold setup addon --target ~/dev/my-project --addon routellm
coding-scaffold setup addon --target ~/dev/my-project --addon open-multi-agent
coding-scaffold setup addon --target ~/dev/my-project --addon obsidian
coding-scaffold setup addon --target ~/dev/my-project --addon caveman-compression
coding-scaffold setup knowledge --target ~/dev/my-project --backend obsidian
coding-scaffold setup update --target ~/dev/my-project
coding-scaffold knowledge status --target ~/dev/my-project
coding-scaffold context budget --target ~/dev/my-project --source knowledge
coding-scaffold context budget --target ~/dev/my-project --source knowledge --prefer compressed
coding-scaffold context compress --target ~/dev/my-project --source knowledge
coding-scaffold context compress --target ~/dev/my-project --source knowledge --engine caveman
coding-scaffold team init --target ~/dev/my-project --team platform-api
coding-scaffold team connect --target ~/dev/my-project --manifest https://github.com/acme/platform-ai-onboarding.git
coding-scaffold team sync --target ~/dev/my-project
coding-scaffold team doctor --target ~/dev/my-project
coding-scaffold tools select-model --target ~/dev/my-project --prompt "Review this migration"
coding-scaffold tools adapt --target ~/dev/my-project --tool opencode
coding-scaffold skill --target ~/dev/my-project --adapter opencode --name "Release Review"
coding-scaffold knowledge create --target ~/dev/my-project --backend obsidian
coding-scaffold tools orchestrate --target ~/dev/my-project --profile pair
coding-scaffold policy --target ~/dev/my-project --scope company
coding-scaffold tools route --target ~/dev/my-project --backend routellm
coding-scaffold tools workflow --target ~/dev/my-project --backend open-multi-agent
coding-scaffold doctor
```

## Design Goals

- Cross-platform Linux and WSL behavior.
- No secret collection; the scaffold only records whether credentials appear available.
- Local-first routing with explicit cloud escalation.
- Open-source toolchain with no vendor lock-in.
- Generated config that is transparent and easy to edit by hand.
- Team knowledge, skills, and agents that can be reviewed like code.

## License

CodingScaffold is licensed under the Apache License 2.0.
