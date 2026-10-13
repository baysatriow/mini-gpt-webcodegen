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
from src.data.integrity import reuse_tokenization
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
    directory = ROOT / cfg.get('dataset_dir', 'data/processed/curriculum/v1')
    manifest = verify_manifest(directory)
    summary = json.loads((ROOT / 'data/manifests/pipeline_summary.json').read_text(encoding='utf-8'))
    reuse_tokenization(ROOT, summary, summary['split'], json.loads((ROOT / 'configs/tokenizer.json').read_text()))
    cfg['model_config'] = json.loads((ROOT / cfg['model_config_path']).read_text())
    cfg['source_config_sha256'] = sha256_file(args.config)
    cfg['initial_checkpoint'] = str(args.initialize_from.resolve().relative_to(ROOT))
    cfg['initial_checkpoint_sha256'] = checkpoint_sha256(args.initialize_from)
    parent_state = read_checkpoint(args.initialize_from)
    indices = torch.randperm(manifest['counts']['validation']['rows'], generator=torch.Generator().manual_seed(59)).tolist()[:cfg['batch_size'] * cfg['validation_batches']]
    fingerprint = pretrain_descriptor(ROOT, summary)
    cfg['lineage'] = {'tokenizer_sha256': manifest['tokenizer_sha256'], 'pretrain_fingerprint': fingerprint,
        'synthetic_manifest_sha256': sha256_file(directory / 'manifest.json'),
        'data_sha256': {s: manifest['files'][s]['rows']['sha256'] for s in ('train', 'validation')},
        'validation_indices_sha256': hashlib.sha256(json.dumps(indices).encode()).hexdigest(),
        'train_blocks_or_examples': manifest['counts']['train']['rows'], 'validation_blocks_or_examples': len(indices),
        'smoke': False, 'human_reviewed': False,
        'pretraining_parent': {'checkpoint_sha256': cfg['initial_checkpoint_sha256'], 'phase': 'pretrain',
            'global_step': parent_state['global_step'], 'pretrain_fingerprint': fingerprint}}
    if cfg.get('curriculum_continuation', False):
        cfg['lineage']['pretraining_parent'] = parent_state['config']['lineage']['pretraining_parent']
        cfg['lineage']['curriculum_parent'] = {'checkpoint_sha256': cfg['initial_checkpoint_sha256'],
            'global_step': parent_state['global_step'],
            'synthetic_manifest_sha256': parent_state['config']['lineage']['synthetic_manifest_sha256'],
            'run_id': parent_state['run_id']}
    validate_initial_checkpoint(parent_state, cfg, ROOT, summary)
    weights_path = None
    if 'name_loss_weight' in cfg:
        weights = json.loads((directory / 'name_weights.json').read_text(encoding='utf-8'))
        weights_path = ROOT / weights['path']
        if (weights['name_weight'] != cfg['name_loss_weight'] or sha256_file(weights_path) != weights['sha256']
                or weights['train_sha256'] != manifest['files']['train']['rows']['sha256']):
            raise ValueError('Name-weight objective data changed')
        cfg['lineage']['name_loss_weights'] = weights
    pinned = cfg.get('performance', {}).get('pin_memory', False)
    train = DataLoader(CurriculumDataset(manifest, 'train', weights_path), batch_sampler=ResumableBatchSampler(manifest['counts']['train']['rows'], cfg['batch_size'], cfg['seed']), num_workers=0, pin_memory=pinned)
    development = DataLoader(Subset(CurriculumDataset(manifest, 'validation'), indices), batch_size=cfg['batch_size'], num_workers=0, pin_memory=pinned)
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
