# Code Review Batch 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the four design-bearing issue clusters from the batch-1 code review (#30, #31, #32, #35, #36, #39, #43) on top of the already-merged mechanical fixes.

**Architecture:** Each cluster is an independent commit on `integration/review-batch-1`. Land in order C → A → D → B so the smallest, lowest-risk change goes first and the largest (`team.py` rewrite) lands on a known-good base.

**Tech Stack:** Python 3.11+, stdlib only. Tests via `pytest`. Lint via `ruff`. Run gates `uv run ruff check` and `uv run pytest` clean after each task.

**Spec reference:** [`docs/superpowers/specs/2026-05-18-code-review-batch-1-design.md`](../specs/2026-05-18-code-review-batch-1-design.md)

**Branch:** `integration/review-batch-1` (already exists; mechanical fixes from the prior batch are already merged in).

---

## Task 1 — Cluster C: Drop article-stripping heuristic

**Closes #32.**

**Files:**
- Modify: `src/coding_scaffold/context.py:270`
- Modify: `tests/test_context.py` (add regression test)

- [ ] **Step 1: Write the failing regression test**

Add to `tests/test_context.py`:

```python
def test_compress_preserves_inline_code_identifiers(tmp_path):
    from coding_scaffold.context import compress_context

    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    note = knowledge / "note.md"
    note.write_text(
        "Use `the-prod-route` to deploy.\n"
        "See [the docs](./the-docs) for details.\n",
        encoding="utf-8",
    )

    result = compress_context(tmp_path, source="knowledge")

    assert not result.warnings, result.warnings
    compressed = (knowledge / "note.caveman.md").read_text(encoding="utf-8")
    assert "`the-prod-route`" in compressed, compressed
    assert "[the docs](./the-docs)" in compressed, compressed
```

- [ ] **Step 2: Run test to verify it fails**

```
uv run pytest tests/test_context.py::test_compress_preserves_inline_code_identifiers -v
```

Expected: FAIL. The `the` and `the-` get mangled by the article-stripping regex.

- [ ] **Step 3: Delete the article-stripping line**

In `src/coding_scaffold/context.py:270`, delete the entire line:

```python
    body = re.sub(r"\b(the|a|an)\b", "", body, flags=re.I)
```

Adjacent lines (filler-word substitution, whitespace collapse) stay.

- [ ] **Step 4: Run full test suite to verify**

```
uv run ruff check
uv run pytest
```

Both must pass. New test passes; all existing tests still green.

- [ ] **Step 5: Commit**

```
git add src/coding_scaffold/context.py tests/test_context.py
git commit -m "Drop article-stripping from context compression

The 'the|a|an' substitution corrupted identifiers inside backtick spans
and link targets. Token savings were minor; correctness for agent-facing
knowledge wins.

Closes #32"
```

---

## Task 2 — Cluster A: Provider redact_fields infrastructure

**Closes #31 and #35.**

**Files:**
- Modify: `src/coding_scaffold/credentials.py` (split SECRET_ENV_NAMES)
- Modify: `src/coding_scaffold/providers.py` (add `redact_fields`, redact in `to_dict`, tag Azure providers)
- Modify: `tests/test_providers.py` (assert redaction)
- Modify: `tests/test_credentials.py` (assert split + template content)

- [ ] **Step 1: Split SECRET_ENV_NAMES in credentials.py**

Replace the `SECRET_ENV_NAMES` block at the top of `src/coding_scaffold/credentials.py` with:

```python
SECRET_KEY_ENV_NAMES = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_AI_API_KEY",
    "AZURE_AI_SERVICES_KEY",
    "AZURE_COGNITIVE_SERVICES_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
)

AZURE_NONKEY_ENV_NAMES = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_AI_ENDPOINT",
    "AZURE_AI_MODEL",
    "AZURE_AI_MODEL_FAMILY",
    "AZURE_AI_SERVICES_ENDPOINT",
    "AZURE_COGNITIVE_SERVICES_ENDPOINT",
)

# Union: everything that belongs in .env.local rather than committed config.
# Azure endpoints/deployments are treated as sensitive because the subdomain
# typically encodes tenant identity.
SECRET_ENV_NAMES = SECRET_KEY_ENV_NAMES + AZURE_NONKEY_ENV_NAMES
```

