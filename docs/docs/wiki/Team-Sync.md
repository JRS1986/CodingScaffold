# Team Sync

Team sync imports reviewed team defaults into a repository while keeping repo-local work reviewable.
See [Team Onboarding](./Team-Onboarding.md) for the first-run flow.

## Cascade Semantics

Manifests merge from parent to child. Plain scalar fields use child-overrides-parent semantics.
Remote lists such as `skills.remotes`, `agents.remotes`, and `configs.remotes` are unioned in
order. The following fields are tighten-only unless the parent explicitly marks them relaxable:

| Field | Tightening rule |
| --- | --- |
| `mcp.allowlist` | Child list must be a subset of the parent list. |
| `policy.allowed_providers` | Child list must be a subset of the parent list. |
| `policy.allowed_mcp_servers` | Child list must be a subset of the parent list. |
| `security.required_review_modes` | Child list must keep every parent-required review mode. |
| `tools.required_addons` | Child list must keep every parent-required add-on. |

Parents can opt a field out of tighten-only enforcement:

```json
{
  "inheritable": {
    "policy.allowed_providers": "relax"
  }
}
```

Nested form is also accepted:

```json
{
  "policy": {
    "inheritable": {
      "allowed_providers": "relax"
    }
  }
}
```

## Doctor JSON

`coding-scaffold team doctor --format json` prints the effective manifest, layers, per-field
provenance, recent stale pull failures, and inbound nomination records. The shape is:

```json
{
  "actions": [],
  "warnings": [],
  "manifest": {},
  "layers": [],
  "field_provenance": {
    "tools.default": {
      "layer": "frontend",
      "source": "local",
      "source_ref": "",
      "value": "opencode"
    }
  },
  "stale_pulls": [],
  "inbound_nominations": []
}
```

## Nominations

`team push` writes reviewable bundles under `.coding-scaffold/team/outbox/`. Pass `--open-pr` to
attempt a draft PR against a GitHub manifest repository; if GitHub, `gh`, auth, clone, push, or PR
creation is unavailable, the command keeps the outbox bundle and prints a clear warning.
