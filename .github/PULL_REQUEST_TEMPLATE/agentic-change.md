<!--
GitHub will offer this template via the "Choose a template" picker when opening a new PR. You
can also link to it directly:
  https://github.com/<owner>/<repo>/compare/main...feature-branch?template=agentic-change.md

Fill in every section. If a field doesn't apply, write "n/a" and a one-line reason instead of
leaving it blank.
-->

## Agentic coding disclosure

- **Agent / tool used:** <!-- e.g. Claude Code, Codex, OpenCode, Cursor, manual + Copilot completions -->
- **Model / provider:** <!-- e.g. anthropic/claude-opus-4-7, openai/gpt-5, local: qwen2.5-coder:7b -->
- **Human operator:** <!-- @your-handle -->
- **Task:** <!-- one-line description of what the change is supposed to do -->

## What changed

- **Files changed:** <!-- bullet list, or "see diff" if mechanical -->
- **Commands run:** <!-- exact commands you ran during the session, e.g. `uv run pytest`, `npm test`, `cargo build` -->
- **Tests run:** <!-- which tests, and the pass/fail result -->
- **Tests not run and why:** <!-- explicit list; "n/a" if everything ran -->

## Risk surface

- **External tools or MCP servers used:** <!-- list each by name, or "none" -->
- **Secrets / data exposure risk:** <!-- did the agent see .env, customer data, private logs? "none" is a valid answer -->
- **Network calls made during the session:** <!-- "none" if local-only -->

## Review focus

- **Human review focus:** <!-- 1-3 bullets telling the reviewer what to look at carefully -->
- **Known limitations:** <!-- anything the agent couldn't verify, or any "TODO" left for follow-up -->
- **Reusable knowledge captured:** <!-- if a skill, decision, or wiki page should be promoted from the session trace, link it -->

<!--
Reviewer checklist (suggested, not required to tick every box):

- [ ] The diff matches the stated task.
- [ ] Tests cover the change or the missing coverage is explicitly noted.
- [ ] No secrets or customer data in the diff or the agent's output.
- [ ] Policy (.coding-scaffold/policy/) was not silently relaxed.
- [ ] No new MCP servers added without an entry in the team review.
- [ ] If a session trace was generated (.coding-scaffold/sessions/), it's referenced above.
-->