The `SECRET_ENV_NAMES` name is preserved so existing callers in `write_local_credential_file` don't break.

- [ ] **Step 2: Write the failing test for credentials split**

Add to `tests/test_credentials.py`:

```python
def test_secret_env_names_separates_keys_from_azure_config():
    from coding_scaffold.credentials import (
        AZURE_NONKEY_ENV_NAMES,
        SECRET_ENV_NAMES,
        SECRET_KEY_ENV_NAMES,
    )

    assert "OPENAI_API_KEY" in SECRET_KEY_ENV_NAMES
    assert "AZURE_OPENAI_ENDPOINT" in AZURE_NONKEY_ENV_NAMES
    assert "AZURE_OPENAI_ENDPOINT" not in SECRET_KEY_ENV_NAMES
    # Backwards-compat: the union is still importable under the old name.
    assert set(SECRET_KEY_ENV_NAMES) <= set(SECRET_ENV_NAMES)
    assert set(AZURE_NONKEY_ENV_NAMES) <= set(SECRET_ENV_NAMES)
```

- [ ] **Step 3: Add `redact_fields` to Provider dataclass**

In `src/coding_scaffold/providers.py`, change the `Provider` dataclass to:

```python
REDACTED_PLACEHOLDER = "<configured locally; see .env.local>"


@dataclass(frozen=True)
class Provider:
    name: str
    kind: str
    available: bool
    status: str
    endpoint: str | None = None
    model_family: str | None = None
    deployment: str | None = None
    redact_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for field in self.redact_fields:
            if data.get(field):
                data[field] = REDACTED_PLACEHOLDER
        data.pop("redact_fields", None)
        return data
```

- [ ] **Step 4: Tag Azure providers**

In `src/coding_scaffold/providers.py`, update both Azure constructors to set `redact_fields`:

`_azure_openai_provider` — return:

```python
return Provider(
    "azure-openai",
    "cloud",
    available,
    status,
    endpoint=endpoint,
    model_family="openai",
    deployment=deployment,
    redact_fields=("endpoint", "deployment"),
)
```

`_azure_ai_provider` — same pattern, set `redact_fields=("endpoint", "deployment", "model_family")` (model_family for Azure AI can come from `AZURE_AI_MODEL_FAMILY` which is in the redact list).

- [ ] **Step 5: Write the failing test for redaction**

Add to `tests/test_providers.py`:

```python
def test_azure_openai_provider_redacts_endpoint_and_deployment():
    from coding_scaffold.providers import REDACTED_PLACEHOLDER, detect_providers

    env = {
        "AZURE_OPENAI_API_KEY": "key-xyz",
        "AZURE_OPENAI_ENDPOINT": "https://contoso-prod.openai.azure.com/",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4-internal",
    }
    providers = detect_providers(env=env)
    azure = next(p for p in providers if p.name == "azure-openai")

    # In-memory values stay intact for routing.
    assert azure.endpoint == "https://contoso-prod.openai.azure.com/"
    assert azure.deployment == "gpt-4-internal"

    # Serialized form redacts.
    serialized = azure.to_dict()
    assert serialized["endpoint"] == REDACTED_PLACEHOLDER
    assert serialized["deployment"] == REDACTED_PLACEHOLDER
    assert "redact_fields" not in serialized
    # Non-redacted providers serialize unchanged.
    openai = next(p for p in providers if p.name == "openai")
    assert "redact_fields" not in openai.to_dict()
```

- [ ] **Step 6: Add CREDENTIALS.md guidance + writers.py regression assertion**

