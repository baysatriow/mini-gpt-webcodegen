"""Build notebooks and a source-bound progress artifact from actual saved reports."""
import argparse
import json
from pathlib import Path
import nbformat
from src.fullpage.curriculum import write_json
from src.data.sources import sha256_file


def record_fullpage_progress(root,*,reports,output):
    root=Path(root).resolve(); existing={}
    for path in reports:
        path=Path(path)
        if path.is_file(): existing[path.relative_to(root).as_posix()]={'sha256':sha256_file(path),'report':json.loads(path.read_text(encoding='utf-8'))}
    candidates=[v['report'] for k,v in existing.items() if k.endswith('TRAIN-017_DEVELOPMENT_BEST.json')]
    selected=candidates[0] if candidates else None
    final=[v['report'] for k,v in existing.items() if k.endswith('FINAL.json')]
    status='model_gate_passed_review_pending' if selected and selected['model_gate'] else 'needs_more_model_work' if selected else 'training_in_progress'
    data={'status':status,'evidence':existing,'final_evaluated':bool(final),'human_review_status':'pending','browser_status':'pending','ui_implemented':False,
          'limits':['Synthetic four-sector curriculum, not arbitrary web instructions.','Shared component text and templates intentionally repeated.','Heldout target order is disclosed but request acceptance allows any valid required-role order.','No human ratings or browser acceptance are invented.']}
    write_json(output,data); return data


