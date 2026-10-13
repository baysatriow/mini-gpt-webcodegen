"""Audit existing raw model artifacts against the explicit prompt contract, without rerendering."""
import argparse
import json
from pathlib import Path

from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import assess_output
from src.evaluation.prompt_contract import assess_prompt_contract

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--runtime-dir', type=Path, action='append', default=[])
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists(): raise ValueError('Preserve earlier audit report')
    evidence = json.loads(args.evaluation.read_text(encoding='utf-8'))
    raw_file = ROOT / evidence['outputs_path']
    rows = json.loads(raw_file.read_text(encoding='utf-8'))
    results = []
    for row in rows:
        spec = assess_output(row['raw_output'])['parsed_spec']
        check = assess_prompt_contract(row['prompt'], spec) if spec else {'checked': False, 'errors': ['Invalid schema']}
        results.append({'example_id': row['example_id'], 'accepted': check['checked'] and not check['errors'], 'contract': check})
    runtime = []
    for directory in args.runtime_dir:
        prompt, raw = directory / 'prompt.txt', directory / 'raw_output.txt'
        spec = assess_output(raw.read_text(encoding='utf-8'))['parsed_spec']
        check = assess_prompt_contract(prompt.read_text(encoding='utf-8'), spec) if spec else {'checked': False, 'errors': ['Invalid schema']}
        runtime.append({'directory': str(directory), 'raw_sha256': sha256_file(raw), 'prompt_sha256': sha256_file(prompt),
                        'historical_status': json.loads((directory / 'generation.json').read_text())['status'],
                        'contract_accepted_now': check['checked'] and not check['errors'], 'contract': check})
    report = {'evaluation_sha256': sha256_file(args.evaluation), 'raw_artifacts_sha256': sha256_file(raw_file),
              'final_count': len(results), 'final_contract_accepted': sum(r['accepted'] for r in results),
              'results': results, 'runtime': runtime, 'browser_evaluated': False,
              'limits': ['Artifact audit only; no new generation, no output repair, no browser/visual approval']}
    write_manifest(args.report, report)
    print(json.dumps({'final': [report['final_contract_accepted'], report['final_count']],
                      'runtime': [{'directory': r['directory'], 'accepted': r['contract_accepted_now'], 'errors': r['contract']['errors']} for r in runtime]}))


if __name__ == '__main__': main()
