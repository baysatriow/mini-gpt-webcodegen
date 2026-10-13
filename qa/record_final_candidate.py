"""Record the predeclared development-selected candidate before one locked final evaluation."""
import argparse
import json
from datetime import datetime, timezone

from src.data.curriculum import ROOT, verify_manifest
from src.data.sources import sha256_file, write_manifest
from src.training.engine import checkpoint_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    run = args.run_id
    output = ROOT / f'reports/training/{run}_FINAL_SELECTION.json'
    final_report = ROOT / f'reports/training/{run}-FINAL_curriculum_evaluation.json'
    if output.exists() or final_report.exists(): raise ValueError('Candidate selection must precede final and be immutable')
    read = lambda path: json.loads((ROOT / path).read_text(encoding='utf-8'))
    training = read(f'reports/training/{run}.json')
    development = read(f'reports/training/{run}-DEV_curriculum_evaluation.json')
    if training['status'] != 'completed' or training['global_step'] != training['config']['max_steps']:
        raise ValueError('Requires completed fixed training budget')
    sha = checkpoint_sha256(ROOT / f'checkpoints/{run}/best.pt')
    if development['split'] != 'validation' or development['checkpoint_sha256'] != sha or training['best_checkpoint_sha256'] != sha:
        raise ValueError('Validation-selected checkpoint mismatch')
    if (training['best_validation_loss'] >= training['initial_validation']['loss']
            or development['schema_valid_rate'] < .95 or development['exact_contract_rate'] < .90):
        raise ValueError('Predeclared development criteria failed; do not open final')
    manifest = verify_manifest(ROOT / training['config']['dataset_dir'])
    policy = ROOT / 'docs/superpowers/plans/2026-10-13-copying-quality-continuation.md'
    selection = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'run_id': run,
        'checkpoint': f'checkpoints/{run}/best.pt', 'checkpoint_sha256': sha,
        'selected_by': 'best full validation ordinary CE after fixed budget; development generation gate',
        'training_report_sha256': sha256_file(ROOT / f'reports/training/{run}.json'),
        'development_report_sha256': sha256_file(ROOT / f'reports/training/{run}-DEV_curriculum_evaluation.json'),
        'policy_sha256': sha256_file(policy), 'final_suite': manifest['final_suite'],
        'acceptance': manifest['acceptance'], 'decode': development['decode_config'],
        'final_targets_read_for_selection': False, 'final_report_id': f'{run}-FINAL',
        'rule_after_final': 'Record pass/failure once; no checkpoint reselection or retraining from this final result',
        'limits': ['Controlled synthetic recipes only; not arbitrary prompt or browser acceptance']}
    write_manifest(output, selection)
    print(json.dumps(selection, indent=2))


if __name__ == '__main__': main()
