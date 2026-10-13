"""Diagnose development copying errors using training exposure, never final targets."""
import argparse
from collections import Counter
import json
from pathlib import Path

from tokenizers import Tokenizer
from src.data.curriculum import ROOT, serialize_spec, verify_manifest
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file, write_manifest


def differences(expected, actual, path='$'):
    if type(expected) is not type(actual):
        return [{'path': path, 'expected': expected, 'actual': actual}]
    if isinstance(expected, dict):
        result = []
        for key in sorted(expected.keys() | actual.keys()):
            if key not in expected or key not in actual:
                result.append({'path': f'{path}.{key}', 'expected': expected.get(key), 'actual': actual.get(key)})
            else:
                result.extend(differences(expected[key], actual[key], f'{path}.{key}'))
        return result
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [{'path': path, 'expected': expected, 'actual': actual}]
        return [item for index, (left, right) in enumerate(zip(expected, actual))
                for item in differences(left, right, f'{path}[{index}]')]
    return [] if expected == actual else [{'path': path, 'expected': expected, 'actual': actual}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir', type=Path, required=True)
    parser.add_argument('--evaluations', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('Preserve existing diagnostics')
    manifest = verify_manifest(args.dataset_dir)
    tokenizer = Tokenizer.from_file(str(ROOT / 'data/tokenizer/tokenizer.json'))
    title_counts, title_row_counts = Counter(), Counter()
    for row in read_jsonl(ROOT / manifest['files']['train']['rows']['path']):
        ids = tokenizer.encode(row['target_spec']['title']).ids
        title_counts.update(ids); title_row_counts.update(set(ids))
    development = {r['example_id']: r for r in read_jsonl(ROOT / manifest['files']['validation']['rows']['path'])}
    diagnostics = []
    for path in args.evaluations:
        evaluation = json.loads(path.read_text(encoding='utf-8'))
        if evaluation['split'] != 'validation': raise ValueError('Development diagnostics only')
        rows_path = ROOT / evaluation['outputs_path']
        if sha256_file(rows_path) != evaluation['outputs_sha256']: raise ValueError('Evaluation output changed')
        failures = []
        for row in json.loads(rows_path.read_text(encoding='utf-8')):
            source = development.get(row['example_id'])
            if source is None or source['target_spec'] != row['target_spec'] or source['prompt'] != row['prompt']:
                raise ValueError('Development membership changed')
            if row['exact_contract']: continue
            name = row['target_spec']['title']
            ids = tokenizer.encode(name).ids
            expected = tokenizer.encode(serialize_spec(row['target_spec'], manifest['serialization'])).ids
            actual = tokenizer.encode(row['raw_output']).ids
            first = next((i for i, (left, right) in enumerate(zip(expected, actual)) if left != right), min(len(expected), len(actual)))
            failures.append({'example_id': row['example_id'], 'recipe': row['recipe'], 'expected_name': name,
                'schema_valid': row['parsed_spec'] is not None,
                'differences': differences(row['target_spec'], row['parsed_spec']),
                'first_target_token_divergence': first,
                'expected_token': tokenizer.decode(expected[first:first+1]),
                'actual_token': tokenizer.decode(actual[first:first+1]),
                'name_piece_train_exposure': [{'id': i, 'piece': tokenizer.decode([i]),
                    'occurrences': title_counts[i], 'train_rows': title_row_counts[i]} for i in ids]})
        diagnostics.append({'evaluation': str(path.resolve().relative_to(ROOT)), 'checkpoint_sha256': evaluation['checkpoint_sha256'],
            'checkpoint_step': evaluation['checkpoint_step'], 'schema_valid': evaluation['schema_valid'],
            'exact_contract': evaluation['exact_contract'], 'count': evaluation['count'], 'failures': failures})
    result = {'dataset_manifest_sha256': sha256_file(args.dataset_dir / 'manifest.json'),
        'train_rows': manifest['counts']['train']['rows'], 'development': diagnostics,
        'policy': 'Only train and validation rows read; test/final files hashed for integrity but never parsed',
        'limits': ['Token exposure suggests a data imbalance; it does not prove causality or visual quality']}
    write_manifest(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
