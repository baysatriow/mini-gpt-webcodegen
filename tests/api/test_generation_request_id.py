import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apps.api import routers
from apps.api.schemas import GenerationRequest, IntakeResponse, RequestDraft


class _CapturingGenerator:
    def __init__(self):
        self.request = None

    def generate(self, request, output_dir):
        self.request = request
        output_dir.mkdir()
        return {"request_id": request["request_id"], "status": "stage_failed"}


class _Runtime:
    def __init__(self, output_root):
        self.settings = SimpleNamespace(
            generation_output_dir=Path(output_root),
            project_root=Path.cwd(),
            host="127.0.0.1",
            port=8000,
        )
        self.generation_lock = threading.Lock()
        self.generator = _CapturingGenerator()

    def get_generator(self):
        return self.generator


class GenerationRequestIdTests(unittest.TestCase):
    def test_generation_preserves_the_validated_intake_request_id(self):
        request_id = "intake-" + "a" * 24
        intake = IntakeResponse(
            status="ready",
            message="ready",
            request={
                "request_id": request_id,
                "prompt": "Buat landing page untuk Kedai Demo.",
                "business_facts": [{"kind": "name", "value": "Kedai Demo"}],
            },
        )
        body = GenerationRequest(
            prompt="Buat landing page untuk Kedai Demo.",
            draft=RequestDraft(),
        )

        with tempfile.TemporaryDirectory() as temporary:
            runtime = _Runtime(temporary)
            with (
                patch("apps.api.routers.generations.get_runtime", return_value=runtime),
                patch("apps.api.routers.generations.validate_intake", return_value=intake),
            ):
                result = routers.generations.create_generation(body)

        self.assertEqual("generation_failed", result.status)
        self.assertEqual(request_id, runtime.generator.request["request_id"])