Find the CREDENTIALS.md generator (search: `grep -rn "CREDENTIALS\|credentials.md" src/coding_scaffold/writers.py`). Append a paragraph near the Azure-related section:

```
Azure endpoint and deployment values are treated as sensitive. The
generated `providers.json` and adapter configs contain a placeholder; the
real values live only in `.env.local` and are resolved at agent start.
```

In `tests/test_writers.py`, add a regression test:

```python
def test_providers_json_redacts_azure_endpoint(tmp_path, monkeypatch):
    from coding_scaffold.providers import detect_providers
    from coding_scaffold.writers import write_scaffold

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://contoso.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "internal-gpt")

    # Use whatever the existing write_scaffold signature requires; mirror an
    # existing test in test_writers.py.
    write_scaffold(tmp_path, providers=detect_providers())

    providers_json = (tmp_path / ".coding-scaffold" / "providers.json").read_text(encoding="utf-8")
    assert "contoso.openai.azure.com" not in providers_json
    assert "internal-gpt" not in providers_json
```

If `write_scaffold`'s signature is different, mirror the call shape used by the nearest existing test in that file.

- [ ] **Step 7: Run tests**

```
uv run ruff check
uv run pytest
```

All must pass.

- [ ] **Step 8: Commit**

```
git add src/coding_scaffold/credentials.py src/coding_scaffold/providers.py \
        src/coding_scaffold/writers.py \
        tests/test_providers.py tests/test_credentials.py tests/test_writers.py
git commit -m "Treat Azure endpoint/deployment as secret in serialized config

Provider gains a redact_fields tag; Azure constructors set it so to_dict()
emits a placeholder instead of the tenant-identifying URL/deployment.
In-memory values still drive routing.

Closes #31
Closes #35"
```

---

## Task 3 — Cluster D: Deep merge + .new staging for policy

**Closes #39.**

**Files:**
- Modify: `src/coding_scaffold/file_ops.py` (add `deep_merge_mapping`)
- Modify: `src/coding_scaffold/policy.py` (use deep_merge_mapping, stage `.new`)
- Modify: `tests/test_policy.py` (assert preservation + staging)

- [ ] **Step 1: Add deep_merge_mapping helper**

Append to `src/coding_scaffold/file_ops.py`:

```python
def deep_merge_mapping(
    base: dict[str, object],
    overlay: dict[str, object],
    deep_keys: tuple[str, ...] = (),
) -> dict[str, object]:
    """Merge ``overlay`` into ``base``. For top-level keys in ``deep_keys``,
    if both sides are mappings the merge recurses one level; otherwise overlay
    wins. Non-listed keys use shallow overlay-wins.
    """
    result: dict[str, object] = dict(base)
    for key, value in overlay.items():
        if (
            key in deep_keys
            and isinstance(value, dict)
            and isinstance(result.get(key), dict)
        ):
            result[key] = {**result[key], **value}  # type: ignore[dict-item]
        else:
            result[key] = value
    return result
```

- [ ] **Step 2: Write the failing test for deep merge**

Add to `tests/test_policy.py`:

```python
def test_policy_preserves_user_mcp_servers(tmp_path):
    import json
    from coding_scaffold.policy import write_policy_pack

    target = tmp_path
    (target / ".coding-scaffold").mkdir()
    opencode = target / "opencode.json"
    opencode.write_text(json.dumps({
        "mcp": {
            "user-defined-server": {"command": "user-server", "enabled": True},
        },
    }), encoding="utf-8")

    write_policy_pack(target, scope="team", disabled_mcp_servers=["bad-server"])

    new_file = target / "opencode.json.new"
    assert new_file.exists(), "policy must stage opencode.json.new when opencode.json exists"
    # Original untouched.
    original = json.loads(opencode.read_text(encoding="utf-8"))
    assert original == {"mcp": {"user-defined-server": {"command": "user-server", "enabled": True}}}
    # Staged file deep-merges: user's server survives alongside the disabled one.
    staged = json.loads(new_file.read_text(encoding="utf-8"))
    assert staged["mcp"]["user-defined-server"] == {"command": "user-server", "enabled": True}
    assert staged["mcp"]["bad-server"] == {"enabled": False}
```

