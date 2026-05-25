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

Every nomination bundle includes `inbound-nominations.json`. Manifest maintainers should keep this
file with the accepted note, skill, or policy entry so downstream teams can audit where inherited
knowledge came from. The file uses this schema:

```json
{
  "inbound_nominations": [
    {
      "slug": "api-runbook",
      "source_team": "platform",
      "source_scope": "team",
      "nominated_at": "2026-05-25T17:15:00Z",
      "accepted_at": "",
      "manifest_target": "https://github.com/acme/manifest.git",
      "manifest_ref": "",
      "rationale_ref": "nomination.md"
    }
  ]
}
```

When the manifest repo later syncs into a consuming project, `team sync` copies this metadata into
`.coding-scaffold/team-provenance.json`, and `team doctor` shows the inbound nomination.

## Stale Pull History

Failed remote updates are retained in `team-provenance.json` under `stale_pulls`. Records are keyed
by remote, include `first_seen` and `last_seen`, and are capped to the latest ten entries per remote
so successful syncs do not erase the audit trail.
