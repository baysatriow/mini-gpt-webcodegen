"""Record the attention operators actually used by a real train-only update."""
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from src.data.curriculum import CurriculumDataset, verify_manifest
from src.data.sources import write_manifest
from src.models.minigpt import MiniGPT
from src.training.engine import read_checkpoint, train_one_step

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / 'reports/training/GPU-PERF-001_attention_operators.json'
    if destination.exists():
        raise ValueError('Operator report already exists')
    parent = read_checkpoint(ROOT / 'checkpoints/TRAIN-012/best.pt')
    model = MiniGPT(parent['model_config']).cuda()
    model.load_state_dict(parent['model'])
    model.set_attention_backend('sdpa')
    model.supervised_only_logits = True
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5, fused=True)
    manifest = verify_manifest(ROOT / 'data/processed/curriculum/v5')
    batch = next(iter(DataLoader(CurriculumDataset(manifest, 'train'), batch_size=4)))
    train_one_step(model, batch, optimizer, None, 'sft', precision='bf16')
    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,
                                            torch.profiler.ProfilerActivity.CUDA]) as profile:
        metrics = train_one_step(model, batch, optimizer, None, 'sft', precision='bf16')
        torch.cuda.synchronize()
    operators = [{'name': event.key, 'calls': event.count} for event in profile.key_averages()
                 if any(word in event.key.lower() for word in ('attention', 'sdp', 'flash', 'adam'))]
    result = {'kind': 'operator profiling on train only; discarded weights', 'operators': operators,
              'update': metrics, 'torch': torch.__version__, 'gpu': torch.cuda.get_device_name()}
    write_manifest(destination, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
