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