If the `write_policy_pack` signature differs, adjust the kwargs but keep the assertions.

- [ ] **Step 3: Rewrite `_merge_opencode_config` to stage `.new` and deep-merge**

In `src/coding_scaffold/policy.py`, replace the existing `_merge_opencode_config` body:

```python
def _merge_opencode_config(path: Path, policy: dict[str, object]) -> tuple[Path, str | None]:
    from .file_ops import deep_merge_mapping

    current: dict[str, object] = {}
    warning = None
    target_path = path
    file_existed = path.exists()
    if file_existed:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            warning = f"Could not parse {path}; wrote policy overlay to {path}.new instead."
            target_path = path.with_suffix(path.suffix + ".new")
            target_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return target_path, warning
        if isinstance(loaded, dict):
            current = loaded

    merged = deep_merge_mapping(current, policy, deep_keys=("mcp", "permission"))
    if "instructions" in current or "instructions" in policy:
        merged["instructions"] = _merge_list(current.get("instructions"), policy.get("instructions"))

    if file_existed:
        target_path = path.with_suffix(path.suffix + ".new")
        warning = (
            f"Staged {target_path.name}; review and `mv {target_path.name} {path.name}` to apply."
        )
    target_path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path, warning
```

Drop the now-unused `_merge_mapping` if no other call site uses it (grep first; keep if used).

- [ ] **Step 4: Run tests**

```
uv run ruff check
uv run pytest
```

Existing policy tests may break if they assert that `opencode.json` is rewritten in place. Update those tests to look at `opencode.json.new` when an existing file is present; the no-existing-file path still writes `opencode.json` directly.

- [ ] **Step 5: Commit**

```
git add src/coding_scaffold/file_ops.py src/coding_scaffold/policy.py tests/test_policy.py
git commit -m "Stage opencode.json.new and deep-merge nested keys on policy

When opencode.json already exists, the policy pack now writes the merged
result to opencode.json.new so the user reviews and applies the change
explicitly. mcp.<server> and permission.<scope> entries from the user are
preserved by deep-merging those top-level keys.

Closes #39"
```

---

## Task 4 — Cluster B: Team sync layered + safe

**Closes #30, #36, #43.**

This is the largest task. Split into four steps that each leave the suite green.

**Files:**
- Modify: `src/coding_scaffold/team.py` (layout + clone strategy + scheme validation)
- Modify: `src/coding_scaffold/cli.py` (add `--allow-local` flag to `team connect`/`team sync`)
- Modify: `tests/test_team.py` (regressions + new safety assertions; existing tests get `--allow-local` where needed)
- Modify: `docs/wiki/Team-Onboarding.md` (trust-model paragraph)

- [ ] **Step 1: Write the four new failing regression tests**

Add to `tests/test_team.py`:

