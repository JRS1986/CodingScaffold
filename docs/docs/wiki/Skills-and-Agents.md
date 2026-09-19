# Skills and Agents

Skills and agents are the team acceleration layer. They turn one good workflow into something peers
can reuse and improve.

## Create A Skill

```bash
coding-scaffold skill --target ~/dev/my-project \
  --adapter opencode \
  --name "Release Review" \
  --description "Review a release candidate before tagging."
```

This creates:

- `.coding-scaffold/skills/release-review.md`
- `.opencode/commands/release-review.md`

## What A Good Skill Contains

For a native Agent Skills package, use the plural `skills` commands:

```bash
coding-scaffold skills new release-review --location agents --owner @platform
coding-scaffold skills lint --target .
coding-scaffold skills approve release-review --location agents
coding-scaffold skills export release-review --location agents --output release-review.tar.gz
```

Locations are `scaffold` (the existing default, `.coding-scaffold/skills`), `agents`
(`.agents/skills`), `claude` (`.claude/skills`) and `opencode` (`.opencode/skills`).
`skills lint` inspects all four project-local folders, without reading user-global
skills. Native findings include their relative folder path, so duplicate names
remain distinguishable. In-project directory aliases are scanned once.

Generated packages include `name` and `description` frontmatter. The offline
validator accepts plain/quoted strings and indented folded/literal blocks for
these fields; it does not implement a general YAML parser. Names must match their
folder and use lowercase letters/digits separated by hyphens. Native packages do
not require the scaffold-specific manifest or section headings. If a native
package includes a manifest, it is validated. All skills are checked for broad
triggers and hidden instructions.

New approvals cover the complete package, including file paths, contents,
executable bits and supporting instructions. Old approvals produce a migration
warning until reviewed and approved again. External directory links and links or
special files within a package are rejected; copy their contents into regular
project files before approval or export. A checksum is a local drift marker, not
a signature or execution permission. See [Upgrading](Upgrading.md#skill-approval-migration).

The singular `skill` command above retains its legacy Markdown/slash-command
behavior; it does not create a native Agent Skills package.

A good skill is short and procedural:

- when to use it
- what context to inspect
- what not to touch
- the step-by-step workflow
- verification expectations
- escalation rules

## Agent Profiles

Generate an orchestration plan:

```bash
coding-scaffold tools orchestrate --target ~/dev/my-project --profile pair
```

Profiles:

- `solo`: one agent with explicit checkpoints
- `pair`: builder plus reviewer
- `team`: explorer, planner, implementer, verifier

## Review Skills Like Code

Skills should be reviewed when they:

- add broad write permissions
- change model routing assumptions
- introduce new verification behavior
- become team defaults
- encode project-specific architecture rules

The best skills are not clever prompts. They are reliable engineering habits.
