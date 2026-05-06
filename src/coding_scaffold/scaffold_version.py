from __future__ import annotations

import hashlib
import json
from pathlib import Path


SCAFFOLD_VERSION_FILE = ".coding-scaffold/scaffold-version.json"


def write_scaffold_version(target: Path, files: list[Path]) -> Path:
    root = target.expanduser().resolve()
    payload = {
        "version": 1,
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


def write_scaffold_hashes(root: Path, hashes: dict[str, str]) -> Path:
    path = root / SCAFFOLD_VERSION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "files": dict(sorted(hashes.items()))}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
