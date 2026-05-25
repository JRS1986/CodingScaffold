# First Agentic Coding Session

This walkthrough is designed to make the difference from autocomplete obvious.

## 1. Start With Context, Not Edits

```bash
opencode
```

Inside OpenCode:

```text
/first-session
```

Expected result: the agent identifies the project shape, run command, test command, key files,
risks, reusable knowledge candidates, and one safe improvement. It should not edit yet.

## 2. Run One Small Agentic Loop

```text
/agentic-change
```

Expected result:

- explorer maps the relevant files
- implementer makes a bounded change
- verification runs
- reviewer challenges the result
- you get changed files, checks, findings, and follow-up

## 3. Capture The Habit As A Skill

If the workflow helped, make it reusable:

```bash
coding-scaffold skill --target . --adapter opencode --name "Small Safe Improvement"
```

Skills are team leverage. They let peers reuse a good engineering habit without relying on memory or
a long prompt copied from chat history.
