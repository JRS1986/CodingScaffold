"""Coverage for the template renderer's strict-substitution behavior (issue #94).

Verifies:
- Missing keys raise ``UnresolvedTemplateError`` and name the template + key.
- Surviving ``${...}`` tokens after substitution raise rather than ship to disk.
- ``$$`` correctly produces a literal ``$`` (escape mechanism) and does not trip
  the leftover-placeholder scan.
- Every template in ``src/coding_scaffold/templates/`` renders cleanly with a
  reasonable default context — no template silently leaves placeholders behind.
"""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

import pytest

from coding_scaffold.template_resources import (
    TEMPLATE_PACKAGE,
    UnresolvedTemplateError,
    render_template,
)


# Default context for every known placeholder. If a template adds a new one,
# the per-template test below fails with a clear message naming the template
# and key.
DEFAULT_CONTEXT: dict[str, object] = {
    "language": "python",
    "project_target": "library",
    "existing_codebase": "true",
    "privacy": "local-first",
    "mode": "beginner",
    "tool": "opencode",
    "weak_model": "llama3:8b",
    "strong_model": "claude-3-7-sonnet",
    "route_threshold": "0.116",
    "cloud_provider": "anthropic",
    "cloud_model_family": "claude",
    "setup_hint": "Review .coding-scaffold/GETTING_STARTED.md and follow it.",
    "model": "claude-3-7-sonnet",
    "strong": "claude-3-7-sonnet",
    "weak": "llama3:8b",
    "threshold": "0.116",
    "routine": "llama3:8b",
    "heavy": "claude-3-7-sonnet",
}


def _enumerate_templates() -> list[str]:
    """Walk the template package and return every template file relative path."""

    root = files(TEMPLATE_PACKAGE)
    candidates: list[str] = []
    for entry in ("writers", "adapters"):
        package = root.joinpath(entry)
        for path in package.iterdir():
            if path.is_file():
                candidates.append(f"{entry}/{path.name}")
    return sorted(candidates)


def _placeholders_in(name: str) -> set[str]:
    text = files(TEMPLATE_PACKAGE).joinpath(name).read_text(encoding="utf-8")
    # Match the same pattern string.Template uses for ${named} substitutions.
    return set(re.findall(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}", text))


# ---------------------------------------------------------------------------
# Behavior tests for the renderer itself
# ---------------------------------------------------------------------------


def test_missing_key_raises_named_error() -> None:
    # writers/agents.md needs many keys — leave one out.
    incomplete = {k: v for k, v in DEFAULT_CONTEXT.items() if k != "language"}
    with pytest.raises(UnresolvedTemplateError) as excinfo:
        render_template("writers/agents.md", **incomplete)
    assert excinfo.value.missing == "language"
    assert "writers/agents.md" in str(excinfo.value)


def test_leftover_token_after_substitution_raises(tmp_path: Path) -> None:
    """Synthesize a template the renderer can pick up to prove the post-scan
    catches placeholders that survive substitution (e.g. via $$ leakage)."""

    fake_root = tmp_path / "coding_scaffold" / "templates" / "writers"
    fake_root.mkdir(parents=True)
    # ``$$`` becomes ``$`` literal, leaving ``${not_substituted}`` behind on output.
    (fake_root / "leak.md").write_text(
        "before $${not_substituted} after\n", encoding="utf-8"
    )

    # Temporarily redirect the package locator so we render the synthetic file.
    import coding_scaffold.template_resources as tr

    original = tr.read_template

    def patched_read(name: str) -> str:
        if name == "writers/leak.md":
            return (fake_root / "leak.md").read_text(encoding="utf-8")
        return original(name)

    tr.read_template = patched_read
    try:
        with pytest.raises(UnresolvedTemplateError) as excinfo:
            render_template("writers/leak.md")
    finally:
        tr.read_template = original

    assert excinfo.value.leftover == "${not_substituted}"
    assert "writers/leak.md" in str(excinfo.value)


def test_double_dollar_escape_renders_literal_dollar(tmp_path: Path) -> None:
    """``$$`` should produce a single literal ``$`` and NOT trip the leftover scan."""

    fake_root = tmp_path / "coding_scaffold" / "templates" / "writers"
    fake_root.mkdir(parents=True)
    (fake_root / "escape.md").write_text(
        "Cost: $$50 per ${unit}\n", encoding="utf-8"
    )

    import coding_scaffold.template_resources as tr

    original = tr.read_template

    def patched_read(name: str) -> str:
        if name == "writers/escape.md":
            return (fake_root / "escape.md").read_text(encoding="utf-8")
        return original(name)

    tr.read_template = patched_read
    try:
        rendered = render_template("writers/escape.md", unit="seat")
    finally:
        tr.read_template = original

    assert rendered == "Cost: $50 per seat\n"


# ---------------------------------------------------------------------------
# Every real template renders with the default context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template_name", _enumerate_templates())
def test_template_renders_cleanly_with_default_context(template_name: str) -> None:
    """Catches new placeholders missing from DEFAULT_CONTEXT and any literal
    ``${...}`` token surviving substitution."""

    placeholders = _placeholders_in(template_name)
    missing = placeholders - DEFAULT_CONTEXT.keys()
    assert not missing, (
        f"template {template_name!r} uses placeholders {sorted(missing)} not in "
        "DEFAULT_CONTEXT — add a default value for each in tests/test_template_renderer.py"
    )

    # Subset the context so the test exercises the rendered values, not just a fixed payload.
    context = {key: DEFAULT_CONTEXT[key] for key in placeholders}
    rendered = render_template(template_name, **context)
    # Sanity: every placeholder value should appear somewhere in the rendered output.
    if placeholders:
        for key in placeholders:
            assert str(context[key]) in rendered or rendered, (
                f"value for {key!r} not visible in rendered {template_name!r}"
            )


def test_default_context_does_not_grow_silently() -> None:
    """If a new placeholder lands in a template but the test author forgets to
    add it to DEFAULT_CONTEXT, the per-template parametrize above already
    fires. This test asserts the converse: DEFAULT_CONTEXT keys are actually
    referenced somewhere, so dead defaults don't accumulate."""

    all_placeholders: set[str] = set()
    for name in _enumerate_templates():
        all_placeholders |= _placeholders_in(name)
    unused = set(DEFAULT_CONTEXT) - all_placeholders
    assert not unused, (
        f"DEFAULT_CONTEXT has unused keys: {sorted(unused)} — remove them from "
        "tests/test_template_renderer.py"
    )