def create_notebooks(root):
    metadata={'kernelspec':{'display_name':'Python (.venv - Mini GPT WebCodeGen)','language':'python','name':'mini-gpt-webcodegen'}}
    setup="""from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
ROOT = Path.cwd().resolve()
while not (ROOT / '.venv').exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
assert (ROOT / 'src/fullpage').is_dir(), 'Open using the project kernel and folder'
def read(path): return json.loads((ROOT / path).read_text(encoding='utf-8'))
display(Markdown('Environment proyek: ' + str(ROOT)))"""
    nb10=nbformat.v4.new_notebook(metadata=metadata,cells=[
        nbformat.v4.new_markdown_cell('# 10. Curriculum, konteks2048 dan profil RTX5070\n\nHasil aktual dari artefak pipeline. Data sintetis belum menjadi review manusia. Notebook ini tidak membuka target final dan tidak menjalankan training otomatis.'),
        nbformat.v4.new_code_cell(setup),
        nbformat.v4.new_code_cell("manifest = read('data/processed/fullpage/v1/manifest.json')\ndisplay({k:manifest[k] for k in ('family_counts','task_counts','block_size','output_budgets','max_prefix','max_target_with_eos','max_total_tokens','human_reviewed')})"),
        nbformat.v4.new_markdown_cell('## Panjang train/development\n\nEOS tetap menjadi label. Prompt dan padding dimask. Nama/family berbeda antar split; komponen dan teks generik berulang secara sengaja.'),
        nbformat.v4.new_code_cell("from src.data.normalize import read_jsonl\nframes = []\nfor split in ('train','validation'):\n    rows = list(read_jsonl(ROOT / f'data/processed/fullpage/v1/{split}.jsonl'))\n    frames.append(pd.DataFrame(rows)[['task','length','genre','style_mode','retry']].assign(split=split))\nlengths = pd.concat(frames)\ndisplay(lengths.groupby(['split','task']).length.agg(['count','min','median','max']))\nfig, ax = plt.subplots(figsize=(9,4))\nfor task, group in lengths.groupby('task'):\n    ax.hist(group.length, bins=30, alpha=.6, label=task)\nax.axvline(1024, color='black', linestyle='--'); ax.set(xlabel='Sequence tokens', ylabel='Rows'); ax.legend(); plt.show()"),
        nbformat.v4.new_code_cell("display(read('reports/data/FULLPAGE_LOADER_V1.json'))\nrow = next(read_jsonl(ROOT / 'data/processed/fullpage/v1/train.jsonl'))\nprint('Task:',row['task']); print('Prompt preview:',row['prompt'][:260]); print('Compact plan target:',row['target'])"),
        nbformat.v4.new_markdown_cell('## Migrasi posisi\n\n1.024 posisi lama identik, tambahan1.024 diinisialisasi dengan seed42. Bobot lama dipertahankan. Diagnosis logits pendek bukan bukti posisi baru sudah belajar.'),
        nbformat.v4.new_code_cell("display(read('reports/training/INIT-2048-001.json'))\ndisplay(read('reports/training/INIT-2048-001_LOAD_INSPECTION.json'))"),
        nbformat.v4.new_code_cell("profile = read('reports/training/FULLPAGE-GPU-002.json')\nworst = read('reports/training/FULLPAGE-GPU-001.json')\ndisplay(pd.DataFrame([{k:r.get(k) for k in ('batch','accumulation','status','tokens_per_second','peak_allocated_bytes','free_device_bytes')} for r in profile['results']]))\nfig, ax = plt.subplots(figsize=(8,4))\nax.plot([r['batch'] for r in worst['results']], [r.get('tokens_per_second',0) for r in worst['results']], 'o-', label='Full context2048')\nax.plot([r['batch'] for r in profile['results']], [r.get('tokens_per_second',0) for r in profile['results']], 'o-', label='Representative trim')\nax.set(xlabel='Micro batch',ylabel='Supervised tokens/s'); ax.legend(); plt.show()\nprint('Selected:',profile['selected']['batch'],'accumulation:',profile['selected']['accumulation'])"),
        nbformat.v4.new_markdown_cell('## Fixture renderer\n\nEmpat fixture manual9 bagian tersedia di examples/generated/AI-018-manual. Ini contoh kontrak dan ekspor, bukan raw model output. CSS responsif sudah tersedia; penerimaan browser390/1440 tetap pending.'),
        nbformat.v4.new_code_cell("fixture = read('reports/fullpage/AI-018_RENDER_FIXTURES.json')\ndisplay({k:v for k,v in fixture.items() if k!='fixtures'})\nfor page in fixture['fixtures']: print(page['genre'],page['style'],page['label'])")])
    nb11=nbformat.v4.new_notebook(metadata=metadata,cells=[
        nbformat.v4.new_markdown_cell('# 11. Training dan generasi halaman utuh\n\nLoss teacher forcing, raw generation, review manusia dan pemeriksaan browser adalah bukti yang berbeda. Final hanya dibuka setelah kandidat terkunci; notebook pengembangan ini tidak membuka final.'),
        nbformat.v4.new_code_cell(setup),
        nbformat.v4.new_code_cell("display(read('configs/fullpage/training-v2.json'))\nfor run in ('TRAIN-016','TRAIN-017'):\n    summary = read(f'reports/training/{run}.json')\n    display({k:summary.get(k) for k in ('run_id','status','global_step','best_validation_loss','wall_seconds','total_train_tokens','peak_allocated_bytes','free_bytes_after')})"),
        nbformat.v4.new_markdown_cell('## Kurva dan throughput aktual\n\nTraining utama berdiri sendiri dari INIT2048, budget2.400. Best dipilih dengan ordinary CE penuh pada development. Best disimpan weights-only; exact resume memakai last.'),
        nbformat.v4.new_code_cell("fig, axes = plt.subplots(1,2,figsize=(12,4))\nfor run in ('TRAIN-016','TRAIN-017'):\n    metrics = pd.read_json(ROOT / f'outputs/metrics/{run}.jsonl',lines=True)\n    train = metrics[metrics.event=='train']; val = metrics[metrics.event=='validation']\n    axes[0].plot(val.step,val.loss,'o-',label=run+' validation')\n    axes[1].plot(train.step,train.tokens_per_second,label=run+' target tokens/s')\n    print(run, 'target tokens:',int(train.valid_tokens.sum()),'long-position labels:',int(train.supervised_tokens_after_position_1024.sum()),'mean target tokens/s:',int(train.valid_tokens.sum()/train.seconds.sum()))\naxes[0].set(xlabel='Update',ylabel='Ordinary CE',yscale='log'); axes[1].set(xlabel='Update',ylabel='Supervised tokens/s')\nfor ax in axes: ax.legend()\nplt.show()"),
        nbformat.v4.new_code_cell("for run in ('TRAIN-016','TRAIN-017'):\n    gpu = pd.read_json(ROOT / f'outputs/metrics/{run}_gpu.jsonl',lines=True)\n    display(gpu[['utilization_pct','memory_used_mib','power_w','temperature_c']].agg(['mean','max']))\n    task_report = ROOT / f'reports/training/{run}_TASK_LOSS.json'\n    if task_report.exists(): display(read(str(task_report.relative_to(ROOT))))"),
        nbformat.v4.new_markdown_cell('## Generation pilot dan development\n\nPlan512, section1536; output yang tidak valid gagal, tidak diperbaiki memakai target. Retry maksimum sekali. Halaman diterima hanya jika semua fakta dan komponen lolos.'),
        nbformat.v4.new_code_cell("for filename in ('TRAIN-016_PILOT.json','TRAIN-017_DEVELOPMENT_BEST.json','TRAIN-017_DEVELOPMENT_LAST.json'):\n    path = ROOT / 'reports/fullpage' / filename\n    if path.exists():\n        report = read(str(path.relative_to(ROOT)))\n        display({k:report.get(k) for k in ('scope','complete','total','first_attempt_complete','after_retry_complete','model_gate','groups','failures','page_seconds','browser_status','human_review_status')})"),
        nbformat.v4.new_code_cell("directory = ROOT / 'outputs/fullpage/TRAIN-017-development-best'\nif directory.exists():\n    paths = sorted(directory.glob('*/attempt-*/result.json'))\n    accepted = [p for p in paths if json.loads(p.read_text(encoding='utf-8'))['status']=='accepted']\n    selected = accepted[0] if accepted else paths[0]\n    result = json.loads(selected.read_text(encoding='utf-8'))\n    print('Raw model example:',result['request_id'],result['status'])\n    display(pd.DataFrame([{k:a.get(k) for k in ('stage','retry','stop_reason','generated_tokens','prefix_tokens','seconds','errors')} for a in result['attempts']]))\n    print('Raw plan:',result['attempts'][0].get('raw','')[:1800])\n    plan_path = selected.parent / 'plan.json'\n    if plan_path.exists(): display(json.loads(plan_path.read_text(encoding='utf-8')))\n    website = selected.parent / 'website/page_spec.json'\n    if website.exists(): display(json.loads(website.read_text(encoding='utf-8')))"),
        nbformat.v4.new_markdown_cell('## Status akhir dan opt-in training\n\nUI tetap tahap akhir. Jangan menyatakan model siap jika gate development belum95%, review manusia belum diisi, atau browser belum diperiksa. Sel di bawah tidak memulai training ketika notebook dibuka.'),
        nbformat.v4.new_code_cell("progress = ROOT / 'reports/fullpage/AI-018_PROGRESS.json'\nif progress.exists():\n    snapshot = read(str(progress.relative_to(ROOT)))\n    display({k:v for k,v in snapshot.items() if k!='evidence'})\nRUN_TRAINING = False\nif RUN_TRAINING:\n    raise RuntimeError('Create a new logged run ID or exact-resume from last; preserve previous artifacts. Use qa.run_logged and qa.train_fullpage.')\nprint('Training automatic execution:',RUN_TRAINING)")])
    for name,nb in [('10_fullpage_data_context_dan_gpu.ipynb',nb10),('11_fullpage_training_dan_generation.ipynb',nb11)]:
        nbformat.validate(nb); destination=root/'notebooks'/name
        if destination.exists(): raise ValueError('Notebook exists')
        nbformat.write(nb,destination)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--notebooks',action='store_true'); p.add_argument('--output',default='reports/fullpage/AI-018_PROGRESS.json')
    args=p.parse_args(); root=args.root.resolve()
    reports=list((root/'reports/fullpage').glob('*.json'))+list((root/'reports/training').glob('TRAIN-01[67]*.json'))
    output=root/args.output; reports=[r for r in reports if r.resolve()!=output.resolve()]
    result=record_fullpage_progress(root,reports=reports,output=output)
    if args.notebooks: create_notebooks(root)
    print(json.dumps({'status':result['status'],'report_count':len(result['evidence'])},indent=2))


if __name__=='__main__': main()
