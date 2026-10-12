import json
import tempfile
import unittest
from pathlib import Path

from tokenizers import Tokenizer
from src.data.tokenizer import train_tokenizer
from src.data.dataset import PageSpecDataset, encode_pretraining, encode_sft
from tests.data.test_schema import valid_spec


class TokenizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        path = self.root / "train.jsonl"
        self.text = 'Bahasa Indonesia: café, naïve, belajar. <div class="bg-blue-500">Halo</div> body{color:red;} <prompt>'
        path.write_text(json.dumps({"split": "train", "text": self.text}) + "\n", encoding="utf-8")
        tokenizer_path = train_tokenizer(path, self.root / "tok", {"vocab_size": 512, "min_frequency": 1})
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))

    def tearDown(self):
        self.tmp.cleanup()

    def test_unicode_code_and_special_token_roundtrip(self):
        tokens = self.tokenizer.encode(self.text).ids
        self.assertEqual(self.tokenizer.decode(tokens, skip_special_tokens=False), self.text)

    def test_train_tokenizer_rejects_validation_rows(self):
        path = self.root / "bad.jsonl"
        path.write_text(json.dumps({"split": "validation", "text": "should not train"}) + "\n")
        with self.assertRaises(ValueError):
            train_tokenizer(path, self.root / "bad_tok", {"vocab_size": 512})
        self.assertFalse((self.root / "bad_tok/tokenizer.json").exists())

    def test_sft_only_target_and_eos_are_supervised(self):
        target = json.dumps(valid_spec(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ids, labels = encode_sft("Buat profil Indonesia", target, self.tokenizer, 1024)
        boundary = ids.index(self.tokenizer.token_to_id("<target>"))
        self.assertTrue(all(label == -100 for label in labels[:boundary]))
        self.assertNotEqual(labels[boundary], -100)
        supervised = [label for label in labels if label != -100]
        self.assertEqual(self.tokenizer.decode(supervised[:-1], skip_special_tokens=False), target)
        self.assertEqual(supervised[-1], self.tokenizer.token_to_id("<eos>"))
        self.assertEqual(len(ids), 1024)
        self.assertTrue(all(label == -100 for token, label in zip(ids, labels) if token == self.tokenizer.token_to_id("<pad>")))

    def test_oversize_json_and_reserved_prompt_are_rejected(self):
        target = json.dumps(valid_spec())
        with self.assertRaises(ValueError):
            encode_sft("Buat profil", target, self.tokenizer, 8)
        with self.assertRaises(ValueError):
            encode_sft("Buat <target> profil", target, self.tokenizer, 1024)

    def test_pretrain_labels_shift_and_long_documents_are_not_lost(self):
        x, y = encode_pretraining("Halo", self.tokenizer)
        self.assertEqual(x[1:], y[:-1])
        self.assertEqual(y[-1], self.tokenizer.token_to_id("<eos>"))
        ds = PageSpecDataset([{"text": "Halo " * 80}], self.tokenizer, "pretrain", 16)
        self.assertGreater(len(ds), 1)
        self.assertEqual(tuple(ds[0]["input_ids"].shape), (16,))
        self.assertEqual(tuple(ds[len(ds)-1]["labels"].shape), (16,))


if __name__ == "__main__":
    unittest.main()
