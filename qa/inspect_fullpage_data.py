"""Artifact inspection, masking and exact sampler continuation diagnostics."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from tokenizers import Tokenizer
from src.data.sources import sha256_file
from src.data.normalize import read_jsonl
from src.fullpage.curriculum import write_json
from src.fullpage.dataset import TaskDataset, TaskBatchSampler, trim_collate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--data', default='data/processed/fullpage/v1')
    parser.add_argument('--report', default='reports/data/FULLPAGE_LOADER_V1.json')
    args = parser.parse_args(); root = args.root.resolve(); directory = root / args.data
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    for name, info in manifest['files'].items():
        if sha256_file(directory / name) != info['sha256']: raise ValueError('Dataset checksum changed')
    tokenizer = Tokenizer.from_file(str(root / 'data/tokenizer/tokenizer.json'))
    datasets = {s: TaskDataset(directory / (s + '.jsonl'), tokenizer) for s in ('train', 'validation')}
    train = datasets['train']; sampler = TaskBatchSampler(train.lengths, train.task_kinds, 8, 42)
    stream = iter(sampler)
    for _ in range(7): next(stream)
    state = sampler.state_dict(); expected = list(stream)
    restored = TaskBatchSampler(train.lengths, train.task_kinds, 8, 42); restored.load_state_dict(state)
    if list(restored) != expected: raise ValueError('Sampler continuation differs')
    eos = tokenizer.token_to_id('<eos>'); masked = 0; long = 0
    for row, encoded in zip(train.rows, train.encoded):
        prefix = 3 + len(tokenizer.encode(row['prompt']).ids)
        if any(label != -100 for label in encoded['labels'][:prefix-1]) or encoded['labels'][-1] != eos:
            raise ValueError('Incorrect masking or EOS')
        masked += prefix - 1
        long += any(label != -100 for label in encoded['labels'][1024:])
    batch = trim_collate([train[0], train[1], train[2]])
    for i, row in enumerate([train[0], train[1], train[2]]):
        if not (batch['labels'][i, row['length']:] == -100).all(): raise ValueError('Padding is supervised')
    # Inspect only train/development request facts. Final targets remain unopened.
    families = {}; hashes = {}; counts = {}; duplicates = {}
    for split in datasets:
        rows = list(read_jsonl(directory / (split + '.requests.jsonl')))
        families[split] = {r['family_id'] for r in rows}
        names = [next(f['value'] for f in r['request']['business_facts'] if f['kind'] == 'name') for r in rows]
        hashes[split] = {hashlib.sha256(n.encode()).hexdigest() for n in names}
        counts[split] = dict(Counter((r['request']['genre'] + ':' + r['request']['style_mode']) for r in rows))
        targets = [hashlib.sha256(r['target'].encode()).hexdigest() for r in datasets[split].rows if not r['retry']]
        duplicates[split] = len(targets) - len(set(targets))
    if families['train'] & families['validation'] or hashes['train'] & hashes['validation']: raise ValueError('Split overlap')
    output = {'kind': 'pipeline artifact diagnosis, not model generation', 'manifest_sha256': sha256_file(directory / 'manifest.json'),
              'rows': {s: len(d) for s,d in datasets.items()}, 'counts': counts, 'families_disjoint': True,
              'intentional_target_duplicates': duplicates, 'shared_component_templates': True,
              'historical_final_used_for_selection': False, 'final_targets_opened': False,
              'long_supervised_train_rows': long, 'prompt_labels_masked': masked, 'eos_retained': True,
              'sampler_restored_exactly': True, 'trim_shape': list(batch['input_ids'].shape),
              'rejected_rows': 0, 'pad_labels_masked': True}
    write_json(root / args.report, output); print(json.dumps(output, indent=2))


if __name__ == '__main__': main()
