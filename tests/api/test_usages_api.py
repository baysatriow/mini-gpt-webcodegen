from datetime import datetime, timezone
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.api.routers.generations import create_generation
from apps.api.schemas import GenerationRequest, IntakeResponse, RequestDraft
from apps.api.services.usage_audit import UsageRecorder
from apps.api.services.usage_store import UsageStore


class _Generator:
    def generate(self, request, output_dir):
        output_dir.mkdir()
        return {
            "request_id": request["request_id"],
            "status": "stage_failed",
            "attempts": [{"stage": "plan", "generated_tokens": 17}],
            "seconds": 0.2,
        }


class _Runtime:
    def __init__(self, output_root):
        self.settings = SimpleNamespace(
            generation_output_dir=Path(output_root),
            project_root=Path.cwd(),
            checkpoint_path=Path("TRAIN-025-step1800.pt"),
            host="127.0.0.1",
            port=8000,
        )
        self.generation_lock = threading.Lock()
        self.inference_lock = threading.Lock()
        self.generator = _Generator()

    def get_generator(self):
        return self.generator


def _generation_body():
    return GenerationRequest(
        prompt="Buat landing page untuk Kedai Demo.",
        draft=RequestDraft(),
    )


def _ready_intake():
    return IntakeResponse(
        status="ready",
        message="ready",
        request={
            "request_id": "intake-" + "a" * 24,
            "prompt": "Buat landing page untuk Kedai Demo.",
            "business_facts": [{"kind": "name", "value": "Kedai Demo"}],
        },
    )


class UsageApiTests(unittest.TestCase):
    def test_invalid_generation_body_gets_usage_id_and_privacy_safe_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(usage_root=Path(temporary) / "usages")
            with TestClient(app) as client:
                response = client.post("/api/v1/generations", json={"prompt": "private prompt"})

                self.assertEqual(422, response.status_code)
                usage_id = response.headers.get("x-usage-id")
                self.assertIsNotNone(usage_id)
                detail = client.get(f"/api/v1/usages/{usage_id}")

                self.assertEqual(200, detail.status_code)
                record = detail.json()
                self.assertEqual("rejected", record["outcome"])
                self.assertEqual("request_validation", record["stage"])
                self.assertEqual("invalid_request", record["failure_code"])
                self.assertEqual(422, record["http_status"])
                self.assertFalse(record["inference_started"])
                self.assertNotIn("private prompt", str(record))
                self.assertNotIn("prompt", record)

    def test_generation_failure_http_200_is_recorded_as_failed(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = UsageStore(Path(temporary) / "usages")
            instance_id = store.start_instance()
            usage_id = "00000000-0000-4000-8000-000000000010"
            store.create_record(
                {
                    "usage_id": usage_id,
                    "server_instance_id": instance_id,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "outcome": "running",
                    "stage": "request_received",
                }
            )
            recorder = UsageRecorder(store, usage_id, time.monotonic())
            request = SimpleNamespace(state=SimpleNamespace(usage_recorder=recorder))
            runtime = _Runtime(Path(temporary) / "generations")
            with (
                patch("apps.api.routers.generations.get_runtime", return_value=runtime),
                patch("apps.api.routers.generations.validate_intake", return_value=_ready_intake()),
            ):
                response = create_generation(_generation_body(), request)

            record = store.get_record(usage_id)
            self.assertEqual("generation_failed", response.status)
            self.assertEqual("failed", record["outcome"])
            self.assertEqual(200, record["http_status"])
            self.assertTrue(record["inference_started"])
            self.assertEqual("inference_failed", record["failure_code"])
            store.stop_instance(instance_id)

    def test_generation_lock_rejection_is_pre_inference_and_has_safe_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = UsageStore(Path(temporary) / "usages")
            instance_id = store.start_instance()
            usage_id = "00000000-0000-4000-8000-000000000011"
            store.create_record(
                {
                    "usage_id": usage_id,
                    "server_instance_id": instance_id,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "outcome": "running",
                    "stage": "request_received",
                }
            )
            recorder = UsageRecorder(store, usage_id, time.monotonic())
            request = SimpleNamespace(state=SimpleNamespace(usage_recorder=recorder))
            runtime = _Runtime(Path(temporary) / "generations")
            runtime.generation_lock.acquire()
            with patch("apps.api.routers.generations.get_runtime", return_value=runtime):
                with self.assertRaises(HTTPException) as raised:
                    create_generation(_generation_body(), request)

            record = store.get_record(usage_id)
            self.assertEqual(409, raised.exception.status_code)
            self.assertEqual("rejected", record["outcome"])
            self.assertEqual("generation_busy", record["failure_code"])
            self.assertFalse(record["inference_started"])
            runtime.generation_lock.release()
            store.stop_instance(instance_id)

    def test_current_gpu_endpoint_does_not_access_runtime_or_load_models(self):
        snapshot = {
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
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(usage_root=Path(temporary) / "usages")
            with TestClient(app) as client:
                with (
                    patch("apps.api.routers.usages.current_gpu_snapshot", return_value=snapshot),
                    patch("apps.api.routers.usages.get_runtime", create=True, side_effect=AssertionError("runtime accessed")),
                ):
                    response = client.get("/api/v1/usages/gpu/current")
            self.assertEqual(200, response.status_code)
            self.assertFalse(response.json()["available"])

    def test_summary_list_detail_and_cursor_are_typed_and_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(usage_root=Path(temporary) / "usages")
            with TestClient(app) as client:
                invalid = client.post("/api/v1/generations", json={})
                self.assertIsNotNone(invalid.headers.get("x-usage-id"))

                summary = client.get("/api/v1/usages/summary?window=24h")
                page = client.get("/api/v1/usages/?limit=1&window=24h")
                detail = client.get(f"/api/v1/usages/{invalid.headers['x-usage-id']}")
                bad_cursor = client.get("/api/v1/usages/?cursor=not-a-valid-cursor")

            self.assertEqual(200, summary.status_code)
            self.assertEqual(1, summary.json()["total_requests"])
            self.assertEqual(200, page.status_code)
            self.assertEqual(1, len(page.json()["items"]))
            self.assertEqual(200, detail.status_code)
            self.assertEqual(422, bad_cursor.status_code)
            self.assertNotIn("prompt", detail.json())
            self.assertNotIn("source", detail.json())
            self.assertNotIn("exception", detail.json())


if __name__ == "__main__":
    unittest.main()
