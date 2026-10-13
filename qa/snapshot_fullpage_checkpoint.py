"""Save an immutable weights-only checkpoint for one approved comparison step."""
import argparse
import json
from pathlib import Path

from src.data.sources import sha256_file
from src.training.engine import checkpoint_sha256, read_checkpoint, save_checkpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--step', type=int, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    source = (root / args.source).resolve()
    destination = (root / args.destination).resolve()
    if not source.is_relative_to(root) or not destination.is_relative_to(root):
        parser.error('Checkpoint paths must stay inside --root')
    if not source.is_file() or destination.exists():
        raise FileExistsError('Source must exist and snapshot destination must be new')
    state = read_checkpoint(source)
    if state.get('weights_only') or state.get('run_id') != args.run_id or state.get('global_step') != args.step:
        raise ValueError('Snapshot source run or update does not match the frozen comparison')
    snapshot = {key: state[key] for key in ('run_id', 'global_step', 'config', 'model_config', 'model')}
    snapshot['weights_only'] = True
    snapshot['snapshot_parent'] = source.relative_to(root).as_posix()
    snapshot['snapshot_parent_sha256'] = checkpoint_sha256(source)
    save_checkpoint(destination, snapshot)
    result = {'source': source.relative_to(root).as_posix(), 'source_sha256': checkpoint_sha256(source),
              'destination': destination.relative_to(root).as_posix(),
              'destination_sha256': checkpoint_sha256(destination), 'destination_file_sha256': sha256_file(destination),
              'run_id': args.run_id, 'global_step': args.step, 'weights_only': True,
              'dataset_manifest_sha256': state['config'].get('lineage', {}).get('fullpage_manifest_sha256')}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
