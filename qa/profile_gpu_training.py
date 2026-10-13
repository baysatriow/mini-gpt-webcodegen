"""Measure real train-only update throughput in isolated CUDA processes, without retaining weights."""
import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from src.data.curriculum import CurriculumDataset, verify_manifest
from src.data.sources import write_manifest, sha256_file
from src.models.minigpt import MiniGPT
from src.training.engine import ResumableBatchSampler, read_checkpoint, seed_everything, train_one_step
from src.training.performance import GpuMonitor

ROOT = Path(__file__).resolve().parents[1]


def inventory(path):
    properties = torch.cuda.get_device_properties(0)
    report = {'python': sys.version, 'interpreter': sys.executable, 'torch': torch.__version__,
              'cuda': torch.version.cuda, 'gpu': properties.name, 'vram_bytes': properties.total_memory,
              'cuda_available': torch.cuda.is_available(), 'bf16': torch.cuda.is_bf16_supported(),
              'capability': list(torch.cuda.get_device_capability()), 'platform': platform.platform(),
              'disk_free_bytes': shutil.disk_usage(ROOT).free,
              'nvidia_smi': subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu,power.draw,power.limit,temperature.gpu', '--format=csv'], text=True)}
    write_manifest(path, report)
    print(json.dumps(report, indent=2))


def probe(args):
    output = ROOT / 'outputs/gpu_profile' / args.report_id / f'{args.case}.json'
    if output.exists():
        raise ValueError('Probe output already exists')
    report = {'case': args.case, 'batch_size': args.batch, 'accumulation': args.accumulation,
              'attention_backend': args.backend, 'fused_adamw': args.fused,
              'supervised_only_logits': args.packed,
              'allocator_config': os.environ.get('PYTORCH_ALLOC_CONF', ''),
              'precision': 'bf16', 'context': 1024, 'status': 'running',
              'kind': 'discarded performance probe on train only, not quality evaluation',
              'warmup_updates': 6, 'measured_updates': args.steps}
    monitor = None
    try:
        seed_everything(42)
        dataset_dir = (ROOT / args.dataset_dir).resolve()
        dataset_dir.relative_to(ROOT / 'data/processed/curriculum')
        manifest = verify_manifest(dataset_dir)
        report['dataset_dir'] = str(dataset_dir.relative_to(ROOT))
        report['dataset_manifest_sha256'] = sha256_file(dataset_dir / 'manifest.json')
        parent = read_checkpoint(ROOT / 'checkpoints/TRAIN-012/best.pt')
        model = MiniGPT(parent['model_config']).cuda()
        model.load_state_dict(parent['model'])
        del parent
        model.set_attention_backend(args.backend)
        model.supervised_only_logits = args.packed
        torch.backends.cuda.matmul.allow_tf32 = args.fused
        torch.backends.cudnn.allow_tf32 = args.fused
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5, betas=(0.9, 0.95),
                                      weight_decay=.1, **({'fused': True} if args.fused else {}))
        loader = DataLoader(CurriculumDataset(manifest, 'train'),
            batch_sampler=ResumableBatchSampler(manifest['counts']['train']['rows'], args.batch, 42),
            num_workers=0, pin_memory=args.fused)
        iterator = iter(loader)
        torch.cuda.reset_peak_memory_stats()
        durations, counts, norms, losses = [], [], [], []
        for step in range(6 + args.steps):
            if step == 6:
                monitor = GpuMonitor(output.with_suffix('.telemetry.jsonl')).start()
            started = time.perf_counter()
            batches = [next(iterator) for _ in range(args.accumulation)]
            metrics = train_one_step(model, batches, optimizer, None, 'sft', precision='bf16')
            torch.cuda.synchronize()
            if step >= 6:
                durations.append(time.perf_counter() - started)
                counts.append(metrics['valid_tokens'])
                norms.append(metrics['grad_norm'])
                losses.append(metrics['loss'])
        report.update(status='completed', seconds=sum(durations),
            seconds_per_update=statistics.mean(durations), target_tokens_per_second=sum(counts)/sum(durations),
            input_tokens_per_second=args.steps * args.batch * args.accumulation * 1024 / sum(durations),
            examples_per_second=args.steps * args.batch * args.accumulation / sum(durations),
            peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            free_vram_bytes=torch.cuda.mem_get_info()[0], max_grad_norm=max(norms), last_loss=losses[-1],
            update_seconds=durations, supervised_tokens=counts)
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error))
    finally:
        if monitor is not None:
            report['telemetry'] = monitor.finish()
        write_manifest(output, report)
        print(json.dumps({k:v for k,v in report.items() if k not in {'update_seconds','supervised_tokens'}}, indent=2), flush=True)
    return 0 if report['status'] == 'completed' else 2


