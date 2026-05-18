from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class HardwareProfile:
    os_name: str
    is_wsl: bool
    cpu_count: int
    ram_gb: float
    gpu_name: str | None
    vram_gb: float | None
    llmfit_available: bool
    local_runtimes: list[str]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["os"] = data.pop("os_name")
        return data


def probe_hardware() -> HardwareProfile:
    gpu_name, vram_gb = _detect_gpu()
    return HardwareProfile(
        os_name=platform.platform(),
        is_wsl=_is_wsl(),
        cpu_count=os.cpu_count() or 1,
        ram_gb=_detect_ram_gb(),
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        llmfit_available=shutil.which("llmfit") is not None,
        local_runtimes=[name for name in ("ollama", "llama-server", "vllm", "lmstudio") if shutil.which(name)],
    )


def _is_wsl() -> bool:
    release = platform.release().lower()
    if "microsoft" in release or "wsl" in release:
        return True
    version = Path("/proc/version")
    try:
        if version.exists():
            return "microsoft" in version.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return False


def _detect_ram_gb() -> float:
    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if pages <= 0 or page_size <= 0:
                raise ValueError
            return round((pages * page_size) / (1024**3), 2)
        except (OSError, TypeError, ValueError):
            pass
    if shutil.which("wmic"):
        output = _run(["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"])
        for line in output.splitlines():
            if line.startswith("TotalPhysicalMemory="):
                return round(int(line.split("=", 1)[1]) / (1024**3), 2)
    return 0.0


def _detect_gpu() -> tuple[str | None, float | None]:
    nvidia = _detect_nvidia_gpu()
    if nvidia != (None, None):
        return nvidia
    system = platform.system().lower()
    if system == "darwin":
        return _detect_apple_gpu()
    return None, None


def _detect_nvidia_gpu() -> tuple[str | None, float | None]:
    if not shutil.which("nvidia-smi"):
        return None, None
    output = _run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )
    first = next((line for line in output.splitlines() if line.strip()), "")
    if not first:
        return None, None
    name, _, memory_mb = first.partition(",")
    try:
        return name.strip(), round(float(memory_mb.strip()) / 1024, 2)
    except ValueError:
        return name.strip(), None


def _detect_apple_gpu() -> tuple[str | None, float | None]:
    output = _run(["system_profiler", "SPDisplaysDataType", "-json"])
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return _macos_gpu_fallback(), None
    displays = data.get("SPDisplaysDataType", [])
    if not displays:
        return _macos_gpu_fallback(), None
    name = displays[0].get("sppci_model") or displays[0].get("_name")
    return str(name) if name else _macos_gpu_fallback(), None


def _macos_gpu_fallback() -> str:
    if platform.machine().lower() == "arm64":
        return "Apple Silicon GPU"
    return "macOS GPU (unknown)"


def _run(command: list[str]) -> str:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
