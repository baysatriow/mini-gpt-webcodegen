"""Record actual copy-training evidence, comprehensive logs, plots and notebook08."""
import argparse
import bisect
from datetime import datetime, timedelta, timezone
import json
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat as nbf

from src.data.curriculum import ROOT, verify_manifest
from src.data.sources import sha256_file, write_manifest
from src.training.engine import checkpoint_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    run = args.run_id
    read = lambda path: json.loads((ROOT / path).read_text(encoding='utf-8'))
    destination = ROOT / f'reports/training/{run}_copy_experiment.json'
    notebook_path = ROOT / 'notebooks/08_kualitas_penyalinan_dan_training.ipynb'
    report_path = ROOT / 'reports/COPYING_QUALITY_2026-10-13.md'
    heading = f'### {run}: Varied lexical copying actual record'
    if any(p.exists() for p in (destination, notebook_path, report_path)):
        raise ValueError('Preserve existing quality artifacts')
    training = read(f'reports/training/{run}.json')
    if training['status'] != 'completed' or training['global_step'] != training['config']['max_steps']:
        raise ValueError('Requires completed fixed budget')
    cfg, lineage = training['config'], training['config']['lineage']
    manifest = verify_manifest(ROOT / cfg['dataset_dir'])
    source = verify_manifest(ROOT / 'data/processed/curriculum/v5')
    if (manifest['parent_manifest_sha256'] != sha256_file(ROOT / 'data/processed/curriculum/v5/manifest.json')
            or any(manifest['files'][s][k]['sha256'] != source['files'][s][k]['sha256']
                   for s in ('validation', 'test') for k in ('rows', 'inputs', 'labels'))
            or manifest['final_suite']['sha256'] != source['final_suite']['sha256']):
        raise ValueError('Frozen heldout hashes changed')
    evaluations = {kind: read(f'reports/training/{run}{suffix}_curriculum_evaluation.json')
                   for kind, suffix in [('best', '-DEV'), ('last', '-LAST-DEV')]}
    for kind, evaluation in evaluations.items():
        expected = checkpoint_sha256(ROOT / f'checkpoints/{run}/{kind}.pt')
        if evaluation['split'] != 'validation' or evaluation['checkpoint_sha256'] != expected:
            raise ValueError('Development checkpoint mismatch')
    records = [json.loads(line) for line in (ROOT / f'outputs/metrics/{run}.jsonl').read_text().splitlines()]
    updates = [row for row in records if row['event'] == 'train'][5:]
    samples = [json.loads(line) for line in (ROOT / f'outputs/metrics/{run}_gpu.jsonl').read_text().splitlines()]
    ends = [row['time_unix'] for row in updates]
    active = []
    for sample in samples:
        index = bisect.bisect_left(ends, sample['time_unix'])
        if index < len(ends) and ends[index] - updates[index]['seconds'] <= sample['time_unix']:
            active.append(sample)
    telemetry = {key: {'mean': statistics.mean(s[key] for s in active) if active else None,
                       'max': max((s[key] for s in active), default=None)}
                 for key in ('utilization_pct', 'temperature_c', 'power_w', 'memory_used_mib')}
    augmentation = manifest['lexical_copy_augmentation']
    result = {'run_id': run, 'dataset_dir': cfg['dataset_dir'], 'counts': manifest['counts'],
        'added_train_rows': augmentation['added_rows'], 'attempted_rare_pieces': len(augmentation['attempted_piece_ids']),
        'pieces_with_targeted_rows': sum(r['added_targeted_rows'] > 0 for r in augmentation['rows_per_piece']),
        'skipped_title_variants': len(augmentation['skipped_variants']),
        'baseline_development': read('reports/training/TRAIN-014-DEV_curriculum_evaluation.json'),
        'development': evaluations, 'heldout_byte_hashes_preserved': True, 'final_evaluated': False,
        'selection_rule': cfg['selection_rule'], 'selected_step': training['best_checkpoint']['global_step'],
        'initial_validation': training['initial_validation'], 'final_validation': training['final_validation'],
        'best_validation_loss': training['best_validation_loss'], 'wall_seconds': training['wall_seconds'],
        'supervised_target_labels': training['total_train_tokens'],
        'measured_updates_excluding_first5': len(updates),
        'target_tokens_per_second': sum(r['valid_tokens'] for r in updates) / sum(r['seconds'] for r in updates),
        'active_sample_count': len(active), 'active_telemetry': telemetry,
        'peak_allocated_bytes': training['peak_allocated_bytes'], 'peak_reserved_bytes': training['peak_reserved_bytes'],
        'free_disk_bytes': training['free_bytes_after'], 'best_checkpoint_sha256': training['best_checkpoint_sha256'],
        'last_checkpoint_sha256': training['final_checkpoint_sha256'],
        'limits': ['Data are synthetic and share recipes across splits; title families are held out',
                   'Data, learning rate and update budget differ from TRAIN-014; no isolated causal attribution to augmentation',
                   'Development generation has been used for iteration and is not final proof',
                   'Many BPE pieces cannot be reproduced under the lowercase contextual brand generator; skipped variants disclosed',
                   'No JSON repair, target substitution, external pretrained weights or browser/production acceptance',
                   'Runtime remains TRAIN-012 until independent final evidence supports a new selection']}
    write_manifest(destination, result)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for event, label in [('train', 'Augmented train CE'), ('validation', 'Unchanged development CE')]:
        curve = [r for r in records if r['event'] == event]
        axes[0].plot([r['step'] for r in curve], [r['loss'] for r in curve], label=label, alpha=.75)
    axes[0].set(xlabel='Optimizer update', ylabel='Ordinary supervised token CE', yscale='log', title=run)
    axes[0].legend(); axes[0].grid(alpha=.2)
    baseline = result['baseline_development']
    labels = ['Baseline', 'Best CE', 'Last update']
    metrics = [baseline, evaluations['best'], evaluations['last']]
    axes[1].bar(labels, [e['exact_contract']/e['count']*100 for e in metrics], color=['#94a3b8', '#2563eb', '#0d9488'])
    axes[1].axhline(90, color='#ea580c', linestyle='--', label='Controlled contract threshold')
    axes[1].set(ylim=(0, 105), ylabel='Exact contracts (%)', title='Development generation only')
    axes[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(ROOT / f'reports/training/{run}_copy_training.png', dpi=160); plt.close(fig)
    best, last = evaluations['best'], evaluations['last']
    report = f'''# Kelanjutan kualitas penyalinan

AI-013, 13 Oktober 2026. Eksperimen {run} memakai model proyek14.186.496parameter dari bobot acak proyek, parent TRAIN-012 best. Tidak memakai pretrained LLM eksternal.

Dokumen dan notebook08 merekam fase development sebelum evaluasi final. Status terbaru sesudah fase berikutnya dicatat terpisah di README dan laporan gerbang final.

## Data dan diagnosis

TRAIN-013 last name16x menghasilkan23/24schema dan20/24exact pada development, dengan satu token_limit. Diagnosis baseline menemukan kesalahan nama pada empat contoh, dan satu potongan hanya memiliki dua exposure row train. Frekuensi ini dihitung pada train.

V6 menambah **{augmentation['added_rows']:,} row train**, total **{manifest['counts']['train']['rows']:,}**. Dari {len(augmentation['attempted_piece_ids']):,} potongan langka yang dicoba, {result['pieces_with_targeted_rows']:,} mendapat konteks targeted baru. Sebanyak {result['skipped_title_variants']:,} varian judul ditolak/dilewati karena batas generator, BPE membership atau nama. Tidak mengklaim seluruh vocabulary sudah terwakili dalam konteks baru. Semua data tambahan sintetis dengan human_reviewed=False.

Validation1.440/test1.440/final48 dipertahankan byte-identik terhadap v5. Final belum dievaluasi. Pemeriksaan hashes tidak membaca target final untuk tuning. Nama baru dicegah mengulang brand historis melalui hash membership pada semua prefix. [Manifest v6](data/SYNTHETIC_CURRICULUM_V6.json).

## Training dan hasil aktual

Budget tetap2.400update, batch48, BF16, ordinaryCE, LR5e-5ke5e-6, SDPA/fusedAdamW. [Probe v6](training/GPU-PERF-005.json) mengonfirmasi batch sebelum training; bobot probe dibuang. Waktu trainer {training['wall_seconds']:.2f}detik, {training['total_train_tokens']:,} label target termasuk pengulangan. Throughput setelah lima update awal {result['target_tokens_per_second']:,.0f}token target/detik. Peak allocated/reserved {training['peak_allocated_bytes']/2**30:.2f}/{training['peak_reserved_bytes']/2**30:.2f}GiB. Sisa storage {training['free_bytes_after']/2**30:.2f}GiB, reserve15GiB.

| Checkpoint | Step | Schema development | Exact development | Full validation CE |
| --- | --- | --- | --- | --- |
| Baseline TRAIN-012/14 best | 3.600/0 | {baseline['schema_valid']}/24 | {baseline['exact_contract']}/24 | {baseline['token_metrics']['loss']:.8f} |
| {run} best | {best['checkpoint_step']} | {best['schema_valid']}/24 | {best['exact_contract']}/24 | {best['token_metrics']['loss']:.8f} |
| {run} last | {last['checkpoint_step']} | {last['schema_valid']}/24 | {last['exact_contract']}/24 | {last['token_metrics']['loss']:.8f} |

Best dipilih berdasarkan full validation ordinaryCE sesuai aturan sebelum training. Pengukuran best/last generation merupakan diagnosis development. Final tetap tertutup; tidak memilih checkpoint dengan mencoba final berulang. Backend training SDPA dan evaluator manual dapat menghasilkan beda numerik kecil.

Data, learning rate dan budget berbeda dari TRAIN-014. Ini eksperimen kelanjutan yang telah ditetapkan, bukan ablation dengan budget identik. Peningkatan tidak dapat diatribusikan seluruhnya pada data tambahan.

## Batas dan langkah berikutnya

Runtime website tetap TRAIN-012 dengan hasil final historis43/48exact. Hasil development di atas belum membuktikan arbitrary prompt, layout baru atau kualitas browser. UI aplikasi tetap tahap setelah kualitas. Langkah berikutnya menetapkan kandidat dan aturan final sebelum satu evaluasi holdout, atau memperbaiki model/data jika development belum memadai.

[Log training](../logs/LOG_TRAINING.md), [log interaksi](../logs/interaksi_llm/AI-013_2026-10-13.md), [notebook08](../notebooks/08_kualitas_penyalinan_dan_training.ipynb), [summary aktual](training/{run}_copy_experiment.json), [rencana](../docs/superpowers/plans/2026-10-13-copying-quality-continuation.md).

![Kurva dan generation development](training/{run}_copy_training.png)
'''
    report_path.write_text(report, encoding='utf-8')
    cells = []
    md = lambda text: cells.append(nbf.v4.new_markdown_cell(text))
    code = lambda text: cells.append(nbf.v4.new_code_cell(text))
    md(f'''# 08. Kualitas penyalinan dan training

AI-013, {run}, 13 Oktober2026. Notebook membaca hasil eksperimen nyata dan menampilkan tahap proses. Snapshot fase development sebelum evaluasi final, dengan status lanjut di README. Sel default tidak memulai training atau membuka final targets. Data sintetis berbeda dari12anotasi reviewed. Notebook01sampai07 tetap sebagai riwayat.''')
    code('''from pathlib import Path
import sys, json
import pandas as pd
from IPython.display import display, Image
ROOT = Path.cwd()
if ROOT.name == 'notebooks': ROOT = ROOT.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
read = lambda path: json.loads((ROOT/path).read_text(encoding='utf-8'))
print('Active project interpreter:',sys.executable)''')
    md('## 1. Diagnosis sebelum perubahan\n\nCompare raw development failures and train-only lexical exposure. The old name16x last checkpoint did not improve exact generation.')
    code('''diagnosis = read('reports/training/AI-013_COPY_DIAGNOSTIC.json')
rows = []
for checkpoint in diagnosis['development']:
    for failure in checkpoint['failures']:
        rows.append({'checkpoint_step':checkpoint['checkpoint_step'], 'recipe':failure['recipe'],
                     'name':failure['expected_name'], 'schema_valid':failure['schema_valid'],
                     'expected_first_piece':failure['expected_token'], 'actual_first_piece':failure['actual_token']})
display(pd.DataFrame(rows))
display(diagnosis['development'][0]['failures'][0]['name_piece_train_exposure'])''')
    md('Exposure sesudah penambahan data juga dihitung pada train. Target development yang sama digunakan hanya untuk diagnosis, tidak dimasukkan ke train.')
    code('''post_data = read('reports/training/AI-013_COPY_POST_DATA_DIAGNOSTIC.json')
before = pd.DataFrame(diagnosis['development'][0]['failures'][0]['name_piece_train_exposure'])
after = pd.DataFrame(post_data['development'][0]['failures'][0]['name_piece_train_exposure'])
display(before[['id','piece','train_rows']].merge(after[['id','train_rows']],on='id',suffixes=('_before','_after')))''')
    md('## 2. Data revision and rejected contexts\n\nOnly train data expanded. Validation/test/final are byte-identical. Counts and skipped variants are disclosed, not presented as complete vocabulary coverage.')
    code(f'''summary = read('reports/training/{run}_copy_experiment.json')
data = read('reports/data/SYNTHETIC_CURRICULUM_V6.json')
display(pd.DataFrame(data['counts']).T)
display({{k:summary[k] for k in ('added_train_rows','attempted_rare_pieces','pieces_with_targeted_rows','skipped_title_variants','heldout_byte_hashes_preserved','final_evaluated')}})
exposure = pd.DataFrame(data['lexical_copy_augmentation']['rows_per_piece'])
display(exposure.sort_values('after',ascending=False).head(10))
display(exposure.groupby('added_targeted_rows').size().rename('piece_count').to_frame())''')
    md('## 3. GPU probe before training\n\nProbe weights discarded. Dataset hash and VRAM headroom recorded. Nvidia-smi totals include desktop memory.')
    code("display(read('reports/training/GPU-PERF-005.json'))")
    md('## 4. Configuration, ancestry and actual training\n\nNew continuation starts a new optimizer and schedule; it is not an exact optimizer resume.')
    code(f'''training = read('reports/training/{run}.json')
display(training['config'])
display({{k:training[k] for k in ('status','global_step','wall_seconds','total_train_tokens','initial_validation','final_validation','best_checkpoint','best_checkpoint_sha256','final_checkpoint_sha256')}})''')
    md('## 5. Learning curve and development generation\n\nGeneration exactness and token CE measure different aspects. No repaired JSON or substituted ground truth.')
    code(f'''display(Image(filename=str(ROOT/'reports/training/{run}_copy_training.png')))
comparison = [('baseline',summary['baseline_development']), *summary['development'].items()]
display(pd.DataFrame([{{'checkpoint':name,'step':e['checkpoint_step'],'schema':e['schema_valid'],
    'exact':e['exact_contract'],'count':e['count'],'CE':e['token_metrics']['loss'],'EOS':e['all_ended_eos']}} for name,e in comparison]))''')
    md('## 6. Raw model output audit on development\n\nRead actual raw prediction records, with unchanged expected development contracts for comparison. No final examples read.')
    code('''best = summary['development']['best']
raw = read(best['outputs_path'])
display(pd.DataFrame([{'recipe':r['recipe'],'style':r['target_spec']['style_mode'],
    'expected_name':r['target_spec']['title'],'actual_name':(r['parsed_spec'] or {}).get('title'),
    'exact':r['exact_contract'],'stop':r['stop_reason']} for r in raw]))
print('One unchanged raw model output:')
print(raw[0]['raw_output'])''')
    md('## 7. Telemetry and readiness limits\n\nUpdate-only samples differ from all-phase telemetry. Development results are not final or browser proof. Runtime remains TRAIN-012 until separately supported by final evidence.')
    code('''display(summary['active_telemetry'])
display({k:summary[k] for k in ('target_tokens_per_second','active_sample_count','peak_allocated_bytes','peak_reserved_bytes','free_disk_bytes','final_evaluated')})
display(summary['limits'])''')
    md('''## Reproduce as separate logged runs

Run `qa.prepare_copy_curriculum` only for a new immutable destination. Training: `qa.train_configured_gpu --config configs/training_copy_contexts.json --initialize-from checkpoints/TRAIN-012/best.pt`. Evaluation: `qa.evaluate_curriculum --checkpoint checkpoints/TRAIN-NNN/best.pt --split validation --report-id NEW-ID`. Wrap every execution with `qa.run_logged`. Use a new report ID; old outputs are never overwritten. Final evaluation requires an independent predeclared decision.''')
    notebook = nbf.v4.new_notebook(cells=cells, metadata={'kernelspec': {'display_name':'Python (.venv - Mini GPT WebCodeGen)',
        'language':'python', 'name':'mini-gpt-webcodegen'}, 'language_info': {'name':'python','version':'3.11.9'}})
    nbf.validate(notebook); nbf.write(notebook, notebook_path)
    wib = lambda value: datetime.fromisoformat(value).astimezone(timezone(timedelta(hours=7))).isoformat()
    entry = f'''
{heading}

- AI-013 continuation sesuai persetujuan pengguna; status {training['status']}, committed step {training['last_committed_step']}. Mulai {wib(training['started_at_utc'])}, selesai {wib(training['ended_at_utc'])}, wall {training['wall_seconds']:.6f}detik. Tidak ada training exception/OOM/nonfinite tercatat.
- Environment {training['environment']}; model {training['parameter_count']}parameter, config {training['model_config']}. Bobot berasal dari proyek, original pretraining parent {lineage['pretraining_parent']}; curriculum parent {lineage['curriculum_parent']}.
- Dataset {cfg['dataset_dir']}, counts {manifest['counts']}; tambah {augmentation['added_rows']}train-only rows. {result['pieces_with_targeted_rows']}/{result['attempted_rare_pieces']}piece mendapat targeted contexts; {result['skipped_title_variants']}varian dilewati. Validation/test/final byte-identik v5, final belum dievaluasi. Origin {cfg['data_origin']}, human_reviewed {cfg['human_reviewed']}, bukan production reviewed.
- Batch {cfg['batch_size']} x accumulation {cfg['gradient_accumulation']}; budget {cfg['max_steps']}, seed {cfg['seed']}, warmup {cfg['warmup_steps']}, LR {cfg['learning_rate']} ke {cfg['min_learning_rate']}; betas {cfg['betas']}, decay {cfg['weight_decay']}, clip {cfg['grad_clip']}. Validation/checkpoint interval {cfg['validation_interval']}/{cfg['checkpoint_interval']}, batches {cfg['validation_batches']}, full {lineage['validation_blocks_or_examples']}rows.
- Objective ordinary CE dengan prompt/pad-100 dan JSON/EOS aktif, labels already shifted. Performance {cfg['performance']}, allocator {training['allocator_config']}. Probe GPU-PERF-005 selesai sebelum training, bobot probe dibuang. Continuation baru optimizer/schedule/cursor; resume parent {training['resume_parent']}, resume SHA {training['resume_parent_sha256']}.
- Initial validation {training['initial_validation']}; final {training['final_validation']}; best CE {training['best_validation_loss']}step{result['selected_step']}; final train loss {training['final_train_loss']}. {training['total_train_tokens']}target labels kumulatif termasuk pengulangan. Setelah lima update awal: {len(updates)}update, {result['target_tokens_per_second']:.3f}targettokens/sec.
- Development best {best['schema_valid']}/24schema, {best['exact_contract']}/24exact, CE{best['token_metrics']['loss']}; last {last['schema_valid']}/24schema, {last['exact_contract']}/24exact, CE{last['token_metrics']['loss']}. Semua raw/model/hash tersimpan. Final belum diuji; runtime tetap TRAIN-012. Tidak menyatakan arbitrary-prompt/browser/production readiness.
- Active telemetry {len(active)}samples, {telemetry}; all-phase telemetry {training['gpu_telemetry']}. Timestamp query dibanding interval update; bukan klaim utilisasi selalu100%. Peak allocated {training['peak_allocated_bytes']}bytes, reserved {training['peak_reserved_bytes']}bytes; nvidia-smi mencakup desktop. Free disk {training['free_bytes_after']}bytes, reserve {cfg['reserve_free_bytes']}bytes.
- Tokenizer SHA `{lineage['tokenizer_sha256']}`, synthetic manifest SHA `{lineage['synthetic_manifest_sha256']}`, pretrain fingerprint `{lineage['pretrain_fingerprint']['sha256']}`, data SHA {lineage['data_sha256']}, validationindices SHA `{lineage['validation_indices_sha256']}`.
- Initial checkpoint SHA `{cfg['initial_checkpoint_sha256']}`, sourceconfig SHA `{cfg['source_config_sha256']}`, expandedconfig SHA `{training['config_sha256']}`, best SHA `{training['best_checkpoint_sha256']}`, last SHA `{training['final_checkpoint_sha256']}`. Git HEAD saat training `{training['git_commit']}`; perubahan AI-013 dicommit setelah seluruh pengukuran.
- [Report training](../reports/training/{run}.json), [summary](../reports/training/{run}_copy_experiment.json), [hasil kualitas](../reports/COPYING_QUALITY_2026-10-13.md), [notebook08](../notebooks/08_kualitas_penyalinan_dan_training.ipynb). Raw lokal outputs/metrics/{run}.jsonl dan {run}_gpu.jsonl, checkpoints/{run}/, logs/training/{run}.log.
'''
    ledger = ROOT / 'logs/LOG_TRAINING.md'
    if heading in ledger.read_text(encoding='utf-8'): raise ValueError('Training record already exists')
    with ledger.open('a', encoding='utf-8') as handle: handle.write(entry)
    print(json.dumps({'run_id':run, 'summary':str(destination.relative_to(ROOT)), 'notebook':str(notebook_path.relative_to(ROOT)),
        'best_exact':best['exact_contract'], 'last_exact':last['exact_contract'], 'final_evaluated':False}))


if __name__ == '__main__': main()
