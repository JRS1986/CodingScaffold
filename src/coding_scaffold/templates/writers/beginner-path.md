# Beginner Path: Your First AI-Enabled Coding Project

This guide helps you complete one careful AI-assisted coding session without handing the whole
project to an agent at once.

## 1. Inspect The Project

Goal: understand what you have before asking an AI to change it.

```bash
coding-scaffold probe
```

Then ask your coding agent:

```text
Inspect this project and tell me the language, test command, run command, and risky areas. Do not edit yet.
```

## 2. Check Model And Privacy Defaults

Goal: use local models for routine work when possible.

Routine model: `${weak_model}`
Heavy-lift model: `${strong_model}`
Privacy mode: `${privacy}`

If an answer seems vague or overconfident, run a route recheck:

```text
Restate the task, list the exact files you inspected, and suggest the smallest next step.
```

## 3. Make One Small Change

Goal: complete a tiny, reviewable improvement.

Ask:

```text
Pick one small improvement in this project. Explain it first, then implement it, then run the narrowest test.
```

## 4. Pause Before Broad Changes

Goal: learn when to pause.

Pause before migrations, broad refactors, dependency upgrades, generated code rewrites, or anything
that changes public behavior. Make a checkpoint and ask for a plan before edits.

## 5. Keep The Habit

Goal: build a repeatable habit.

Small change. Fast test. Clear rollback. Short review.
