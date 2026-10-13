"""Train a disclosed synthetic curriculum with unchanged model and verified pretrain parent."""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset

from qa.train_minigpt import next_run_id
from src.data.curriculum import CurriculumDataset, DIRECTORY, verify_manifest
from src.data.sources import sha256_file, write_manifest
from src.training.engine import ResumableBatchSampler, checkpoint_sha256, read_checkpoint, run_training
from src.training.lineage import pretrain_descriptor, validate_initial_checkpoint

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/training_curriculum.json')
    parser.add_argument('--initialize-from', type=Path, required=True)
    parser.add_argument('--stop-after', type=int)
    parser.add_argument('--resume', type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    if cfg['data_origin'] != 'synthetic_curriculum' or cfg['human_reviewed'] is not False:
        raise ValueError('Curriculum origin must remain explicit')
    manifest = verify_manifest()
    summary = json.loads((ROOT / 'data/manifests/pipeline_summary.json').read_text(encoding='utf-8'))
    cfg['model_config'] = json.loads((ROOT / cfg['model_config_path']).read_text())
    cfg['source_config_sha256'] = sha256_file(args.config)
    cfg['initial_checkpoint'] = str(args.initialize_from.resolve().relative_to(ROOT))
    cfg['initial_checkpoint_sha256'] = checkpoint_sha256(args.initialize_from)
    indices = torch.randperm(manifest['counts']['validation']['rows'], generator=torch.Generator().manual_seed(59)).tolist()[:cfg['batch_size'] * cfg['validation_batches']]
    fingerprint = pretrain_descriptor(ROOT, summary)
    cfg['lineage'] = {'tokenizer_sha256': manifest['tokenizer_sha256'], 'pretrain_fingerprint': fingerprint,
        'synthetic_manifest_sha256': sha256_file(DIRECTORY / 'manifest.json'),
        'data_sha256': {s: manifest['files'][s]['rows']['sha256'] for s in ('train', 'validation')},
        'validation_indices_sha256': hashlib.sha256(json.dumps(indices).encode()).hexdigest(),
        'train_blocks_or_examples': manifest['counts']['train']['rows'], 'validation_blocks_or_examples': len(indices),
        'smoke': False, 'human_reviewed': False,
        'pretraining_parent': {'checkpoint_sha256': cfg['initial_checkpoint_sha256'], 'phase': 'pretrain',
            'global_step': read_checkpoint(args.initialize_from)['global_step'], 'pretrain_fingerprint': fingerprint}}
    validate_initial_checkpoint(read_checkpoint(args.initialize_from), cfg, ROOT, summary)
    train = DataLoader(CurriculumDataset(manifest, 'train'), batch_sampler=ResumableBatchSampler(manifest['counts']['train']['rows'], cfg['batch_size'], cfg['seed']), num_workers=0)
    development = DataLoader(Subset(CurriculumDataset(manifest, 'validation'), indices), batch_size=cfg['batch_size'], num_workers=0)
    run_id = next_run_id()
    runtime = ROOT / f'configs/.{run_id}.json'
    write_manifest(runtime, cfg)
    checkpoint = run_training(runtime, train, development, run_id, stop_after=args.stop_after, resume=args.resume)
    report_path = ROOT / f'reports/training/{run_id}.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report['environment'] = {'python': sys.version, 'executable': sys.executable, 'torch': torch.__version__,
                             'cuda': torch.version.cuda, 'gpu': torch.cuda.get_device_name(), 'platform': platform.platform()}
    report['data_review_kind'] = 'programmatic_contract, not human-reviewed production annotations'
    write_manifest(report_path, report)
    print(json.dumps({'run_id': run_id, 'status': report['status'], 'checkpoint': str(checkpoint.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
