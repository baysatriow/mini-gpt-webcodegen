"""Select only the two predeclared TRAIN-018 full-page development snapshots."""
import argparse
import hashlib
import json
from pathlib import Path

from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.fullpage.serialization import canonical
from src.training.engine import checkpoint_sha256, read_checkpoint


STEPS = (
    (1800, 'TRAIN-018', 'reports/training/TRAIN-018.json',
     'checkpoints/TRAIN-018/generation-1800.pt', 'reports/fullpage/TRAIN-018_DEVELOPMENT.json'),
    (3600, 'TRAIN-019', 'reports/training/TRAIN-019.json',
     'checkpoints/TRAIN-019/generation-3600.pt', 'reports/fullpage/TRAIN-019_DEVELOPMENT.json'),
)
SOURCE_FILES = ('src/fullpage/generation.py', 'src/fullpage/compose.py',
                'src/fullpage/contracts.py', 'src/fullpage/prompts.py')


def load(root, relative):
    return json.loads((root / relative).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', default='configs/fullpage/training-improvement-v2-r1.json')
    parser.add_argument('--selection', default='reports/fullpage/AI-019_DEVELOPMENT_SELECTION.json')
    parser.add_argument('--candidate', default='reports/fullpage/AI-019_LOCKED_CANDIDATE.json')
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = root / args.config
    config = load(root, args.config)
    if config['dataset_dir'] != 'data/processed/fullpage/v2' or config['max_steps'] != 3600:
        raise ValueError('Selection requires the frozen fullpage-v2 3600-update config')
    dataset_dir = root / config['dataset_dir']
    manifest = load(root, config['dataset_dir'] + '/manifest.json')
    request_path = dataset_dir / 'validation.requests.jsonl'
    if sha256_file(dataset_dir / 'manifest.json') != config['lineage']['fullpage_manifest_sha256']:
        raise ValueError('Dataset manifest differs from frozen training lineage')
    if sha256_file(request_path) != manifest['files']['validation.requests.jsonl']['sha256']:
        raise ValueError('Development request bytes differ from the frozen manifest')
    rows = list(read_jsonl(request_path))
    requests = [row['request'] for row in rows]
    request_identity = hashlib.sha256(canonical(requests).encode()).hexdigest()
    sources = {name: sha256_file(root / name) for name in SOURCE_FILES}
    if (root / 'data/evaluation/fullpage/final_consumption.json').exists():
        raise ValueError('Final benchmark must remain unopened during this improvement')
    selection_path = root / args.selection
    candidate_path = root / args.candidate
    if selection_path.exists() or candidate_path.exists():
        raise FileExistsError('Selection and candidate records are immutable and must be new')

    candidates = []
    resume_parent_sha256 = None
    for step, run_id, training_rel, checkpoint_rel, development_rel in STEPS:
        training = load(root, training_rel)
        checkpoint_path = root / checkpoint_rel
        state = read_checkpoint(checkpoint_path)
        development = load(root, development_rel)
        if training['config'] != config or training['config_sha256'] != sha256_file(config_path):
            raise ValueError(f'{run_id} training config differs from the frozen config')
        if training['global_step'] != step or training['last_committed_step'] != step:
            raise ValueError(f'{run_id} did not commit the required update {step}')
        expected_status = 'stopped_at_limit' if step == 1800 else 'completed'
        if training['status'] != expected_status:
            raise ValueError(f'{run_id} status differs from the predeclared phase')
        if state['run_id'] != run_id or state['global_step'] != step or not state.get('weights_only'):
            raise ValueError(f'{run_id} comparison checkpoint has the wrong identity or contains optimizer state')
        if state['config'] != config:
            raise ValueError(f'{run_id} comparison checkpoint training config changed')
        expected_parent_path = f'checkpoints/{run_id}/last.pt'
        if (training.get('final_checkpoint_sha256') != state.get('snapshot_parent_sha256')
                or state.get('snapshot_parent') != expected_parent_path):
            raise ValueError(f'{run_id} generation snapshot is not derived from its committed last checkpoint')
        if step == 3600:
            first_last = root / STEPS[0][3].replace('generation-1800.pt', 'last.pt')
            expected_parent = checkpoint_sha256(first_last)
            if training.get('resume_parent_sha256') != expected_parent:
                raise ValueError('3600-update phase did not resume exactly from the 1800-update checkpoint')
            resume_parent_sha256 = expected_parent
        digest = checkpoint_sha256(checkpoint_path)
        if (development['scope'] != 'development' or development['final_used']
                or development['total'] != 80 or development['checkpoint_sha256'] != digest
                or development['request_file_sha256'] != sha256_file(request_path)
                or development['request_file'] != request_path.relative_to(root).as_posix()
                or development['dataset_manifest_sha256'] != sha256_file(dataset_dir / 'manifest.json')
                or development['requests_sha256'] != request_identity
                or development['source_sha256'] != sources):
            raise ValueError(f'{run_id} development report is not bound to the frozen validation requests and renderer')
        output_path = Path(development['output']).resolve()
        if not output_path.is_relative_to(root) or not output_path.is_dir():
            raise ValueError(f'{run_id} development output is missing or outside the project')
        identity = load(root, output_path.relative_to(root).as_posix() + '/identity.json')
        if (identity.get('checkpoint_sha256') != digest or identity.get('requests_sha256') != request_identity
                or identity.get('count') != 80 or identity.get('source_sha256') != sources):
            raise ValueError(f'{run_id} generation output identity differs from its development report')
        loss = training['final_validation']['loss']
        candidates.append({'step': step, 'run_id': run_id, 'checkpoint': checkpoint_rel,
                           'checkpoint_sha256': digest, 'development_report': development_rel,
                           'development_report_sha256': sha256_file(root / development_rel),
                           'complete': development['complete'], 'total': development['total'],
                           'required_roles': development['required_roles'],
                           'first_attempt_complete': development['first_attempt_complete'],
                           'ordinary_validation_ce': loss, 'model_gate': bool(development['model_gate'])})

    selected = max(candidates, key=lambda row: (row['complete'], row['required_roles'],
                                                row['first_attempt_complete'], -row['ordinary_validation_ce'], -row['step']))
    gate = selected['complete'] >= 76 and selected['required_roles'] >= 76 and selected['model_gate']
    selection = {'status': 'candidate_ready' if gate else 'needs_additional_improvement',
                 'selection_rule': config['selection_rule'], 'candidates': candidates,
                 'selected_step': selected['step'], 'selected_run_id': selected['run_id'],
                 'selected_checkpoint': selected['checkpoint'], 'selected_checkpoint_sha256': selected['checkpoint_sha256'],
                 'development_complete': selected['complete'], 'development_total': selected['total'],
                 'development_required_roles': selected['required_roles'],
                 'development_first_attempt_complete': selected['first_attempt_complete'],
                 'development_gate_passed': gate, 'request_file_sha256': sha256_file(request_path),
                 'request_identity_sha256': request_identity, 'dataset_manifest_sha256': sha256_file(dataset_dir / 'manifest.json'),
                 'training_config_sha256': sha256_file(config_path), 'resume_parent_sha256': resume_parent_sha256,
                 'final_targets_read_for_selection': False, 'final_used': False,
                 'browser_status': 'pending', 'human_review_status': 'pending'}
    if gate:
        selection['candidate_lock'] = args.candidate
    selection_path.parent.mkdir(parents=True, exist_ok=True)
    with selection_path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(selection, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

    if gate:
        benchmark_manifest = root / 'data/evaluation/fullpage/manifest.json'
        candidate = {'status': 'locked', 'checkpoint': selected['checkpoint'],
                     'checkpoint_sha256': selected['checkpoint_sha256'],
                     'development_report_sha256': selected['development_report_sha256'],
                     'development_selection': args.selection,
                     'development_selection_sha256': sha256_file(selection_path),
                     'development_complete': selected['complete'],
                     'training_config': config,
                     'benchmark_manifest_sha256': sha256_file(benchmark_manifest),
                     'selection_rule': config['selection_rule'],
                     'final_targets_read_for_selection': False,
                     'final_evaluation_status': 'not_started'}
        with candidate_path.open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(candidate, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
    print(json.dumps(selection, indent=2))


if __name__ == '__main__':
    main()
