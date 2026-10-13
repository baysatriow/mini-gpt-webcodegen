"""Explicit checks for project-owned context extension and full-page training."""
import json
from pathlib import Path
from src.data.sources import sha256_file
from src.training.lineage import pretrain_descriptor


def verify_source_ancestry(parent, root):
    root = Path(root)
    lineage = parent['config']['lineage']
    summary = json.loads((root / 'data/manifests/pipeline_summary.json').read_text(encoding='utf-8'))
    fingerprint = pretrain_descriptor(root, summary)
    if lineage.get('pretrain_fingerprint') != fingerprint or lineage.get('tokenizer_sha256') != sha256_file(root / 'data/tokenizer/tokenizer.json'):
        raise ValueError('Project pretraining/tokenizer ancestry mismatch')
    if parent['config'].get('data_origin') != 'synthetic_curriculum' or parent['global_step'] < 1:
        raise ValueError('Extension requires a trained project synthetic checkpoint')
    from src.data.curriculum import verify_manifest
    directory = root / parent['config']['dataset_dir']
    verify_manifest(directory)
    if sha256_file(directory / 'manifest.json') != lineage['synthetic_manifest_sha256']:
        raise ValueError('Source curriculum manifest changed')
    return fingerprint


def validate_fullpage_parent(parent, config, root):
    lineage = parent['config']['lineage']
    if parent.get('global_step') != 0 or lineage.get('migration_kind') != 'position_extension':
        raise ValueError('Full-page initialization needs an explicit position extension')
    if parent['model_config'] != config['model_config'] or parent['model_config']['block_size'] != 2048:
        raise ValueError('Extended model configuration mismatch')
    if config.get('data_origin') != 'fullpage_curriculum' or config.get('human_reviewed') is not False:
        raise ValueError('Full-page synthetic origin must be disclosed')
    current = sha256_file(Path(root) / 'data/tokenizer/tokenizer.json')
    if lineage['tokenizer_sha256'] != current or config['lineage']['tokenizer_sha256'] != current:
        raise ValueError('Extended tokenizer checksum mismatch')
    if config['lineage']['initialization_parent'] != lineage:
        raise ValueError('Extension ancestry changed')
    if lineage['source_checkpoint_sha256'] != '3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638':
        raise ValueError('Unexpected source checkpoint')