```python
def test_team_sync_never_touches_knowledge_dir(tmp_path):
    """User-owned .coding-scaffold/knowledge/ files survive team sync."""
    import json
    from coding_scaffold.team import sync_team

    knowledge = tmp_path / ".coding-scaffold" / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "secret-note.md").write_text("private", encoding="utf-8")

    # Manifest with a benign local-path remote (allow_local enabled).
    remote = tmp_path / "team-remote"
    remote.mkdir()
    (remote / "shared.md").write_text("shared", encoding="utf-8")
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.write_text(json.dumps({
        "team": "t",
        "knowledge": {"backend": "markdown", "path": ".coding-scaffold/knowledge", "remote": str(remote)},
    }), encoding="utf-8")

    sync_team(tmp_path, allow_local=True)

    assert (knowledge / "secret-note.md").exists()
    assert (knowledge / "secret-note.md").read_text(encoding="utf-8") == "private"


def test_team_sync_rejects_local_remote_without_allow_local(tmp_path):
    import json
    from coding_scaffold.team import sync_team

    remote = tmp_path / "team-remote"
    remote.mkdir()
    manifest = tmp_path / ".coding-scaffold" / "team-onboarding.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "team": "t",
        "knowledge": {"backend": "markdown", "path": ".coding-scaffold/knowledge", "remote": str(remote)},
    }), encoding="utf-8")

    result = sync_team(tmp_path)
    assert any("allow-local" in w.lower() or "local path" in w.lower() for w in result.warnings)


def test_team_sync_keeps_git_directory_inside_repo_subdir(tmp_path, monkeypatch):
    """Cloned repo retains .git inside _repo so subsequent syncs can ff-pull."""
    # Will require monkeypatching subprocess.run for git clone/pull and
    # asserting that team/sources/<kind>/<slug>/_repo/.git is created.
    # Detailed implementation deferred to the agent — keep this stub and
    # implement once the team.py rewrite lands so the helpers exist.
    pytest.skip("Implement after team.py rewrite — see plan task 4 step 3.")


def test_team_sync_strips_nested_git_dirs_from_agent_path(tmp_path):
    """Submodule .git directories don't leak into the agent-readable copy."""
    pytest.skip("Implement after team.py rewrite — see plan task 4 step 3.")
```

Import `pytest` at the top of `test_team.py` if not already there.

- [ ] **Step 2: Run failing tests**

```
uv run pytest tests/test_team.py::test_team_sync_never_touches_knowledge_dir \
              tests/test_team.py::test_team_sync_rejects_local_remote_without_allow_local -v
```

