"""Offline validation of Agent Skills' required scalar frontmatter fields.

This is deliberately not a YAML loader. It reads plain/quoted strings and indented
folded/literal blocks, ignores unrelated metadata, and rejects ambiguous required
fields instead of executing tags or resolving aliases.
"""

from __future__ import annotations

import json
import re


def validate_skill_metadata(text: str, directory_name: str) -> list[str]:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return ["SKILL.md needs YAML frontmatter with name and description."]
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return ["SKILL.md frontmatter is missing its closing --- delimiter."]
    values: dict[str, str] = {}
    errors: list[str] = []
    for index in range(1, end):
        match = re.match(r"^(name|description):\s*(.*)$", lines[index])
        if not match:
            continue
        key, raw = match.groups()
        if not raw.startswith(('"', "'")):
            raw = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
        if key in values:
            errors.append(f"Duplicate frontmatter field: {key}.")
        continuation = []
        for line in lines[index + 1 : end]:
            if line and not line[0].isspace():
                break
            continuation.append(line.strip())
        try:
            if re.fullmatch(r"[>|][+-]?", raw):
                value = " ".join(continuation).strip()
            elif raw.startswith('"'):
                value, consumed = json.JSONDecoder().raw_decode(raw)
                trailing = raw[consumed:].strip()
                if not isinstance(value, str) or (trailing and not trailing.startswith("#")):
                    raise ValueError
            elif raw.startswith("'"):
                quoted = re.fullmatch(r"'((?:[^']|'')*)'(?:\s+#.*)?", raw)
                if not quoted:
                    raise ValueError
                value = quoted.group(1).replace("''", "'")
            else:
                raw = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
                if (
                    raw.startswith(("[", "{", "!", "&", "*"))
                    or raw
                    in {
                        "null",
                        "Null",
                        "NULL",
                        "~",
                        "true",
                        "false",
                        "True",
                        "False",
                    }
                    or re.fullmatch(r"[-+]?\d+(\.\d+)?", raw)
                ):
                    raise ValueError
                if re.search(r":\s", raw):
                    raise ValueError
                value = " ".join([raw, *continuation]).strip()
            values[key] = value
        except (ValueError, TypeError):
            errors.append(
                f"{key} must be a plain, quoted, or block string; quote special YAML syntax."
            )
            values[key] = ""
    name = values.get("name", "")
    if not name or len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append(
            "name must be 1–64 lowercase letters/digits with single hyphens between words."
        )
    elif name != directory_name:
        errors.append(f"name {name!r} must match directory {directory_name!r}.")
    description = values.get("description", "")
    if not description or len(description) > 1024:
        errors.append("description must be a non-empty string of at most 1024 characters.")
    return errors
