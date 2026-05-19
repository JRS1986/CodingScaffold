# Superpowers Wiki

The `/superpowers/` area tracks implementation-focused engineering work: concrete plans, design
decisions, and verification gates used to land non-trivial changes safely.

## What Superpowers Covers

Superpowers content is centered on execution artifacts, including:

- scoped implementation plans with ordered tasks
- design decisions tied to specific issue clusters
- explicit backward-compatibility notes
- test strategy and regression coverage per change set
- rollout order to reduce integration risk
- verification gates (`ruff`, `pytest`, and CI expectations)

This section is not product marketing, not high-level onboarding, and not a replacement for the
core docs in `/wiki/`.

## Current Focus

The active published workstream is **Code Review Batch 1** (dated 2026-05-18), which resolves four
design-bearing clusters:

- Cluster C: remove unsafe article-stripping from context compression (#32)
- Cluster A: treat Azure endpoint/deployment/model metadata as sensitive and redact serialized output (#31, #35)
- Cluster D: deep-merge `opencode.json` policy sections and stage `.new` updates (#39)
- Cluster B: harden team sync trust boundaries and clone/pull behavior (#30, #36, #43)

Execution order is intentionally **C -> A -> D -> B** to land the smallest/lowest-risk work first
and the `team.py` rewrite last on a known-good base.

## Recommended Reading

1. [Code Review Batch 1 - Design Decisions](./specs/2026-05-18-code-review-batch-1-design.md): rationale, mechanisms, tests, compatibility, and out-of-scope boundaries.
2. [Code Review Batch 1 - Implementation Plan](./plans/2026-05-18-code-review-batch-1.md): task-by-task execution checklist, file-level changes, and commit gates.

## Operating Posture

Superpowers work is intentionally strict:

- every meaningful behavior change gets a regression test
- risky writes use reviewable staging (`.new`) instead of silent overwrite
- trust boundaries are explicit for third-party/team-sourced content
- each cluster should be committable independently with green verification
- changes prioritize deterministic, local-first behavior over cleverness
