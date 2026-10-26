import subprocess
import threading
import time
import unittest
from unittest.mock import patch

from apps.api.services.usage_telemetry import (
    GenerationGpuSampler,
    begin_torch_memory_measurement,
    current_gpu_snapshot,
    finish_torch_memory_measurement,
)


class UsageTelemetryTests(unittest.TestCase):
    @patch("apps.api.services.usage_telemetry.subprocess.run")
    def test_current_gpu_returns_normalized_device_fields(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="NVIDIA GeForce RTX 5070, 12, 4500, 12288, 200.5, 61, 1890\n",
            stderr="",
        )

        result = current_gpu_snapshot()

        self.assertTrue(result["available"])
        self.assertEqual("NVIDIA GeForce RTX 5070", result["device_name"])
        self.assertEqual(12.0, result["utilization_pct"])
        self.assertEqual(4500.0, result["memory_used_mib"])
        self.assertEqual(12288.0, result["memory_total_mib"])
        self.assertEqual(200.5, result["power_w"])

    @patch("apps.api.services.usage_telemetry.subprocess.run", side_effect=FileNotFoundError("private path"))
    def test_current_gpu_failure_is_nullable_and_does_not_expose_exception(self, run):
        result = current_gpu_snapshot()

        self.assertFalse(result["available"])
        self.assertEqual("gpu_telemetry_unavailable", result["availability_code"])
        self.assertIsNone(result["utilization_pct"])
        self.assertNotIn("private path", str(result))

    @patch("apps.api.services.usage_telemetry.current_gpu_snapshot")
    def test_generation_sampler_appends_only_safe_samples(self, snapshot):
        snapshot.return_value = {
            "available": True,
            "availability_code": None,
            "device_name": "NVIDIA GeForce RTX 5070",
            "sampled_at": "2026-10-26T05:00:00+00:00",
            "utilization_pct": 30.0,
            "memory_used_mib": 4500.0,
            "memory_total_mib": 12288.0,
            "power_w": 130.0,
            "temperature_c": 55.0,
            "sm_clock_mhz": 1800.0,
        }
        samples = []
        lock = threading.Lock()

        class Store:
            def append_sample(self, usage_id, sample):
                with lock:
                    samples.append((usage_id, sample))

        sampler = GenerationGpuSampler(Store(), "usage-1", interval_seconds=0.1)
        sampler.start()
        time.sleep(0.15)
        result = sampler.finish()

        self.assertGreaterEqual(result["gpu_sample_count"], 1)
        self.assertTrue(samples)
        self.assertTrue(all(item[0] == "usage-1" for item in samples))
        self.assertTrue(all("error" not in item[1] for item in samples))

    def test_torch_peak_metrics_report_baseline_and_delta(self):
        with (
            patch("torch.cuda.is_available", return_value=True),
            patch("torch.cuda.current_device", return_value=0),
            patch("torch.cuda.memory_allocated", return_value=100),
            patch("torch.cuda.memory_reserved", return_value=200),
            patch("torch.cuda.max_memory_allocated", return_value=300),
            patch("torch.cuda.max_memory_reserved", return_value=500),
            patch("torch.cuda.reset_peak_memory_stats") as reset,
        ):
            baseline = begin_torch_memory_measurement()
            result = finish_torch_memory_measurement(baseline)

        self.assertEqual(100, result["torch_allocated_baseline_bytes"])
        self.assertEqual(200, result["torch_reserved_baseline_bytes"])
        self.assertEqual(300, result["torch_allocated_peak_bytes"])
        self.assertEqual(500, result["torch_reserved_peak_bytes"])
        self.assertEqual(200, result["torch_allocated_delta_bytes"])
        self.assertEqual(300, result["torch_reserved_delta_bytes"])
        reset.assert_called_once_with(0)

    @patch("torch.cuda.is_available", return_value=False)
    def test_torch_memory_metrics_stay_unavailable_without_cuda(self, available):
        self.assertIsNone(begin_torch_memory_measurement())


if __name__ == "__main__":
    unittest.main()
