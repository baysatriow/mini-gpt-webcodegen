"""Launch a fresh curriculum process with its recorded allocator setting."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/training_gpu_optimized.json')
    parser.add_argument('--initialize-from', type=Path, required=True)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--stop-after', type=int)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    allocator = config.get('performance', {}).get('allocator_config', '')
    if allocator not in ('', 'expandable_segments:True'):
        raise ValueError('Unsupported allocator configuration')
    environment = dict(os.environ)
    if allocator:
        environment['PYTORCH_ALLOC_CONF'] = allocator
    command = [sys.executable, '-m', 'qa.train_curriculum', '--config', str(args.config),
               '--initialize-from', str(args.initialize_from)]
    if args.resume:
        command += ['--resume', str(args.resume)]
    if args.stop_after is not None:
        command += ['--stop-after', str(args.stop_after)]
    print(json.dumps({'allocator_config': environment.get('PYTORCH_ALLOC_CONF', ''),
                      'config': str(args.config), 'scope': 'child training process only'}), flush=True)
    return subprocess.call(command, cwd=ROOT, env=environment)


if __name__ == '__main__':
    raise SystemExit(main())