def sweep(args):
    output = ROOT / 'reports/training' / f'{args.report_id}.json'
    if output.exists():
        raise ValueError('Performance report already exists')
    cases = [('manual_b4_a2', 4, 2, 'manual', False),
             ('sdpa_b4_a2', 4, 2, 'sdpa', True),
             ('sdpa_b8_a1', 8, 1, 'sdpa', True)]
    cases += [(f'sdpa_b{batch}_a1', batch, 1, 'sdpa', True) for batch in (16, 24, 32, 48, 64)]
    if args.confirm:
        cases = [cases[0]] + [case for case in cases if case[1] in (24, 32)]
    if args.packed:
        cases = [cases[0]] + [(f'packed_b{b}_a1', b, 1, 'sdpa', True) for b in (24,32,48,64,80)]
    records = []
    for case, batch, accumulation, backend, fused in cases:
        command = [sys.executable, '-m', 'qa.profile_gpu_training', '--probe', '--report-id', args.report_id,
                   '--dataset-dir', args.dataset_dir,
                   '--case', case, '--batch', str(batch), '--accumulation', str(accumulation),
                   '--backend', backend, '--steps', str(args.steps)] + (['--fused'] if fused else [])
        if args.packed and backend == 'sdpa':
            command.append('--packed')
        print(f'Performance probe: {case}', flush=True)
        environment = dict(os.environ)
        if args.expandable_segments:
            environment['PYTORCH_ALLOC_CONF'] = 'expandable_segments:True'
        result = subprocess.run(command, cwd=ROOT, env=environment)
        path = ROOT / f'outputs/gpu_profile/{args.report_id}/{case}.json'
        record = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'case': case, 'status': 'failed', 'process_exit': result.returncode}
        records.append(record)
        write_manifest(output, {'status': 'running', 'cases': records})
        if record['status'] != 'completed' and backend == 'sdpa':
            break
        if batch >= 16 and record.get('free_vram_bytes', 0) < 1.5 * 1024**3:
            print('Stop batch growth: retain desktop/allocator memory headroom', flush=True)
            break
    eligible = [r for r in records if r['status'] == 'completed' and r['attention_backend'] == 'sdpa'
                and r['free_vram_bytes'] >= 1024**3]
    selected = max(eligible, key=lambda r:r['target_tokens_per_second']) if eligible else None
    baseline = records[0]
    report = {'status': 'completed', 'cases': records, 'selected': selected,
              'speedup_vs_current': selected['target_tokens_per_second']/baseline['target_tokens_per_second'] if selected and baseline['status']=='completed' else None,
              'selection': 'highest measured supervised-token throughput with at least 1GiB remaining VRAM',
              'limits': ['Short train-only discarded updates, not model quality',
                         'Batch and AdamW/attention change numerical trajectory',
                         'No power, clock, driver, or BIOS changes', 'Desktop load may vary']}
    write_manifest(output, report)
    print(json.dumps({'selected': selected['case'] if selected else None,
                      'speedup': report['speedup_vs_current'], 'report': str(output)}, indent=2))
    return 0 if selected else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-id', default='GPU-PERF-001')
    parser.add_argument('--dataset-dir', default='data/processed/curriculum/v5')
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--case')
    parser.add_argument('--batch', type=int, default=4)
    parser.add_argument('--accumulation', type=int, default=2)
    parser.add_argument('--backend', choices=('manual','sdpa'), default='manual')
    parser.add_argument('--fused', action='store_true')
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--confirm', action='store_true', help='Longer comparison of baseline and top safe batches')
    parser.add_argument('--packed', action='store_true', help='Project vocabulary logits only for already active labels')
    parser.add_argument('--expandable-segments', action='store_true', help='Set allocator config in child processes before importing torch')
    args = parser.parse_args()
    if args.inventory:
        inventory(ROOT / f'reports/training/{args.report_id}_environment.json')
        return 0
    if args.probe:
        return probe(args)
    return sweep(args)


if __name__ == '__main__':
    raise SystemExit(main())
