from coding_scaffold import hardware


def test_detect_nvidia_gpu_parses_name_and_vram(monkeypatch) -> None:
    monkeypatch.setattr(hardware.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(hardware, "_run", lambda command: "NVIDIA RTX 6000 Ada, 49140\n")

    assert hardware._detect_nvidia_gpu() == ("NVIDIA RTX 6000 Ada", 47.99)


def test_detect_nvidia_gpu_handles_malformed_memory(monkeypatch) -> None:
    monkeypatch.setattr(hardware.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(hardware, "_run", lambda command: "NVIDIA RTX, unknown\n")

    assert hardware._detect_nvidia_gpu() == ("NVIDIA RTX", None)


def test_detect_ram_gb_falls_back_to_wmic(monkeypatch) -> None:
    def raise_sysconf(name: str) -> int:
        raise OSError

    monkeypatch.setattr(hardware.os, "sysconf", raise_sysconf, raising=False)
    monkeypatch.setattr(hardware.shutil, "which", lambda name: "wmic" if name == "wmic" else None)
    monkeypatch.setattr(
        hardware,
        "_run",
        lambda command: "TotalPhysicalMemory=17179869184\n",
    )

    assert hardware._detect_ram_gb() == 16.0


def test_detect_ram_gb_handles_invalid_sysconf_values(monkeypatch) -> None:
    def invalid_sysconf(name: str) -> int:
        return -1

    monkeypatch.setattr(hardware.os, "sysconf", invalid_sysconf, raising=False)
    monkeypatch.setattr(hardware.shutil, "which", lambda name: None)

    assert hardware._detect_ram_gb() == 0.0


def test_detect_apple_gpu_uses_neutral_intel_fallback(monkeypatch) -> None:
    monkeypatch.setattr(hardware.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(hardware, "_run", lambda command: "")

    assert hardware._detect_apple_gpu() == ("macOS GPU (unknown)", None)


def test_detect_apple_gpu_uses_apple_silicon_fallback_on_arm(monkeypatch) -> None:
    monkeypatch.setattr(hardware.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(hardware, "_run", lambda command: '{"SPDisplaysDataType": []}')

    assert hardware._detect_apple_gpu() == ("Apple Silicon GPU", None)


def test_is_wsl_detects_release_marker(monkeypatch) -> None:
    monkeypatch.setattr(hardware.platform, "release", lambda: "5.15.90.1-microsoft-standard-WSL2")

    assert hardware._is_wsl() is True
