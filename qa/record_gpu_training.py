"""Append a complete actual GPU training record without rewriting history."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    run=args.run_id
    r=json.loads((ROOT/f'reports/training/{run}.json').read_text(encoding='utf-8'))
    p=json.loads((ROOT/f'reports/training/{run}_gpu_performance.json').read_text(encoding='utf-8'))
    if r['status']!='completed':raise ValueError('Training must have completed')
    c,l=r['config'],r['config']['lineage']
    heading=f'### {run}: GPU optimized training actual record'
    path=ROOT/'logs/LOG_TRAINING.md'
    if heading in path.read_text(encoding='utf-8'):raise ValueError('Record already exists')
    wib=lambda value:datetime.fromisoformat(value).astimezone(timezone(timedelta(hours=7))).isoformat()
    text=f'''
{heading}

- Permintaan pengguna AI-012: maksimalkan performa GPU untuk training. Batch dipilih dari empat sweep aktual, bukan asumsi VRAM besar. [Laporan GPU](../reports/GPU_TRAINING_OPTIMIZATION_2026-10-13.md).
- Status {r['status']}, step {r['global_step']}, last committed {r['last_committed_step']}; mulai {wib(r['started_at_utc'])}, selesai {wib(r['ended_at_utc'])}, wall {r['wall_seconds']:.6f}detik. Tidak ada exception/OOM/nonfinite pada run ini.
- Environment aktual {r['environment']}. Model {r['parameter_count']:,}parameter dengan config {r['model_config']}. Tidak ada pretrained LLM eksternal atau perubahan arsitektur.
- Data {c['dataset_dir']}, origin {c['data_origin']}, human_reviewed {c['human_reviewed']}; train {l['train_blocks_or_examples']}rows, fullvalidation {l['validation_blocks_or_examples']}rows. Train/validation sama dengan v4; finalv5 belum dibuka. Synthetic recipe sharing tetap menjadi keterbatasan.
- Batch {c['batch_size']} x accumulation {c['gradient_accumulation']}, seed {c['seed']}, BF16, budget {c['max_steps']}, warmup {c['warmup_steps']}, LR {c['learning_rate']}ke{c['min_learning_rate']}, AdamWbetas{c['betas']}, decay{c['weight_decay']}, clip{c['grad_clip']}. Validation/checkpoint tiap {c['validation_interval']}/{c['checkpoint_interval']}; validation_batches{c['validation_batches']}.
- Runtime performance {c['performance']}. Allocator process {r['allocator_config']}. SDPA actual profiler mencatat CUTLASS memory-efficient attention, bukan klaim FlashAttention. Tidak melakukan overclock/power-limit/driver changes. Model forward fullcontext tetap; lm_head/CE training hanya active labels, prompt/pad-100, JSON/EOSaktif, labels already shifted. Objective ordinary CE, tanpa name16x.
- Initial validation {r['initial_validation']}; final validation {r['final_validation']}; best loss {r['best_validation_loss']}step{r['best_checkpoint']['global_step']}, final train loss {r['final_train_loss']}. Validation backend SDPA; evaluator development defaultmanual terpisah. Beda numerik runtime dicatat.
- {r['total_train_tokens']:,} supervised target labels termasuk pengulangan. Setelah lima update awal dikeluarkan, {p['measured_training_updates']}update, {p['training_step_seconds']:.6f}detik update, throughput {p['target_tokens_per_second']:.3f}targettokens/sec, sekitar{p['speedup_vs_profile_baseline']:.4f}x baseline probe. Bukan equal-budget quality comparison atau wall speedup seluruh pipeline.
- Active-update telemetry {p['training_active_telemetry']}. Classification query timestamp terhadap intervalupdate; persentase sampling nvidia-smi bisa mencakup lag/window aktivitas. All-phase telemetry termasuk validation/checkpoint/startup ada pada report. Maximum100% tidak berarti selalu100%.
- Peak allocated {r['peak_allocated_bytes']:,}bytes/{r['peak_allocated_bytes']/2**30:.4f}GiB, reserved {r['peak_reserved_bytes']:,}/{r['peak_reserved_bytes']/2**30:.4f}GiB. Memori nvidia-smi termasuk desktop/proses lain dan tidak identik dengan allocated/reserved. Free disk {r['free_bytes_after']:,}bytes/{r['free_bytes_after']/2**30:.4f}GiB, reserve {c['reserve_free_bytes']:,}bytes.
- Initial parent SHA `{c['initial_checkpoint_sha256']}`, curriculum parent {l['curriculum_parent']}, original pretraining parent {l['pretraining_parent']}. Continuation memulai optimizer/schedule/cursor stage baru; bukan resume optimizer lama. Resume parent {r['resume_parent']}, SHA{r['resume_parent_sha256']}.
- Tokenizer SHA `{l['tokenizer_sha256']}`, pretrain fingerprint SHA `{l['pretrain_fingerprint']['sha256']}`, synthetic manifest SHA `{l['synthetic_manifest_sha256']}`, data SHA {l['data_sha256']}, validationindices SHA `{l['validation_indices_sha256']}`.
- Sourceconfig SHA `{c['source_config_sha256']}`, expandedconfig SHA `{r['config_sha256']}`, best SHA `{r['best_checkpoint_sha256']}`, last SHA `{r['final_checkpoint_sha256']}`. Git HEAD saat run `{r['git_commit']}`, perubahan runtime lokal AI-012 dicommit setelah pengukuran/eksekusi selesai.
- Selected model tensors identical to parent: {p['selection_diagnostic']['model_tensors_identical']}, jumlah {p['selection_diagnostic']['parameter_tensors']}. **Throughput meningkat, kualitas terpilih belum membaik**. Runtime contoh tetap TRAIN-012best, gate keseluruhan historis43/48gagal. Tidak memakai final baru untuk mencari kelulusan.
- Artifacts [training report](../reports/training/{run}.json), [performance](../reports/training/{run}_gpu_performance.json), [development](../reports/training/{run}-DEV_curriculum_evaluation.json), [notebook07](../notebooks/07_optimasi_gpu_dan_training.ipynb), local outputs/metrics/{run}.jsonl dan {run}_gpu.jsonl, logs/training/{run}.log, checkpoints/{run}/.
'''
    with path.open('a',encoding='utf-8') as handle:handle.write(text)
    print(json.dumps({'appended':run,'status':r['status'],'step':r['global_step']}))


if __name__=='__main__':main()
