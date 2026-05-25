"""Template loading + substitution with strict placeholder validation (issue #94).

Templates under ``src/coding_scaffold/templates/`` use ``${variable}`` substitution
(``string.Template`` syntax). The risk this module guards against is silent
placeholder leakage: a missing context key, a typo in a placeholder name, or a
delimiter ($) appearing for some other reason all used to be possible failure
modes that ended up writing literal ``${...}`` into user-committed files like
``AGENTS.md``.

Three guarantees:

1. **Missing keys raise a named error.** ``UnresolvedTemplateError`` says which
   template and which key. (``string.Template.substitute`` already raises
   ``KeyError`` for missing keys; we wrap it so the user sees the template name.)
2. **Post-substitution scan.** After ``substitute`` runs, the rendered string is
   scanned for any remaining ``${...}`` token. If one is found, we raise rather
   than ship a broken-looking file to the user.
3. **Literal ``$`` escape.** If a template legitimately needs the ``$`` character
   in output, write ``$$`` — that becomes a literal ``$`` per ``Template``'s spec
   and the post-scan ignores it.
"""

from __future__ import annotations

import re
from importlib.resources import files
from string import Template

TEMPLATE_PACKAGE = "coding_scaffold.templates"

# After substitution, no ``${name}`` should remain. (Literal ``$$`` becomes ``$``
# before this scan runs, so the only way a token survives is if a placeholder
# went unresolved.)
_UNRESOLVED_PATTERN = re.compile(r"\$\{[^}\s]*\}")


class UnresolvedTemplateError(ValueError):
    """A template rendered with an unresolved placeholder or missing key.

    Always names the template and the offending token / key so the user can
    fix it without grepping the source.
    """

    def __init__(self, template: str, *, missing: str | None = None, leftover: str | None = None) -> None:
        if missing is not None:
            super().__init__(
                f"template {template!r} references ${{{missing}}} but no value was provided; "
                f"either pass {missing}= to render_template() or remove the placeholder from the template"
            )
            self.template = template
            self.missing = missing
            self.leftover = None
            return
        if leftover is not None:
            super().__init__(
                f"template {template!r} produced unresolved placeholder {leftover!r} after substitution; "
                "fix the template (typo in name? unintended `$` character? use `$$` for a literal `$`)"
            )
            self.template = template
            self.missing = None
            self.leftover = leftover
            return
        raise ValueError("UnresolvedTemplateError needs missing= or leftover=")


def read_template(name: str) -> str:
    return files(TEMPLATE_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def render_template(name: str, **values: object) -> str:
    """Substitute ``${var}`` placeholders in the named template.

    Raises ``UnresolvedTemplateError`` if any placeholder is missing from
    ``values`` OR if any ``${...}`` token survives substitution (e.g. an
    unintended ``$`` character — escape with ``$$`` for a literal ``$``).
    """

    payload = {key: str(value) for key, value in values.items()}
    template = Template(read_template(name))
    try:
        rendered = template.substitute(payload)
    except KeyError as exc:
        raise UnresolvedTemplateError(name, missing=str(exc).strip("'")) from exc
    leftover_match = _UNRESOLVED_PATTERN.search(rendered)
    if leftover_match:
        raise UnresolvedTemplateError(name, leftover=leftover_match.group(0))
    return rendered
