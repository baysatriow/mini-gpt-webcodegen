"""Create evidence, plots and a read-only notebook from completed GPU experiments."""
import argparse
import bisect
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat as nbf
import torch

from src.data.sources import write_manifest
from src.training.engine import read_checkpoint, checkpoint_sha256

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    run = args.run_id
    destination = ROOT / f'reports/training/{run}_gpu_performance.json'
    if destination.exists():
        raise ValueError('Summary already exists')
    read = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8'))
    r = read(f'reports/training/{run}.json')
    if r['status'] != 'completed':
        raise ValueError('Only completed training may be summarized')
    records = [json.loads(line) for line in (ROOT / f'outputs/metrics/{run}.jsonl').read_text().splitlines()]
    updates = [row for row in records if row['event'] == 'train']
    steady = updates[5:]
    samples = [json.loads(line) for line in (ROOT / f'outputs/metrics/{run}_gpu.jsonl').read_text().splitlines()]
    ends = [row['time_unix'] for row in steady]
    active = []
    for sample in samples:
        i = bisect.bisect_left(ends, sample['time_unix'])
        if i < len(ends) and ends[i] - steady[i]['seconds'] <= sample['time_unix']:
            active.append(sample)
    telemetry = {}
    for field in ('utilization_pct', 'memory_used_mib', 'power_w', 'temperature_c', 'sm_clock_mhz'):
        values = [s[field] for s in active]
        telemetry[field] = {'mean': statistics.mean(values) if values else None,
                            'max': max(values) if values else None,
                            'min': min(values) if values else None}
    baseline = read('reports/training/GPU-PERF-004.json')['cases'][0]
    train_seconds = sum(row['seconds'] for row in steady)
    target_tokens = sum(row['valid_tokens'] for row in steady)
    result = {'run_id': run, 'status': r['status'], 'warmup_updates_excluded': 5,
        'measured_training_updates': len(steady), 'training_step_seconds': train_seconds,
        'target_tokens_per_second': target_tokens / train_seconds,
        'speedup_vs_profile_baseline': target_tokens/train_seconds/baseline['target_tokens_per_second'],
        'seconds_per_update': train_seconds / len(steady),
        'trainer_wall_seconds': r['wall_seconds'],
        'total_train_tokens_including_warmup': r['total_train_tokens'],
        'peak_allocated_bytes': r['peak_allocated_bytes'], 'peak_reserved_bytes': r['peak_reserved_bytes'],
        'training_active_telemetry': {'sample_count': len(active), **telemetry},
        'all_phase_telemetry': r['gpu_telemetry'],
        'initial_validation': r['initial_validation'], 'final_validation': r['final_validation'],
        'best_validation_loss': r['best_validation_loss'], 'best_step': r['best_checkpoint']['global_step'],
        'curve': [{k: row[k] for k in ('event', 'step', 'loss')} for row in records if row['event'] in ('train','validation')],
        'limits': ['Performance baseline from isolated probe, not equal-weight-quality comparison',
                   'GPU percent sampled, not sustained 100 percent claim',
                   'Memory from nvidia-smi includes desktop; PyTorch allocated/reserved reported separately',
                   'Development improvement is not locked-final or general-prompt quality proof',
                   'No browser/production proof; final v5 stays closed']}
    parent = read_checkpoint(ROOT/'checkpoints/TRAIN-012/best.pt')
    selected = read_checkpoint(ROOT/f'checkpoints/{run}/best.pt')
    identical = parent['model'].keys()==selected['model'].keys() and all(torch.equal(parent['model'][k],selected['model'][k]) for k in parent['model'])
    diagnostic = {'parent':'TRAIN-012/best','candidate':f'{run}/best',
        'selected_step':selected['global_step'],'model_tensors_identical':identical,
        'parameter_tensors':len(parent['model']),
        'parent_sha256':checkpoint_sha256(ROOT/'checkpoints/TRAIN-012/best.pt'),
        'candidate_sha256':checkpoint_sha256(ROOT/f'checkpoints/{run}/best.pt'),
        'decision':'Keep historical runtime when selected model equals parent; no fresh final evaluation solely for a runtime change'}
    result['selection_diagnostic'] = diagnostic
    write_manifest(ROOT/f'reports/training/{run}_SELECTION_DIAGNOSTIC.json',diagnostic)
    write_manifest(destination, result)
    profiles = [read(f'reports/training/GPU-PERF-{i:03d}.json') for i in range(1,5)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    latest = profiles[-1]['cases']
    axes[0].bar([row['case'] for row in latest], [row.get('target_tokens_per_second',0)/1000 for row in latest], color=['#94a3b8']+['#2563eb']*(len(latest)-1))
    axes[0].set(ylabel='Supervised target tokens / second (thousands)', title='Actual train-only throughput probes')
    axes[0].tick_params(axis='x', rotation=35)
    axes[0].text(.02, .97, 'Batch64 excluded: less than1GiB free VRAM', transform=axes[0].transAxes, va='top', fontsize=8)
    for event,color in [('train','#2563eb'),('validation','#f97316')]:
        curve = [row for row in result['curve'] if row['event']==event]
        axes[1].plot([row['step'] for row in curve],[row['loss'] for row in curve],label=event,color=color,alpha=.7)
    axes[1].set(xlabel='Optimizer update',ylabel='Ordinary target-token CE',yscale='log',title=f'{run}: real training and development')
    axes[1].legend(); axes[1].grid(alpha=.2)
    fig.tight_layout()
    graph = ROOT / f'reports/training/{run}_gpu_training.png'
    fig.savefig(graph,dpi=160);plt.close(fig)
    cells=[]
    md=lambda text:cells.append(nbf.v4.new_markdown_cell(text))
    code=lambda text:cells.append(nbf.v4.new_code_cell(text))
    md(f'''# 07. Optimasi RTX 5070 dan training nyata

Sesi AI-012, 13 Oktober 2026. Notebook default membaca bukti aktual, tanpa training otomatis.
Alur: environment, empat sweep terpisah, operator CUDA aktual, pemilihan batch48, training800update, development, dan telemetry.
Skor throughput berbeda dari kualitas model. Finalv5 belum dibuka. Prompt/model lama dan log lama dipertahankan.''')
    code('''from pathlib import Path
import sys, json
import pandas as pd
from IPython.display import display, Image
ROOT = Path.cwd()
if ROOT.name == 'notebooks': ROOT = ROOT.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
def read(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))
print('Active interpreter:',sys.executable)
print('Recorded training environment:')
display(read('reports/training/GPU-PERF-001_environment.json'))''')
    md('## 1. Perbandingan nyata, termasuk kandidat yang ditolak\n\nBobot probe dibuang. Input train saja, enam warmup, 40/200/100/100 update terukur tiap case. Perubahan batch/backend menyebabkan trajectory berbeda. Memori total nvidia-smi mencakup desktop.')
    code('''profiles = [read(f'reports/training/GPU-PERF-{i:03d}.json') for i in range(1,5)]
rows=[]
for i,profile in enumerate(profiles,1):
    for row in profile['cases']:
        rows.append({'sweep':i,'case':row['case'],'status':row['status'],
            'target_tokens_s':row.get('target_tokens_per_second'),
            'allocated_GiB':row.get('peak_allocated_bytes',0)/2**30,
            'reserved_GiB':row.get('peak_reserved_bytes',0)/2**30,
            'free_GiB':row.get('free_vram_bytes',0)/2**30,
            'GPU_mean_pct':row.get('telemetry',{}).get('utilization_pct',{}).get('mean')})
display(pd.DataFrame(rows))
print('Selection:',profiles[-1]['selected']['case'])''')
    md('## 2. Backend dan pengaturan yang benar-benar digunakan\n\nSDPA auto dispatch memakai memory-efficient attention CUTLASS dalam operator profiling ini, bukan klaim FlashAttention. Optimizer fused tercatat. Expandable segments mengurangi reserved VRAM pada ukuran target yang bervariasi.')
    code('''operators=read('reports/training/GPU-PERF-001_attention_operators.json')
display(pd.DataFrame(operators['operators']))
config=read('configs/training_gpu_optimized.json')
display(config)''')
    md('## 3. Checkpoint, data, dan training\n\nModel14.186.496parameter tetap dari bobot acak proyek. Continuation memulai optimizer/schedule baru dari TRAIN-012best, bukan resume state optimizer. Target JSON/EOS aktif, prompt/padding masked. Tidak ada name16x pada run ini. Sintetis bukan anotasi reviewed produksi.')
    code(f'''run=read('reports/training/{run}.json')
performance=read('reports/training/{run}_gpu_performance.json')
display({{key:run.get(key) for key in ('status','global_step','wall_seconds','parameter_count','initial_validation','final_validation','best_validation_loss','best_checkpoint','performance','environment')}})
display(run['config']['lineage'])''')
    md('## 4. Telemetry pada update training\n\nRingkasan berikut memilih sampel yang waktunya berada di dalam interval update, setelah lima update awal. Checkpoint/validation/idle dipisahkan dari angka active training. Utilisasi maksimum100% tidak berarti setiap saat100%.')
    code('''display({key:value for key,value in performance.items() if key not in ('curve','all_phase_telemetry')})
print('All-phase telemetry includes validation, checkpoint and startup:')
display(performance['all_phase_telemetry'])''')
    md('## 5. Grafik throughput dan loss aktual\n\nTraining dan validation memakai ordinary CE pada corpus berbeda. Grafik tidak membuktikan ketepatan nama/prompt umum.')
    code(f'''display(Image(filename=str(ROOT/'reports/training/{run}_gpu_training.png')))''')
    md('## 6. Development generation dan batas kualitas\n\nEvaluator memakai checkpoint validation-selected, raw JSON tanpa repair, decodegreedy/EOS. Ini development yang sudah pernah dilihat, bukan locked final baru. Model runtime demonstrasi tetap checkpoint historis sampai bukti final baru tersedia.')
    code(f'''evaluation=read('reports/training/{run}-DEV_curriculum_evaluation.json')
display({{key:evaluation[key] for key in ('count','schema_valid','exact_contract','exact_field_matches','all_ended_eos','token_metrics','contract_gate_passed')}})
print('Finalv5 remains closed; development is not overall production acceptance.')''')
    md('## 7. Menjalankan eksperimen baru secara eksplisit\n\nRUN_TRAINING=False. True akan memakai GPU dan membuat RUN/TRAIN baru. Jangan jalankan bersamaan dengan training lain. Pertahankan reserve15GiB. Bila aplikasi GPU lain aktif, kurangi batch dan hitung ulang validation_batches agar validation tetap lengkap.')
    code('''RUN_TRAINING=False
if RUN_TRAINING:
    import subprocess
    subprocess.run([sys.executable,'-m','qa.run_logged','--label','notebook_gpu_optimized_training','--',
        sys.executable,'-m','qa.train_configured_gpu','--config','configs/training_gpu_optimized.json',
        '--initialize-from','checkpoints/TRAIN-012/best.pt'],cwd=ROOT,check=True)
else:
    print('Read-only mode; no training launched.')''')
    notebook=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Mini GPT WebCodeGen (Python 3.11 CUDA)','language':'python','name':'mini-gpt-webcodegen'},'language_info':{'name':'python','version':'3.11.9'}})
    nbf.validate(notebook)
    nbf.write(notebook,ROOT/'notebooks/07_optimasi_gpu_dan_training.ipynb')
    print(json.dumps({k:v for k,v in result.items() if k not in ('curve','all_phase_telemetry')},indent=2))


if __name__=='__main__':
    main()
