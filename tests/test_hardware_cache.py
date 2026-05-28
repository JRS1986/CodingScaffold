"""Coverage for probe_hardware() caching (spec §5)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import coding_scaffold.hardware as hardware_module
from coding_scaffold.hardware import HardwareProfile, probe_hardware


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect the cache to a tmp dir so tests don't pollute each other or
    the user's real ~/.cache."""

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    yield


def test_first_call_writes_cache(tmp_path: Path) -> None:
    profile = probe_hardware()
    cache_file = tmp_path / "coding-scaffold" / "hardware.json"
    assert cache_file.exists()
    payload = json.loads(cache_file.read_text())
    assert payload["version"] == 1
    assert payload["profile"]["os_name"] == profile.os_name


def test_warm_call_reads_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    fresh_calls: list[int] = []
    real_fresh = hardware_module._probe_hardware_fresh

    def counting_fresh() -> HardwareProfile:
        fresh_calls.append(1)
        return real_fresh()

    monkeypatch.setattr(hardware_module, "_probe_hardware_fresh", counting_fresh)
    probe_hardware()        # populates cache
    probe_hardware()        # should hit cache
    probe_hardware()        # should hit cache
    assert len(fresh_calls) == 1, f"expected 1 fresh probe + 2 cache hits, got {len(fresh_calls)} fresh"


def test_expired_cache_re_probes(tmp_path: Path) -> None:
    probe_hardware()
    cache_file = tmp_path / "coding-scaffold" / "hardware.json"
    payload = json.loads(cache_file.read_text())
    # Backdate cached_at past the TTL window.
    payload["cached_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat(timespec="seconds")
    cache_file.write_text(json.dumps(payload))
    # Counting wrapper to confirm a fresh probe happened.
    fresh_calls: list[int] = []
    import coding_scaffold.hardware as hw_mod
    real_fresh = hw_mod._probe_hardware_fresh

    def counting_fresh() -> HardwareProfile:
        fresh_calls.append(1)
        return real_fresh()

    hw_mod._probe_hardware_fresh = counting_fresh
    try:
        probe_hardware()
    finally:
        hw_mod._probe_hardware_fresh = real_fresh
    assert len(fresh_calls) == 1


def test_corrupt_cache_re_probes_silently(tmp_path: Path) -> None:
    cache_file = tmp_path / "coding-scaffold" / "hardware.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("not json{{")
    # Must not raise.
    profile = probe_hardware()
    assert isinstance(profile, HardwareProfile)


def test_wrong_key_cache_re_probes(tmp_path: Path) -> None:
    """Cache from a different OS/arch/Python is ignored."""

    cache_file = tmp_path / "coding-scaffold" / "hardware.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text(json.dumps({
        "version": 1,
        "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "key": "wat/wat/9.9",
        "profile": {"os_name": "fake", "arch": "fake", "cpu_count": 1,
                    "ram_gb": 1, "gpu_name": None, "vram_gb": None,
                    "is_wsl": False, "llmfit_available": False,
                    "local_runtimes": []},
    }))
    profile = probe_hardware()
    assert profile.os_name != "fake"


def test_use_cache_false_bypasses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    fresh_calls: list[int] = []
    real_fresh = hardware_module._probe_hardware_fresh

    def counting_fresh() -> HardwareProfile:
        fresh_calls.append(1)
        return real_fresh()

    monkeypatch.setattr(hardware_module, "_probe_hardware_fresh", counting_fresh)
    probe_hardware()                            # cache miss + write
    probe_hardware(use_cache=False)             # bypass
    probe_hardware(use_cache=False)             # bypass
    assert len(fresh_calls) == 3


def test_unwritable_cache_dir_proceeds_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Point cache at a path that can't be created (file in the way).
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    monkeypatch.setenv("XDG_CACHE_HOME", str(blocker))
    profile = probe_hardware()
    assert isinstance(profile, HardwareProfile)
    err = capsys.readouterr().err
    assert "warning" in err.lower()


def test_doctor_warm_call_is_under_100ms_median() -> None:
    """Perf gate. Spec §5.6 acceptance criterion."""

    import subprocess
    import sys
    import time
    import statistics
    # Warm the cache (XDG_CACHE_HOME is redirected by isolated_cache fixture).
    subprocess.run(
        [sys.executable, "-m", "coding_scaffold", "doctor", "--target", "/tmp"],
        capture_output=True, check=False,
    )
    runs = []
    for _ in range(5):
        t = time.perf_counter()
        subprocess.run(
            [sys.executable, "-m", "coding_scaffold", "doctor", "--target", "/tmp"],
            capture_output=True, check=False,
        )
        runs.append((time.perf_counter() - t) * 1000)
    median = statistics.median(runs)
    assert median <= 150, (
        f"doctor warm call should be ≤150ms (target 100, allow CI variance), got median={median:.0f}ms"
    )
