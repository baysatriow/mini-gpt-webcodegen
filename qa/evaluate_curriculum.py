"""Evaluate unchanged raw model output on disclosed synthetic development or locked final data."""
import argparse
import json
import re
from pathlib import Path

import torch
from tokenizers import Tokenizer
from torch.utils.data import DataLoader

from qa.prepare_annotation_review import local_link_findings
from src.data.curriculum import ROOT, DIRECTORY, RECIPES, CurriculumDataset, verify_manifest
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import _generate, assess_output
from src.models.minigpt import MiniGPT
from src.training.engine import checkpoint_sha256, evaluate_tokens, load_checkpoint, read_checkpoint
from src.training.lineage import pretrain_descriptor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--split', choices=('validation', 'final'), default='validation')
    parser.add_argument('--report-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]{1,80}', args.report_id): raise ValueError('Invalid report ID')
    report_path = ROOT / f'reports/training/{args.report_id}_curriculum_evaluation.json'
    outputs_path = ROOT / f'outputs/metrics/{args.report_id}_curriculum_outputs.json'
    if report_path.exists() or outputs_path.exists(): raise ValueError('Report already exists')
    manifest = verify_manifest()
    state = read_checkpoint(args.checkpoint)
    lineage = state['config']['lineage']
    summary = json.loads((ROOT / 'data/manifests/pipeline_summary.json').read_text(encoding='utf-8'))
    if state['config'].get('data_origin') != 'synthetic_curriculum' or lineage['human_reviewed'] is not False:
        raise ValueError('Requires a disclosed synthetic checkpoint')
    if lineage['synthetic_manifest_sha256'] != sha256_file(DIRECTORY / 'manifest.json'):
        raise ValueError('Curriculum lineage changed')
    fingerprint = pretrain_descriptor(ROOT, summary)
    parent = lineage['pretraining_parent']
    if lineage['pretrain_fingerprint'] != fingerprint or parent['pretrain_fingerprint'] != fingerprint or parent['phase'] != 'pretrain' or parent['global_step'] < 1:
        raise ValueError('Pretraining ancestry changed')
    if args.split == 'final':
        if state['global_step'] < state['config']['max_steps']:
            raise ValueError('Locked final suite requires the predeclared training budget to finish')
        final = manifest['final_suite']
        path = ROOT / final['path']
        if sha256_file(path) != final['sha256']: raise ValueError('Locked final suite changed')
        rows = list(read_jsonl(path))
        actual = {r['example_id']: r for r in read_jsonl(DIRECTORY / 'test.jsonl')}
        if len(rows) != final['count'] or any(actual.get(r['example_id']) != r for r in rows):
            raise ValueError('Final prompt membership changed')
        split = 'test'
    else:
        path = DIRECTORY / 'validation.jsonl'
        all_rows = list(read_jsonl(path))
        rows = [next(r for r in all_rows if r['recipe'] == recipe and r['target_spec']['style_mode'] == style)
                for recipe in RECIPES for style in ('plain_css', 'tailwind')]
        split = 'validation'
    tokenizer = Tokenizer.from_file(str(ROOT / state['config']['tokenizer']))
    model = MiniGPT(state['model_config']).cuda().eval()
    load_checkpoint(args.checkpoint, model, None, None, restore_rng=False)
    token_metrics = evaluate_tokens(model, DataLoader(CurriculumDataset(manifest, split), batch_size=4, num_workers=0), precision='bf16')
    config = {'precision': 'bf16', 'temperature': 0, 'seed': 42, 'max_new_tokens': 768}
    records = []
    for index, row in enumerate(rows):
        raw, stop, count = _generate(model, tokenizer, row['prompt'], config)
        parsed = assess_output(raw)
        spec = parsed['parsed_spec']
        records.append({**row, 'raw_output': raw, **parsed, 'stop_reason': stop, 'generated_tokens': count,
            'exact_contract': spec == row['target_spec'],
            'resolved_links': spec is not None and not local_link_findings(spec)})
        print(json.dumps({'example': index + 1, 'count': len(rows), 'recipe': row['recipe'],
            'schema_valid': spec is not None, 'exact_contract': spec == row['target_spec'], 'stop': stop}), flush=True)
    write_manifest(outputs_path, records)
    valid = sum(r['parsed_spec'] is not None for r in records)
    exact = sum(r['exact_contract'] for r in records)
    report = {'checkpoint_sha256': checkpoint_sha256(args.checkpoint), 'checkpoint_step': state['global_step'],
        'split': args.split, 'prompt_file_sha256': sha256_file(path), 'token_metrics': token_metrics,
        'count': len(rows), 'parseable': sum(r['parse_status'] == 'passed' for r in records),
        'schema_valid': valid, 'exact_contract': exact, 'schema_valid_rate': valid / len(rows),
        'exact_contract_rate': exact / len(rows), 'resolved_links': sum(r['resolved_links'] for r in records),
        'all_ended_eos': all(r['stop_reason'] == 'eos' for r in records), 'decode_config': config,
        'acceptance_fixed_before_training': manifest['acceptance'],
        'contract_gate_passed': valid / len(rows) >= .95 and exact / len(rows) >= .90,
        'review_kind': 'programmatic_contract, not human-reviewed production SFT',
        'outputs_path': str(outputs_path.relative_to(ROOT)),
        'limits': ['Shared synthetic component recipes across partitions; fictional title families held out',
                   'No JSON repair or forced first token', 'No browser/manual acceptance',
                   'No claim of arbitrary real-world prompts or unseen layout-family generalization']}
    write_manifest(report_path, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
