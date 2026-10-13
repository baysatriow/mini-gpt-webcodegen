"""Extend learned positions while preserving every existing project tensor."""
import hashlib
import json
import shutil
from pathlib import Path

import torch
from src.models.minigpt import MiniGPT
from src.training.engine import read_checkpoint, checkpoint_sha256, save_checkpoint
from src.fullpage.lineage import verify_source_ancestry
from src.fullpage.serialization import canonical

SOURCE_SHA = '3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638'


def extend_project_context(source, destination, *, root, seed=42):
    root, source, destination = Path(root).resolve(), Path(source).resolve(), Path(destination).resolve()
    if not source.is_relative_to(root / 'checkpoints') or not destination.is_relative_to(root / 'checkpoints'):
        raise ValueError('Checkpoint paths must stay inside this project')
    if destination.parent.exists():
        raise ValueError('Initialization directory exists; preserve prior results')
    if checkpoint_sha256(source) != SOURCE_SHA:
        raise ValueError('TRAIN-015 best checksum mismatch')
    parent = read_checkpoint(source)
    fingerprint = verify_source_ancestry(parent, root)
    old_cfg = parent['model_config']
    expected = {'block_size': 1024, 'vocab_size': 8192, 'n_embd': 384, 'n_layer': 6, 'n_head': 6}
    if any(old_cfg[k] != v for k, v in expected.items()):
        raise ValueError('Unexpected source architecture')
    if shutil.disk_usage(root).free < 15 * 2**30 + 160 * 2**20:
        raise OSError('Insufficient reserve for initialization and temporary write')
    torch.manual_seed(seed)
    expanded = MiniGPT({**old_cfg, 'block_size': 2048})
    copied = expanded.state_dict()
    equal_tensors = []
    for name, value in parent['model'].items():
        if name == 'position_embedding.weight':
            copied[name][:1024].copy_(value)
        else:
            if copied[name].shape != value.shape:
                raise ValueError('Unexpected tensor change: ' + name)
            copied[name].copy_(value)
        compare = copied[name][:1024] if name == 'position_embedding.weight' else copied[name]
        if not torch.equal(compare, value):
            raise ValueError('Copy changed tensor: ' + name)
        equal_tensors.append(name)
    expanded.load_state_dict(copied, strict=True)
    if expanded.lm_head.weight is not expanded.token_embedding.weight:
        raise ValueError('Weight tying lost')
    if not torch.isfinite(expanded.position_embedding.weight).all():
        raise ValueError('Nonfinite positional initialization')
    original = MiniGPT(old_cfg); original.load_state_dict(parent['model']); original.eval(); expanded.eval()
    probe = torch.arange(16, dtype=torch.long).reshape(1, -1)
    with torch.no_grad():
        deviation = float((original(probe) - expanded(probe)).abs().max())
    if deviation != 0:
        raise ValueError('Prefix logits changed during extension')
    lineage = {'migration_kind': 'position_extension', 'source_checkpoint_sha256': SOURCE_SHA,
               'source_config_sha256': hashlib.sha256(canonical(parent['config']).encode()).hexdigest(),
               'source_lineage': parent['config']['lineage'], 'pretrain_fingerprint': fingerprint,
               'tokenizer_sha256': parent['config']['lineage']['tokenizer_sha256'],
               'source_positions': 1024, 'target_positions': 2048, 'new_position_seed': seed,
               'new_position_distribution': 'normal mean0 std0.02', 'human_reviewed': False}
    state = {'format_version': 1, 'run_id': 'INIT-2048-001', 'global_step': 0,
             'model': expanded.state_dict(), 'model_config': expanded.config,
             'config': {'mode': 'initialization', 'data_origin': 'fullpage_initialization', 'lineage': lineage},
             'best_checkpoint': None}
    destination.parent.mkdir(parents=True, exist_ok=False)
    save_checkpoint(destination, state)
    digest = checkpoint_sha256(destination)
    if checkpoint_sha256(source) != SOURCE_SHA:
        raise ValueError('Source checkpoint changed')
    return {'status': 'completed', 'initialization_kind': 'weights_only_position_extension',
            'source_checkpoint_sha256': SOURCE_SHA, 'checkpoint': str(destination.relative_to(root)),
            'checkpoint_sha256': digest, 'model_config': expanded.config,
            'parameter_count': expanded.parameter_count(), 'unchanged_tensors': equal_tensors,
            'old_position_rows_identical': True, 'tied_embeddings': True,
            'prefix_logits_max_difference': deviation, 'optimizer_state_reused': False,
            'new_positions_trained': False, 'lineage': lineage, 'free_bytes': shutil.disk_usage(root).free}
