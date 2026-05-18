from __future__ import annotations

import json
from pathlib import Path


def write_text(path: Path, content: str, *, overwrite: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if overwrite or not path.exists():
        path.write_text(content, encoding="utf-8")
    return path


def write_json(path: Path, payload: object, *, overwrite: bool = True, sort_keys: bool = True) -> Path:
    return write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=sort_keys) + "\n",
        overwrite=overwrite,
    )


def collect_text(files: list[Path], skipped: list[Path], path: Path, content: str) -> None:
    if path.exists():
        skipped.append(path)
        return
    files.append(write_text(path, content, overwrite=False))


def collect_json(
    files: list[Path],
    skipped: list[Path],
    path: Path,
    payload: object,
    *,
    sort_keys: bool = True,
) -> None:
    if path.exists():
        skipped.append(path)
        return
    files.append(write_json(path, payload, overwrite=False, sort_keys=sort_keys))
