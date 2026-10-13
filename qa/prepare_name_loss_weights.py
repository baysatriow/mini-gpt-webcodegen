"""Build train-only name-token loss weights with verified already-shifted label alignment."""
import argparse
import json
import re
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer

from src.data.curriculum import ROOT, verify_manifest, serialize_spec
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file, write_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir', type=Path, required=True)
    parser.add_argument('--name-weight', type=float, default=16)
    args = parser.parse_args()
    directory = args.dataset_dir.resolve()
    manifest = verify_manifest(directory)
    if args.name_weight < 1 or not np.isfinite(args.name_weight): raise ValueError('Invalid positive weight')
    output = directory / 'train.name_weights.npy'
    if output.exists(): raise ValueError('Preserve existing weights')
    tokenizer = Tokenizer.from_file(str(ROOT / 'data/tokenizer/tokenizer.json'))
    labels = np.load(directory / 'train.labels.npy', mmap_mode='r')
    weights = np.lib.format.open_memmap(output, mode='w+', dtype=np.float16, shape=labels.shape)
    name_tokens = 0
    for index, row in enumerate(read_jsonl(directory / 'train.jsonl')):
        serialized = serialize_spec(row['target_spec'], manifest['serialization'])
        encoded = tokenizer.encode(serialized, add_special_tokens=False)
        active = np.flatnonzero(labels[index] != -100)
        if labels[index, active].tolist() != encoded.ids + [tokenizer.token_to_id('<eos>')]:
            raise ValueError('Target labels/JSON offsets mismatch')
        name = json.dumps(row['target_spec']['title'], ensure_ascii=False)
        spans = [(m.start()+1, m.end()-1) for m in re.finditer(re.escape(name), serialized)]
        values = np.zeros(labels.shape[1], dtype=np.float16); values[active] = 1
        for position, (start, end) in enumerate(encoded.offsets):
            if any(start < right and end > left for left, right in spans):
                values[active[position]] = args.name_weight; name_tokens += 1
        weights[index] = values
    weights.flush(); del weights
    report = {'path': str(output.relative_to(ROOT)), 'sha256': sha256_file(output), 'name_weight': args.name_weight,
              'weighted_name_token_positions': name_tokens, 'rows': len(labels),
              'train_sha256': manifest['files']['train']['rows']['sha256'],
              'definition': 'sum(weight * CE) / sum(weight) over supervised tokens; names16x, other targets/EOS1x, prompt/pad0',
              'limits': ['Training-only objective; validation/test retain ordinary target-token cross entropy']}
    write_manifest(directory / 'name_weights.json', report)
    write_manifest(ROOT / 'reports/data/NAME_LOSS_WEIGHTS_V5.json', report)
    print(json.dumps(report))


if __name__ == '__main__': main()
