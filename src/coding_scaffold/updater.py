from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from .hardware import HardwareProfile
from .intake import IntakeAnswers
from .providers import Provider
from .router import RoutingPlan
from .scaffold_version import (
    SCAFFOLD_VERSION_FILE,
    display_path,
    read_scaffold_version,
    sha256,
    write_scaffold_hashes,
)
from .adapters import write_tool_adapter
from .writers import write_scaffold


@dataclass(frozen=True)
class ScaffoldUpdateResult:
    updated: list[Path]
    staged: list[Path]
    skipped: list[Path]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "updated": [str(path) for path in self.updated],
            "staged": [str(path) for path in self.staged],
            "skipped": [str(path) for path in self.skipped],
            "warnings": self.warnings,
        }

def refresh_scaffold(
    target: Path,
    intake: IntakeAnswers,
    hardware: HardwareProfile,
    providers: list[Provider],
    routing: RoutingPlan,
) -> ScaffoldUpdateResult:
    root = target.expanduser().resolve()
    previous = read_scaffold_version(root)
    updated: list[Path] = []
    staged: list[Path] = []
    skipped: list[Path] = []
    warnings: list[str] = []
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp).resolve()
        manifest = write_scaffold(temp_root, intake, hardware, providers, routing)
        adapter = (
            write_tool_adapter(temp_root, intake.tool)
            if intake.tool and intake.tool != "manual"
            else None
        )
        generated_files = [path for path in manifest.files if path.exists()]
        if adapter:
            generated_files.extend(path for path in adapter.files if path.exists())
        next_hashes: dict[str, str] = {}
        for generated in generated_files:
            relative = display_path(generated, temp_root)
            if relative == SCAFFOLD_VERSION_FILE:
                continue
            desired = generated.read_bytes()
            desired_hash = sha256(desired)
            destination = root / relative
            previous_hash = previous.get(relative)
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(desired)
                updated.append(destination)
                next_hashes[relative] = desired_hash
                continue
            current = destination.read_bytes()
            current_hash = sha256(current)
            if current_hash == desired_hash:
                skipped.append(destination)
                next_hashes[relative] = desired_hash
                continue
            if previous_hash and current_hash == previous_hash:
                destination.write_bytes(desired)
                updated.append(destination)
                next_hashes[relative] = desired_hash
                continue
            staged_path = _new_path(destination)
            staged_path.write_bytes(desired)
            staged.append(staged_path)
            next_hashes[relative] = previous_hash if previous_hash else desired_hash
    version_path = write_scaffold_hashes(root, next_hashes)
    updated.append(version_path)
    if not previous:
        warnings.append(
            "No previous scaffold-version.json was found; edited existing files were staged as .new."
        )
    return ScaffoldUpdateResult(sorted(updated), sorted(staged), sorted(skipped), warnings)


def _new_path(path: Path) -> Path:
    candidate = path.with_name(f"{path.name}.new")
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.new{index}")
        index += 1
    return candidate
