"""Safe, best-effort NVIDIA telemetry for Usage records."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import subprocess
import threading
from typing import Any


_DEVICE_FIELDS = (
    "device_name",
    "utilization_pct",
    "memory_used_mib",
    "memory_total_mib",
    "power_w",
    "temperature_c",
    "sm_clock_mhz",
)
_QUERY = ",".join(
    (
        "name",
        "utilization.gpu",
        "memory.used",
        "memory.total",
        "power.draw",
        "temperature.gpu",
        "clocks.current.sm",
    )
)
_NUMBER_FIELDS = _DEVICE_FIELDS[1:]


def _number(value: str) -> float | None:
    trimmed = value.strip()
    if trimmed.lower() in {"n/a", "na", "[not supported]", "[n/a]", ""}:
        return None
    try:
        number = float(trimmed)
    except ValueError:
        return None
    return number if number >= 0 else None


def current_gpu_snapshot() -> dict[str, Any]:
    base = {
        "available": False,
        "availability_code": "gpu_telemetry_unavailable",
        "sampled_at": datetime.now(timezone.utc).isoformat(),
        "device_name": None,
        "utilization_pct": None,
        "memory_used_mib": None,
        "memory_total_mib": None,
        "power_w": None,
        "temperature_c": None,
        "sm_clock_mhz": None,
    }
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "-i",
                "0",
                f"--query-gpu={_QUERY}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        rows = list(csv.reader(io.StringIO(result.stdout)))
        if not rows or len(rows[0]) != len(_DEVICE_FIELDS):
            return base
        values = rows[0]
        name = values[0].strip()[:120] or None
        base.update(
            {
                "available": True,
                "availability_code": None,
                "device_name": name,
                **{field: _number(value) for field, value in zip(_NUMBER_FIELDS, values[1:], strict=True)},
            }
        )
        return base
    except Exception:
        return base


def begin_torch_memory_measurement() -> dict[str, int] | None:
    """Capture the resident-model baseline and reset generation peak counters."""
    try:
        import torch

        if not torch.cuda.is_available():
            return None
        device = torch.cuda.current_device()
        baseline = {
            "device": device,
            "allocated": int(torch.cuda.memory_allocated(device)),
            "reserved": int(torch.cuda.memory_reserved(device)),
        }
        torch.cuda.reset_peak_memory_stats(device)
        return baseline
    except Exception:
        return None


def finish_torch_memory_measurement(baseline: dict[str, int] | None) -> dict[str, int | None]:
    fields = (
        "torch_allocated_baseline_bytes",
        "torch_reserved_baseline_bytes",
        "torch_allocated_peak_bytes",
        "torch_reserved_peak_bytes",
        "torch_allocated_delta_bytes",
        "torch_reserved_delta_bytes",
    )
    unavailable = {field: None for field in fields}
    if baseline is None:
        return unavailable
    try:
        import torch

        device = baseline["device"]
        allocated_peak = int(torch.cuda.max_memory_allocated(device))
        reserved_peak = int(torch.cuda.max_memory_reserved(device))
        allocated_baseline = baseline["allocated"]
        reserved_baseline = baseline["reserved"]
        return {
            "torch_allocated_baseline_bytes": allocated_baseline,
            "torch_reserved_baseline_bytes": reserved_baseline,
            "torch_allocated_peak_bytes": allocated_peak,
            "torch_reserved_peak_bytes": reserved_peak,
            "torch_allocated_delta_bytes": max(0, allocated_peak - allocated_baseline),
            "torch_reserved_delta_bytes": max(0, reserved_peak - reserved_baseline),
        }
    except Exception:
        return unavailable


class GenerationGpuSampler:
    def __init__(self, store, usage_id: str, interval_seconds: float = 1.0) -> None:
        if not 0.1 <= interval_seconds <= 60:
            raise ValueError("GPU sampling interval must be between 0.1 and 60 seconds")
        self.store = store
        self.usage_id = usage_id
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._sample_count = 0
        self._device_name: str | None = None
        self._sums = {field: 0.0 for field in _NUMBER_FIELDS}
        self._maxima = {
            "utilization_pct": None,
            "memory_used_mib": None,
            "temperature_c": None,
        }
        self._memory_total_mib: float | None = None

    def start(self) -> GenerationGpuSampler:
        if self._thread is not None:
            return self
        self._thread = threading.Thread(target=self._loop, name="usage-gpu-sampler", daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.is_set():
            snapshot = current_gpu_snapshot()
            if snapshot["available"]:
                sample = {field: snapshot[field] for field in _SAMPLE_FIELDS_FOR_STORE}
                try:
                    self.store.append_sample(self.usage_id, sample)
                except Exception:
                    self._stop.set()
                    return
                with self._lock:
                    self._sample_count += 1
                    self._device_name = snapshot["device_name"] or self._device_name
                    self._memory_total_mib = snapshot["memory_total_mib"] or self._memory_total_mib
                    for field in _NUMBER_FIELDS:
                        value = snapshot[field]
                        if value is not None:
                            self._sums[field] += value
                    for field in self._maxima:
                        value = snapshot[field]
                        if value is not None:
                            current = self._maxima[field]
                            self._maxima[field] = value if current is None else max(current, value)
            self._stop.wait(self.interval_seconds)

    def finish(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=6)
        with self._lock:
            return {
                "gpu_sample_count": self._sample_count,
                "gpu_device_name": self._device_name,
                "gpu_utilization_sum_pct": self._sums["utilization_pct"] if self._sample_count else None,
                "gpu_utilization_max_pct": self._maxima["utilization_pct"],
                "gpu_memory_sum_mib": self._sums["memory_used_mib"] if self._sample_count else None,
                "gpu_memory_max_mib": self._maxima["memory_used_mib"],
                "gpu_memory_total_mib": self._memory_total_mib,
                "gpu_power_sum_w": self._sums["power_w"] if self._sample_count else None,
                "gpu_temperature_max_c": self._maxima["temperature_c"],
                "gpu_sm_clock_sum_mhz": self._sums["sm_clock_mhz"] if self._sample_count else None,
            }


_SAMPLE_FIELDS_FOR_STORE = (
    "sampled_at",
    "device_name",
    "utilization_pct",
    "memory_used_mib",
    "memory_total_mib",
    "power_w",
    "temperature_c",
    "sm_clock_mhz",
)
