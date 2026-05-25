from __future__ import annotations

from importlib.resources import files
from string import Template

TEMPLATE_PACKAGE = "coding_scaffold.templates"


def read_template(name: str) -> str:
    return files(TEMPLATE_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def render_template(name: str, **values: object) -> str:
    payload = {key: str(value) for key, value in values.items()}
    return Template(read_template(name)).substitute(payload)
