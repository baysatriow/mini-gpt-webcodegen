"""Trace target boundaries and teacher-forced accuracy using train/development only."""
import argparse
import json
from pathlib import Path

import torch
from tokenizers import Tokenizer

from src.data.dataset import encode_sft
from src.data.normalize import read_jsonl
from src.data.sources import write_manifest
from src.evaluation.generate import _generate, assess_output
from src.models.minigpt import MiniGPT
from src.training.engine import _autocast, load_checkpoint, read_checkpoint, checkpoint_sha256

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--report-id', required=True)
    args = parser.parse_args()
    report_path = ROOT / f'reports/training/{args.report_id}_diagnostic.json'
    output_path = ROOT / f'outputs/metrics/{args.report_id}_diagnostic_outputs.json'
    if report_path.exists() or output_path.exists():
        raise ValueError('Diagnostic ID already exists')
    state = read_checkpoint(args.checkpoint)
    tokenizer = Tokenizer.from_file(str(ROOT / state['config']['tokenizer']))
    model = MiniGPT(state['model_config']).cuda().eval()
    load_checkpoint(args.checkpoint, model, None, None, restore_rng=False)
    records = []
    config = {'precision': 'bf16', 'seed': 42, 'temperature': 0, 'max_new_tokens': 768}
    for split in ('train', 'validation'):
        for row in read_jsonl(ROOT / f'data/processed/sft/{split}.jsonl'):
            target = json.dumps(row['target_spec'], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            ids, labels = encode_sft(row['prompt'], target, tokenizer, model.config['block_size'])
            active = [i for i, value in enumerate(labels) if value != -100]
            start = active[0]
            prefix = [tokenizer.token_to_id('<bos>'), tokenizer.token_to_id('<prompt>')]
            prefix += tokenizer.encode(row['prompt'], add_special_tokens=False).ids + [tokenizer.token_to_id('<target>')]
            if ids[:start + 1] != prefix:
                raise ValueError('Training/generation prefix mismatch')
            with torch.no_grad(), _autocast(torch.device('cuda'), 'bf16'):
                logits = model(torch.tensor([ids], device='cuda'))[0].float()
                short = model(torch.tensor([prefix], device='cuda'))[0, -1].float()
            predicted = logits.argmax(dim=-1).cpu().tolist()
            top = torch.topk(short, 8)
            raw, stop, count = _generate(model, tokenizer, row['prompt'], config)
            assessed = assess_output(raw)
            records.append({'example_id': row['example_id'], 'split': split,
                'prefix_ids_match': True, 'prefix_logits_max_abs_diff': float((short - logits[start]).abs().max()),
                'target_first_token': tokenizer.decode([labels[start]]),
                'first_prediction': tokenizer.decode([int(short.argmax())]),
                'first_top8': [{'token': tokenizer.decode([int(i)]), 'logit': float(v)} for v, i in zip(top.values, top.indices)],
                'teacher_forced_correct': sum(predicted[i] == labels[i] for i in active), 'target_tokens': len(active),
                'parse_status': assessed['parse_status'], 'schema_valid': assessed['parsed_spec'] is not None,
                'stop_reason': stop, 'generated_tokens': count, 'raw_output': raw})
    write_manifest(output_path, records)
    report = {'checkpoint_sha256': checkpoint_sha256(args.checkpoint), 'step': state['global_step'],
        'scope': 'train and validation only; no pilot test used for development',
        'records': [{k: v for k, v in row.items() if k != 'raw_output'} for row in records],
        'hypothesis': '40 updates are insufficient for learning JSON target boundaries; check train fitting before expansion'}
    write_manifest(report_path, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
