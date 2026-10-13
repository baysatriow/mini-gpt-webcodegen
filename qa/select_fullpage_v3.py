"""Compare the sealed v3 development checkpoints without opening final data."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.data.sources import sha256_file
from src.fullpage.curriculum import write_json
from src.training.engine import checkpoint_sha256, read_checkpoint

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/fullpage/training-improvement-v3.json'
RUNS = (('TRAIN-020', 1800), ('TRAIN-021', 3600))


def role_counts(path):
    counts = Counter()
    task_counts = Counter()
    with Path(path).open(encoding='utf-8') as handle:
        for line in handle:
            row = json.loads(line)
            task_counts[row['task']] += 1
            if row['task'] == 'section_content':
                counts[json.loads(row['target']).get('role')] += 1
    return {'task_counts': dict(task_counts), 'section_role_rows': dict(sorted(counts.items()))}


def audit_output(output_path, checkpoint_digest):
    output = Path(output_path).resolve()
    if not output.is_relative_to(ROOT) or not output.is_dir():
        raise ValueError('Development output must exist inside the project root')
    identity = json.loads((output / 'identity.json').read_text(encoding='utf-8'))
    if identity['checkpoint_sha256'] != checkpoint_digest:
        raise ValueError('Development output identity differs from its checkpoint')

    statuses = Counter()
    error_attempts = Counter()
    error_pages = defaultdict(set)
    pages = 0
    for page in sorted(path for path in output.iterdir() if path.is_dir()):
        attempts = sorted(path for path in page.glob('attempt-*') if path.is_dir())
        if not attempts:
            continue
        attempt_dir = attempts[-1]
        result_path = attempt_dir / 'result.json'
        if not result_path.is_file():
            raise ValueError('Development page has no terminal result: ' + str(page))
        result = json.loads(result_path.read_text(encoding='utf-8'))
        pages += 1
        statuses[result['status']] += 1
        for path in attempt_dir.glob('attempt-*.json'):
            attempt = json.loads(path.read_text(encoding='utf-8'))
            for error in attempt.get('errors', []):
                key = (attempt.get('task'), attempt.get('stage'), error)
                error_attempts[key] += 1
                error_pages[key].add(result['request_id'])

    if pages != 80:
        raise ValueError(f'Expected all 80 development pages, found {pages}')
    ranked_errors = sorted(
        ({'task': key[0], 'stage': key[1], 'error': key[2],
          'attempts': count, 'affected_pages': len(error_pages[key])}
         for key, count in error_attempts.items()),
        key=lambda item: (-item['attempts'], -item['affected_pages'], item['stage'], item['error']),
    )
    return {'pages': pages, 'status_counts': dict(statuses), 'top_errors': ranked_errors[:12]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='reports/training/AI-020_DEVELOPMENT_SELECTION.json')
    args = parser.parse_args()
    destination = (ROOT / args.output).resolve()
    if not destination.is_relative_to(ROOT) or destination.exists():
        raise FileExistsError('Selection report path must be new and remain inside the project')

    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    dataset_dir = ROOT / config['dataset_dir']
    manifest_path = dataset_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('version') != 'fullpage-v3' or manifest.get('human_reviewed') is not False:
        raise ValueError('Expected the disclosed v3 synthetic curriculum')
    if config['lineage']['fullpage_manifest_sha256'] != sha256_file(manifest_path):
        raise ValueError('Frozen training config does not match the v3 dataset manifest')

    candidates = []
    for run_id, expected_step in RUNS:
        summary_path = ROOT / f'reports/training/{run_id}.json'
        evaluation_path = ROOT / f'reports/training/{run_id}_DEVELOPMENT.json'
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        evaluation = json.loads(evaluation_path.read_text(encoding='utf-8'))
        checkpoint = ROOT / f'checkpoints/FULLPAGE-V3/{run_id}-step{expected_step}.pt'
        state = read_checkpoint(checkpoint)
        digest = checkpoint_sha256(checkpoint)

        if state.get('run_id') != run_id or state.get('global_step') != expected_step or not state.get('weights_only'):
            raise ValueError('Candidate snapshot identity or step is invalid: ' + run_id)
        if state.get('config') != config or summary.get('config') != config:
            raise ValueError('Candidate training config differs from the frozen v3 config: ' + run_id)
        if summary.get('global_step') != expected_step or summary.get('config_sha256') != sha256_file(CONFIG):
            raise ValueError('Training summary step/config checksum mismatch: ' + run_id)
        if evaluation.get('scope') != 'development' or evaluation.get('final_used') is not False:
            raise ValueError('Candidate evaluation is not development-only: ' + run_id)
        if evaluation.get('total') != 80 or evaluation.get('checkpoint_sha256') != digest:
            raise ValueError('Development report count/checkpoint mismatch: ' + run_id)
        if evaluation.get('request_file_sha256') != manifest['files']['validation.requests.jsonl']['sha256']:
            raise ValueError('Candidate did not use the frozen development requests: ' + run_id)
        if evaluation.get('dataset_manifest_sha256') != sha256_file(manifest_path):
            raise ValueError('Development report dataset lineage mismatch: ' + run_id)

        failures = audit_output(ROOT / evaluation['output'], digest)
        candidates.append({
            'run_id': run_id,
            'step': expected_step,
            'checkpoint': checkpoint.relative_to(ROOT).as_posix(),
            'checkpoint_sha256': digest,
            'training_status': summary['status'],
            'development_complete': evaluation['complete'],
            'development_total': evaluation['total'],
            'required_roles': evaluation['required_roles'],
            'model_gate': evaluation['model_gate'],
            'development_ce': summary['final_validation']['loss'],
            'page_status_counts': failures['status_counts'],
            'top_generation_errors': failures['top_errors'],
        })

    baseline_summary = json.loads((ROOT / 'reports/training/TRAIN-019.json').read_text(encoding='utf-8'))
    baseline_evaluation = json.loads((ROOT / 'reports/fullpage/TRAIN-019_DEVELOPMENT.json').read_text(encoding='utf-8'))
    if baseline_evaluation['request_file_sha256'] != manifest['files']['validation.requests.jsonl']['sha256']:
        raise ValueError('Baseline did not use the unchanged development request file')

    ordered = sorted(candidates, key=lambda item: (-item['development_complete'], item['development_ce'], item['step']))
    passing = [item for item in candidates if item['model_gate']]
    v2 = role_counts(ROOT / 'data/processed/fullpage/v2/train.jsonl')
    v3 = role_counts(dataset_dir / 'train.jsonl')
    report = {
        'experiment': 'fullpage-targeted-identity-facts-v3',
        'dataset_manifest_sha256': sha256_file(manifest_path),
        'development_request_sha256': manifest['files']['validation.requests.jsonl']['sha256'],
        'baseline': {
            'run_id': 'TRAIN-019',
            'step': baseline_summary['global_step'],
            'plan_batch_probability': baseline_summary['config'].get('plan_batch_probability'),
            'development_complete': baseline_evaluation['complete'],
            'development_total': baseline_evaluation['total'],
            'development_ce': baseline_summary['final_validation']['loss'],
        },
        'training_ratio_note': 'TRAIN-019 and both v3 candidates use plan_batch_probability=0.7; the v3 data augmentation changed role exposure, not this sampler ratio.',
        'training_role_rows': {'v2': v2, 'v3': v3},
        'candidates': candidates,
        'best_observed_by_complete_pages_then_ce': ordered[0]['run_id'],
        'best_observed_step': ordered[0]['step'],
        'model_gate_passed': bool(passing),
        'promotable_candidate': passing[0]['run_id'] if passing else None,
        'target': {'minimum_complete_pages': 76, 'pages': 80, 'rate': 0.95},
        'final_opened': False,
        'final_used': False,
        'browser_reviewed': False,
        'human_reviewed': False,
        'limits': [
            'Programmatic staged generation and strict contracts only; no browser or visual approval.',
            'All training examples are synthetic and not human reviewed.',
            'Neither development checkpoint passed the 95 percent model gate.',
        ],
    }
    write_json(destination, report)
    print(json.dumps({
        'report': destination.relative_to(ROOT).as_posix(),
        'baseline': [report['baseline']['development_complete'], report['baseline']['development_total']],
        'candidates': [[item['run_id'], item['development_complete'], item['development_total'], item['development_ce']] for item in candidates],
        'best_observed': report['best_observed_by_complete_pages_then_ce'],
        'promotable_candidate': report['promotable_candidate'],
        'final_opened': False,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
