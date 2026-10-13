"""Audit literal name/token exposure using training titles only, without heldout labels."""
import argparse
from collections import Counter
from pathlib import Path

from tokenizers import Tokenizer
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file, write_manifest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir', type=Path, required=True)
    parser.add_argument('--name', action='append', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists(): raise ValueError('Preserve previous audit')
    tokenizer = Tokenizer.from_file(str(ROOT / 'data/tokenizer/tokenizer.json'))
    counts, titles = Counter(), set()
    for row in read_jsonl(args.dataset_dir / 'train.jsonl'):
        title = row['target_spec']['title']
        titles.add(title); counts.update(tokenizer.encode(title).ids)
    records = [{'name': name, 'exact_title_in_train': name in titles,
                'token_exposure': [{'id': i, 'piece': tokenizer.decode([i]), 'train_title_occurrences': counts[i]}
                                   for i in tokenizer.encode(name).ids]} for name in args.name]
    report = {'train_sha256': sha256_file(args.dataset_dir / 'train.jsonl'), 'train_title_families': len(titles),
              'tokenizer_sha256': sha256_file(ROOT / 'data/tokenizer/tokenizer.json'), 'records': records,
              'limits': ['Training titles only; exposure is not proof of correct autoregressive copying',
                         'Development probes are not independent final benchmark cases']}
    write_manifest(args.report, report)
    import json
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__': main()