Both must FAIL (the protection doesn't exist yet).

- [ ] **Step 3: Rewrite team.py sync internals**

Replace `_sync_team_payload`, `_resolve_knowledge_destination` (introduce if missing), `_sync_source`, `_clone_or_pull`, and `_remove_nested_git` with the layered design:

```python
ALLOWED_REMOTE_SCHEMES = ("https", "http", "ssh")
SOURCES_SUBDIR = Path(".coding-scaffold") / "team" / "sources"
KNOWLEDGE_FORBIDDEN_PREFIX = Path(".coding-scaffold") / "knowledge"


def _classify_remote(remote: str) -> str:
    """Return 'url', 'local', or raise ValueError for empty/unknown."""
    if not remote:
        raise ValueError("Remote is empty.")
    if "://" in remote:
        scheme = remote.split("://", 1)[0].lower()
        if scheme in ALLOWED_REMOTE_SCHEMES:
            return "url"
        if scheme == "file":
            return "local"
        raise ValueError(f"Unsupported remote scheme: {scheme}")
    if remote.startswith("git@"):
        return "url"
    return "local"  # bare path


def _team_destination(root: Path, kind: str, remote: str) -> Path:
    """Compute the team-sources destination for a (kind, remote) pair.
    Always lives under SOURCES_SUBDIR — never under knowledge/."""
    slug = _slug(remote)
    return root / SOURCES_SUBDIR / kind / slug


def _sync_source(
    remote: str,
    destination: Path,
    *,
    dry_run: bool,
    allow_local: bool,
) -> tuple[str, str | None]:
    """Copy or clone `remote` into `destination`. Never touches paths outside
    SOURCES_SUBDIR."""
    classification = _classify_remote(remote)
    if classification == "local" and not allow_local:
        return (
            f"refused {remote}",
            "Local-path remote requires --allow-local. Skipped.",
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if classification == "local":
        source = Path(remote).expanduser()
        if not source.exists():
            return f"skipped {remote}", f"Local path does not exist: {remote}"
        if dry_run:
            return f"would copy {remote}", None
        # Stage into _repo to mirror clone layout (no .git for local copies).
        repo_dir = destination / "_repo"
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        shutil.copytree(source, repo_dir, ignore=shutil.ignore_patterns(".git"))
        _publish_repo_contents(repo_dir, destination)
        return f"copied {remote}", None
    # URL clone
    return _clone_or_pull(remote, destination, dry_run=dry_run), None


def _clone_or_pull(remote: str, destination: Path, *, dry_run: bool = False) -> str:
    if shutil.which("git") is None:
        raise RuntimeError(
            "git is required for team manifests pointing to a remote URL. "
            "Install git or pass a local path with --allow-local."
        )
    if dry_run:
        return f"would clone/update {remote}"
    repo_dir = destination / "_repo"
    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    if (repo_dir / ".git").exists():
        completed = subprocess.run(
            ["git", "-C", str(repo_dir), "pull", "--ff-only"],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if completed.returncode == 0:
            _publish_repo_contents(repo_dir, destination)
            return f"updated {remote}"
        return f"kept existing checkout for {remote}; git pull failed"
    # Fresh clone (or recovery from a stale partial checkout)
    if destination.exists():
        # Move aside, don't delete user-visible content.
        legacy = destination.with_name(destination.name + f".legacy-{datetime.now(UTC):%Y%m%d-%H%M%S}")
        destination.rename(legacy)
    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "clone", remote, str(repo_dir)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Could not clone {remote}: {completed.stderr.strip()}")
    _publish_repo_contents(repo_dir, destination)
    return f"cloned {remote}"


def _publish_repo_contents(repo_dir: Path, destination: Path) -> None:
    """Copy *.md (and other manifest-allowed files) from repo_dir to destination
    root, skipping any .git directories at any depth. Idempotent — clears
    previously published markdown first."""
    for stale in destination.iterdir() if destination.exists() else []:
        if stale.name == "_repo":
            continue
        if stale.is_dir():
            shutil.rmtree(stale)
        else:
            stale.unlink()
    for path in repo_dir.rglob("*"):
        if ".git" in path.parts:
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(repo_dir)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
```

Then update `_sync_team_payload` so:
- It computes destinations via `_team_destination(root, kind, remote)` only — never under `knowledge/`.
- It refuses any manifest-supplied `knowledge.path` that resolves under `.coding-scaffold/knowledge/`; emits a warning and falls back to the safe location.
- It threads `allow_local` through to `_sync_source` / `_clone_or_pull`.

Update the public functions `sync_team`, `preview_team`, `connect_team` to accept `allow_local: bool = False` and pass it down.

Delete `_remove_nested_git` — `_publish_repo_contents` skips `.git` at any depth so the helper is no longer needed.

- [ ] **Step 4: Add --allow-local to CLI**

In `src/coding_scaffold/cli.py`, find the `team` subparser block and add:

```python
team.add_argument(
    "--allow-local",
    action="store_true",
    help="Permit local-path or file:// remotes for team manifests.",
)
```

Then in the action dispatch (search for `action == "connect"` and `action == "sync"`):

```python
elif action == "connect":
    result = connect_team(target, manifest=args.manifest, allow_local=args.allow_local)
elif action == "sync":
    result = sync_team(target, dry_run=args.dry_run, allow_local=args.allow_local)
```

Add `allow_local: bool = False` to `connect_team`'s and `sync_team`'s signatures and thread through.

- [ ] **Step 5: Update existing team tests that use local paths**

Search `tests/test_team.py` for existing tests that call `sync_team` or `connect_team` with a local path. Add `allow_local=True` to those calls (the protection is intentional; tests opt in explicitly). Then un-skip and implement the two `pytest.skip` regression tests from Step 1 — `_repo/.git` should exist after a stub-git clone; the agent path should not contain any `.git` directories after sync against a fixture with a `subrepo/.git/`.

- [ ] **Step 6: Add the trust-model paragraph to docs**

In `docs/wiki/Team-Onboarding.md`, append:

```markdown
## Trust model

Team manifest content is third-party input. `coding-scaffold team sync`
treats every remote as untrusted: imports land under
`.coding-scaffold/team/sources/<kind>/<slug>/`, never inside your curated
`.coding-scaffold/knowledge/` tree. Review imported markdown before
linking it from your own pages.

`file://` and local-path remotes require `--allow-local` so a teammate's
manifest cannot redirect a sync at an arbitrary directory on your
machine without explicit consent.
```

- [ ] **Step 7: Run tests**

```
uv run ruff check
uv run pytest
```

All green, including the four new regression tests and any existing tests adapted with `allow_local=True`.

- [ ] **Step 8: Commit**

```
git add src/coding_scaffold/team.py src/coding_scaffold/cli.py \
        tests/test_team.py docs/wiki/Team-Onboarding.md
git commit -m "Confine team sync to team/sources; require --allow-local for file paths

Sync now never writes to .coding-scaffold/knowledge/. Remote URLs clone
into a hidden _repo subdir and use git pull --ff-only on subsequent
syncs (no more rmtree-and-reclone). Nested .git directories are filtered
out at publish time, not stripped from the working tree. Local-path and
file:// remotes are gated behind --allow-local.

Closes #30
Closes #36
Closes #43"
```

---

## Task 5 — Final integration: merge to main

- [ ] **Step 1: Verify the integration branch is fully green**

```
uv run ruff check
uv run pytest
```

Both must pass. Expect ~155-160 tests passing + 1 xfailed (#34 deferred).

- [ ] **Step 2: Open a PR from `integration/review-batch-1` to `main`**

```
gh pr create --base main --head integration/review-batch-1 \
  --title "Code review batch 1: critical/important fixes" \
  --body "$(cat <<'EOF'
## Summary

Resolves the design-bearing cluster of the batch-1 code review:

- **#32** Drop article-stripping heuristic in context compression — identifiers in inline code and link targets survive.
- **#31 / #35** Treat Azure endpoint and deployment as secret in serialized config (`Provider.redact_fields`).
- **#39** Policy pack stages `opencode.json.new` and deep-merges `mcp.<server>` / `permission.<scope>` so user customizations survive.
- **#30 / #36 / #43** `team sync` is confined to `.coding-scaffold/team/sources/`; clones keep `.git` inside a hidden `_repo` subdir for ff-pulls; local/`file://` remotes require `--allow-local`.

Plus the mechanical-fix batch already merged into this branch (closes #33, #37, #38, #44, #45, #46, #47, #49) and the case-collision hotfix (`INDEX.md` vs `index.md`).

## Verification

- `uv run ruff check` clean
- `uv run pytest` green (1 xfail for #34, deferred)
- Linux CI must show the case-collision fix clears the failing run on `main`

## Spec / plan

- [Design spec](docs/superpowers/specs/2026-05-18-code-review-batch-1-design.md)
- [Implementation plan](docs/superpowers/plans/2026-05-18-code-review-batch-1.md)
EOF
)"
```

- [ ] **Step 3: Wait for CI to go green, then merge**

```
gh pr merge --merge --delete-branch=false  # keep integration branch for traceability
```

If `--merge` is policy-blocked, use `--squash`. Do not force-push to main.

- [ ] **Step 4: Confirm main is at the new tip**

```
git fetch origin
git log origin/main --oneline -5
```

Last commit should be the merge of `integration/review-batch-1`.

---

## Out-of-scope (deferred to a follow-up batch)

- #34 updater version-file advancement (xfail in this batch).
- #40 intake repo walk caps.
- #41 cli.team subparser refactor.
- #42 RouteLLM YAML quoting.
- #48 parallel CLI argument trees (overlaps #7).

These are mechanical and can fan out to parallel agents in a batch-2 worktree once this PR merges.
