from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import __version__


SCAFFOLD_VERSION_FILE = ".coding-scaffold/scaffold-version.json"


def write_scaffold_version(target: Path, files: list[Path]) -> Path:
    root = target.expanduser().resolve()
    payload = {
        "version": 1,
        # `min_supported_scaffold_version` pins the "do not downgrade past this
        # CodingScaffold version" boundary for this project. `setup update` refuses
        # to run when the installed scaffold is older than this — see
        # ``read_min_supported_version`` and the `--force` flag handling in
        # `cli._cmd_update`. Pinned to the current installed version on every
        # write so a project upgraded on vN cannot silently regress on vN-1.
        "min_supported_scaffold_version": __version__,
        "files": {
            display_path(path, root): sha256(path.read_bytes())
            for path in sorted(files)
            if path.exists() and display_path(path, root) != SCAFFOLD_VERSION_FILE
        },
    }
    path = root / SCAFFOLD_VERSION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_scaffold_version(root: Path) -> dict[str, str]:
    path = root / SCAFFOLD_VERSION_FILE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    files = payload.get("files", {})
    if not isinstance(files, dict):
        return {}
    return {str(key): str(value) for key, value in files.items()}


def read_min_supported_version(root: Path) -> str | None:
    """Return ``min_supported_scaffold_version`` from the snapshot, or None.

    None means: the snapshot predates this field (legacy projects) and no version
    boundary is in effect.
    """

    path = root / SCAFFOLD_VERSION_FILE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("min_supported_scaffold_version")
    return str(value) if value else None


def write_scaffold_hashes(root: Path, hashes: dict[str, str]) -> Path:
    path = root / SCAFFOLD_VERSION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "min_supported_scaffold_version": __version__,
        "files": dict(sorted(hashes.items())),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def compare_versions(left: str, right: str) -> int:
    """Lexicographic semver-ish comparator. Returns -1/0/1.

    Tolerates `0.5.1`, `0.5.1.dev0`, `1.0`, `1`. Pre-release suffixes after the
    third part compare lexicographically; this is fine for refusing downgrades
    where the exact ordering of dev-versions is not safety-critical.
    """

    def parts(value: str) -> list[object]:
        out: list[object] = []
        for chunk in value.split("."):
            try:
                out.append((0, int(chunk)))
            except ValueError:
                out.append((1, chunk))
        return out

    a, b = parts(left), parts(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0
