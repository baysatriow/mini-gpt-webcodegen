from datetime import datetime, timedelta, timezone
import tempfile
import unittest
import uuid
from pathlib import Path

from apps.api.services.usage_store import ActiveUsageInstanceError, UsageStore


def _record(usage_id: str, instance_id: str, started_at: datetime) -> dict:
    return {
        "usage_id": usage_id,
        "server_instance_id": instance_id,
        "started_at": started_at.isoformat(),
        "outcome": "running",
        "stage": "request_received",
    }


class UsageStoreTests(unittest.TestCase):
    def test_start_instance_rejects_a_second_live_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = UsageStore(Path(temporary))
            first = store.start_instance()

            with self.assertRaises(ActiveUsageInstanceError):
                store.start_instance()

            store.stop_instance(first)
            second = store.start_instance()
            self.assertNotEqual(first, second)
            store.stop_instance(second)

    def test_startup_recovers_records_when_the_previous_process_has_exited(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = UsageStore(Path(temporary))
            old_instance = store.start_instance()
            usage_id = str(uuid.uuid4())
            store.create_record(_record(usage_id, old_instance, datetime.now(timezone.utc)))
            store._release_process_lock()

            new_instance = store.start_instance()

            recovered = store.get_record(usage_id)
            self.assertEqual("interrupted", recovered["outcome"])
            self.assertEqual("server_interrupted", recovered["failure_code"])
            self.assertTrue(
                any(
                    event["stage"] == "server_restart" and event["event_type"] == "interrupted"
                    for event in recovered["events"]
                )
            )
            store.stop_instance(new_instance)

    def test_list_records_uses_stable_cursor_and_privacy_allowlist(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = UsageStore(Path(temporary))
            instance = store.start_instance()
            stamp = datetime.now(timezone.utc).isoformat()
            first_id = "00000000-0000-4000-8000-000000000001"
            second_id = "00000000-0000-4000-8000-000000000002"
            store.create_record(_record(first_id, instance, datetime.fromisoformat(stamp)))
            store.create_record(_record(second_id, instance, datetime.fromisoformat(stamp)))

            page = store.list_records(cursor=None, limit=1, window=None, status=None, stage=None)
            next_page = store.list_records(
                cursor=page["next_cursor"], limit=1, window=None, status=None, stage=None
            )

            self.assertEqual([second_id], [row["usage_id"] for row in page["items"]])
            self.assertEqual([first_id], [row["usage_id"] for row in next_page["items"]])
            with self.assertRaises(ValueError):
                store.create_record({**_record(str(uuid.uuid4()), instance, datetime.now(timezone.utc)), "prompt": "private"})
            store.stop_instance(instance)

    def test_retention_removes_expired_sample_before_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = UsageStore(Path(temporary))
            instance = store.start_instance()
            usage_id = str(uuid.uuid4())
            created = datetime.now(timezone.utc) - timedelta(days=100)
            store.create_record(_record(usage_id, instance, created))
            store.append_sample(usage_id, {"sampled_at": created.isoformat(), "utilization_pct": 30.0})
            sample = Path(temporary) / "samples" / f"{usage_id}.jsonl"
            self.assertTrue(sample.is_file())

            removed = store.prune(now=datetime.now(timezone.utc))

            self.assertEqual(1, removed)
            self.assertIsNone(store.get_record(usage_id))
            self.assertFalse(sample.exists())
            store.stop_instance(instance)

    def test_retention_removes_only_uuid_jsonl_orphans_under_samples(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = UsageStore(Path(temporary))
            instance = store.start_instance()
            orphan = Path(temporary) / "samples" / f"{uuid.uuid4()}.jsonl"
            unrelated = Path(temporary) / "samples" / "keep.txt"
            orphan.write_text("{}\n", encoding="utf-8")
            unrelated.write_text("keep", encoding="utf-8")

            store.prune(now=datetime.now(timezone.utc))

            self.assertFalse(orphan.exists())
            self.assertTrue(unrelated.is_file())
            store.stop_instance(instance)


if __name__ == "__main__":
    unittest.main()
