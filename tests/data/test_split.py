import json
import tempfile
import unittest
from pathlib import Path

from src.data.split import assign_splits, canonical_hash, deduplicate, split_jsonl
from src.data.schema import PageExample
from tests.data.test_schema import valid_spec


def records():
    result = []
    for i in range(20):
        spec = valid_spec()
        spec["title"] = f"Page {i}"
        result.append(PageExample(str(i), f"Prompt {i}", spec, "fixture", "a" * 40, "mit", f"layout-{i // 2}"))
    return result


class SplitTests(unittest.TestCase):
    def test_group_never_crosses_split_and_seed_is_repeatable(self):
        first = assign_splits(records(), 42, (0.8, 0.1, 0.1))
        second = assign_splits(list(reversed(records())), 42, (0.8, 0.1, 0.1))
        self.assertEqual([(e.example_id, e.split) for e in first], [(e.example_id, e.split) for e in second])
        groups = {}
        for row in first:
            groups.setdefault(row.group_id, set()).add(row.split)
        self.assertTrue(all(len(value) == 1 for value in groups.values()))
        self.assertEqual(set(e.split for e in first), {"train", "validation", "test"})

    def test_too_few_groups_and_invalid_ratios_are_rejected(self):
        with self.assertRaises(ValueError):
            assign_splits(records()[:4], 42, (0.8, 0.1, 0.1))
        with self.assertRaises(ValueError):
            assign_splits(records(), 42, (0.8, 0.2, 0.2))

    def test_dedup_ignores_source_metadata_but_preserves_distinct_targets(self):
        rows = records()
        unique, rejected = deduplicate(rows + [rows[0]])
        self.assertEqual(len(unique), 20)
        self.assertEqual(len(rejected), 1)
        self.assertNotEqual(canonical_hash(rows[0]), canonical_hash(rows[1]))

    def test_pretrain_split_manifest_matches_files_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            rows = [{"example_id": str(i), "text": f"<html>{i}</html>", "group_id": f"g-{i}", "split": "unsplit"} for i in range(20)]
            raw = path / "rows.jsonl"
            raw.write_text("".join(json.dumps(row) + "\n" for row in rows + [rows[0]]))
            report = split_jsonl(raw, path / "split", seed=42)
            self.assertEqual(report["deduplicated_rows"], 20)
            self.assertEqual(report["duplicates"], 1)
            self.assertEqual(report["group_overlap"], [])
            self.assertEqual(sum(report["row_counts"].values()), 20)


if __name__ == "__main__":
    unittest.main()
