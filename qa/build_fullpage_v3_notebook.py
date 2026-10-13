"""Build and execute a notebook that reviews the completed v3 experiment artifacts."""
from pathlib import Path

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'notebooks/13_fullpage_v3_targeted_training.ipynb'


def main():
    if OUTPUT.exists():
        raise FileExistsError('Preserve an existing v3 notebook')

    specs = KernelSpecManager().get_all_specs()
    kernel_name = 'mini-gpt-webcodegen' if 'mini-gpt-webcodegen' in specs else 'python3'
    display_name = specs[kernel_name]['spec']['display_name'] if kernel_name in specs else 'Python 3'
    notebook = nbformat.v4.new_notebook()
    notebook.metadata.kernelspec = {
        'display_name': display_name,
        'language': 'python',
        'name': kernel_name,
    }
    notebook.metadata.language_info = {'name': 'python'}
    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            '# Fullpage v3: eksperimen identity dan fakta\n\n'
            'Notebook ini merangkum artefak yang sudah dibuat. Sel-selnya membaca manifest train, '
            'profil GPU, log training, dan evaluasi development. Notebook tidak menjalankan ulang training, '
            'tidak membuka baris data final, dan tidak mengubah validator.\n\n'
            'Semua data curriculum pada eksperimen ini sintetis dan belum ditinjau manusia.'
        ),
        nbformat.v4.new_markdown_cell(
            '## Alur eksperimen\n\n'
            '1. Menambah contoh nama usaha sintetis hanya pada keluarga train.\n'
            '2. Menjaga manifest validation dan test tetap sama dengan v2.\n'
            '3. Mengukur batch GPU lalu membekukan konfigurasi training.\n'
            '4. Melatih TRAIN-020 sampai update 1.800, lalu resume persis sebagai TRAIN-021 sampai update 3.600.\n'
            '5. Mengevaluasi kedua snapshot pada 80 permintaan development dengan validator yang sama.'
        ),
        nbformat.v4.new_code_cell(
            "import json\n"
            "from pathlib import Path\n"
            "from collections import Counter\n"
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n\n"
            "ROOT = Path.cwd()\n"
            "def read_json(path):\n"
            "    return json.loads(Path(path).read_text(encoding='utf-8'))\n"
            "print('Project root:', ROOT)\n"
            "print('Final benchmark opened: no')"
        ),
        nbformat.v4.new_markdown_cell('## Dataset v3 dan partisi yang dipertahankan'),
        nbformat.v4.new_code_cell(
            "v2_manifest = read_json(ROOT / 'data/processed/fullpage/v2/manifest.json')\n"
            "v3_manifest = read_json(ROOT / 'data/processed/fullpage/v3/manifest.json')\n"
            "augmentation = v3_manifest['augmentation']\n"
            "heldout_names = ('validation.jsonl', 'validation.requests.jsonl', 'test.jsonl', 'test.requests.jsonl')\n"
            "heldout_unchanged = {name: v3_manifest['files'][name]['sha256'] == v2_manifest['files'][name]['sha256'] for name in heldout_names}\n"
            "assert all(heldout_unchanged.values())\n"
            "pd.DataFrame([\n"
            "    {'item': 'versi', 'nilai': v3_manifest['version']},\n"
            "    {'item': 'train families', 'nilai': augmentation['train_families']},\n"
            "    {'item': 'halaman sintetis baru', 'nilai': augmentation['train_pages_added']},\n"
            "    {'item': 'alias nama train', 'nilai': augmentation['new_name_aliases']},\n"
            "    {'item': 'task page_plan baru', 'nilai': augmentation['added_tasks']['page_plan']},\n"
            "    {'item': 'task section_content baru', 'nilai': augmentation['added_tasks']['section_content']},\n"
            "    {'item': 'jumlah task train', 'nilai': v3_manifest['task_counts']['train']},\n"
            "    {'item': 'panjang konteks maksimum', 'nilai': v3_manifest['max_total_tokens']},\n"
            "    {'item': 'data ditinjau manusia', 'nilai': augmentation['human_reviewed']},\n"
            "    {'item': 'file heldout sama dengan v2', 'nilai': all(heldout_unchanged.values())},\n"
            "])"
        ),
        nbformat.v4.new_markdown_cell(
            'Perbandingan heldout di atas memakai checksum yang tercatat pada manifest. Notebook tidak membaca isi file test maupun benchmark final.'
        ),
        nbformat.v4.new_markdown_cell('## Eksposur role section pada train'),
        nbformat.v4.new_code_cell(
            "def section_role_counts(path):\n"
            "    roles = Counter()\n"
            "    tasks = Counter()\n"
            "    with Path(path).open(encoding='utf-8') as handle:\n"
            "        for line in handle:\n"
            "            row = json.loads(line)\n"
            "            tasks[row['task']] += 1\n"
            "            if row['task'] == 'section_content':\n"
            "                roles[json.loads(row['target']).get('role')] += 1\n"
            "    return tasks, roles\n\n"
            "v2_tasks, v2_roles = section_role_counts(ROOT / 'data/processed/fullpage/v2/train.jsonl')\n"
            "v3_tasks, v3_roles = section_role_counts(ROOT / 'data/processed/fullpage/v3/train.jsonl')\n"
            "role_frame = pd.DataFrame({'v2': v2_roles, 'v3': v3_roles}).fillna(0).astype(int).sort_values('v3', ascending=False)\n"
            "display(role_frame)\n"
            "ax = role_frame.plot(kind='bar', figsize=(11, 4), title='Contoh train per role section')\n"
            "ax.set_ylabel('Baris target')\n"
            "ax.set_xlabel('Role')\n"
            "plt.xticks(rotation=35, ha='right')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),
        nbformat.v4.new_markdown_cell(
            'Data v3 menambah contoh untuk navigation, hero, services, faq atau portfolio, dan footer. Jumlah contoh process tetap 480, sama seperti v2. Ini selaras dengan error JSON pada role process yang muncul di kedua evaluasi, tetapi korelasi ini sendiri belum membuktikan sebab-akibat.'
        ),
        nbformat.v4.new_markdown_cell('## Profil GPU dan konfigurasi yang dibekukan'),
        nbformat.v4.new_code_cell(
            "profile = read_json(ROOT / 'reports/training/FULLPAGE-GPU-004.json')\n"
            "profile_rows = profile['results']\n"
            "display(pd.DataFrame([{\n"
            "    'batch': row['batch'], 'akumulasi': row['accumulation'],\n"
            "    'status': row['status'], 'token/detik': round(row.get('tokens_per_second', 0)),\n"
            "    'VRAM puncak GiB': round(row.get('peak_reserved_bytes', 0) / 2**30, 2),\n"
            "} for row in profile_rows]))\n"
            "config = read_json(ROOT / 'configs/fullpage/training-improvement-v3.json')\n"
            "pd.DataFrame([{'parameter': key, 'nilai': config[key]} for key in ('batch_size', 'gradient_accumulation', 'max_steps', 'plan_batch_probability', 'warmup_steps', 'validation_interval', 'checkpoint_interval')])"
        ),
        nbformat.v4.new_markdown_cell(
            'Catatan perbandingan rasio: konfigurasi TRAIN-019 yang menjadi baseline juga memakai plan_batch_probability 0.7. Jadi perubahan v3 terhadap baseline ada pada data augmentation dan komposisi role, bukan pada rasio sampler.'
        ),
        nbformat.v4.new_markdown_cell('## Kurva training dan cross-entropy development'),
        nbformat.v4.new_code_cell(
            "metric_rows = []\n"
            "for run_id in ('TRAIN-020', 'TRAIN-021'):\n"
            "    with (ROOT / f'outputs/metrics/{run_id}.jsonl').open(encoding='utf-8') as handle:\n"
            "        metric_rows.extend({'run_id': run_id, **json.loads(line)} for line in handle if line.strip())\n"
            "metrics = pd.DataFrame(metric_rows)\n"
            "train = metrics[metrics['event'] == 'train'].copy()\n"
            "validation = metrics[metrics['event'] == 'validation'].copy()\n"
            "display(validation[['run_id', 'step', 'loss', 'perplexity', 'valid_tokens']])\n"
            "fig, axes = plt.subplots(1, 2, figsize=(12, 4))\n"
            "for run_id, rows in train.groupby('run_id'):\n"
            "    axes[0].plot(rows['step'], rows['loss'], label=run_id, alpha=.8)\n"
            "    axes[1].plot(rows['step'], rows['tokens_per_second'], label=run_id, alpha=.8)\n"
            "axes[0].set_title('Loss train')\n"
            "axes[0].set_xlabel('Update')\n"
            "axes[0].set_ylabel('Loss')\n"
            "axes[1].set_title('Throughput per update')\n"
            "axes[1].set_xlabel('Update')\n"
            "axes[1].set_ylabel('Token/detik')\n"
            "for axis in axes: axis.legend()\n"
            "plt.tight_layout()\n"
            "plt.show()\n"
            "fig, axis = plt.subplots(figsize=(7, 4))\n"
            "for run_id, rows in validation.groupby('run_id'):\n"
            "    axis.plot(rows['step'], rows['loss'], marker='o', label=run_id)\n"
            "axis.set_title('Cross-entropy pada validation')\n"
            "axis.set_xlabel('Update')\n"
            "axis.set_ylabel('Cross-entropy')\n"
            "axis.legend()\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),
        nbformat.v4.new_markdown_cell('## Hasil evaluasi halaman development'),
        nbformat.v4.new_code_cell(
            "selection = read_json(ROOT / 'reports/training/AI-020_DEVELOPMENT_SELECTION.json')\n"
            "rows = [{\n"
            "    'run': selection['baseline']['run_id'], 'update': selection['baseline']['step'],\n"
            "    'valid': selection['baseline']['development_complete'], 'total': selection['baseline']['development_total'],\n"
            "    'CE': selection['baseline']['development_ce'], 'gate': 'baseline'\n"
            "}] + [{\n"
            "    'run': row['run_id'], 'update': row['step'], 'valid': row['development_complete'],\n"
            "    'total': row['development_total'], 'CE': row['development_ce'], 'gate': row['model_gate']\n"
            "} for row in selection['candidates']]\n"
            "display(pd.DataFrame(rows))\n"
            "print('Target:', selection['target']['minimum_complete_pages'], 'dari', selection['target']['pages'])\n"
            "print('Candidate yang lolos gate:', selection['promotable_candidate'])\n"
            "print('Final dibuka:', selection['final_opened'])"
        ),
        nbformat.v4.new_markdown_cell('## Error validator paling sering'),
        nbformat.v4.new_code_cell(
            "error_rows = []\n"
            "for candidate in selection['candidates']:\n"
            "    for item in candidate['top_generation_errors']:\n"
            "        error_rows.append({'run': candidate['run_id'], 'role': item['stage'], 'error': item['error'], 'attempts': item['attempts'], 'halaman terdampak': item['affected_pages']})\n"
            "display(pd.DataFrame(error_rows).sort_values(['run', 'attempts'], ascending=[True, False]).groupby('run').head(6))"
        ),
        nbformat.v4.new_markdown_cell(
            '## Kesimpulan\n\n'
            'Baseline TRAIN-019 menghasilkan 70/80 halaman development yang lengkap. Pada eksperimen v3, baik update 1.800 maupun 3.600 menghasilkan 0/80. Target 95 persen membutuhkan sedikitnya 76/80. Cross-entropy rendah tidak membuat hasil ini lolos karena rancangan atau bagian halaman tetap gagal pada validator.\n\n'
            'Kegagalan yang dominan ialah JSON rusak pada bagian process. Ada juga title usaha yang berubah saat dibuat ulang, misalnya huruf atau suku kata hilang/bertambah. Validator tetap ketat. Tidak ada candidate yang dipromosikan. Evaluasi browser, review manusia, dan final benchmark tidak dilakukan.'
        ),
        nbformat.v4.new_markdown_cell(
            '## Bukti dan batas penggunaan\n\n'
            'RUN utama: RUN-295 persiapan data, RUN-297 profil GPU, RUN-300 dan RUN-308 training, RUN-302 dan RUN-310 evaluasi, RUN-320 pemilihan checkpoint. Detail setiap eksekusi ada di logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md dan logs/RUN-*.txt.\n\n'
            'Notebook ini adalah ringkasan hasil lokal. Ia tidak membuktikan kualitas visual browser, generalisasi ke data nyata, atau kelayakan produksi.'
        ),
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    client = NotebookClient(
        notebook,
        timeout=300,
        kernel_name=kernel_name,
        resources={'metadata': {'path': str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbformat.write(executed, OUTPUT)
    print(f'Executed notebook: {OUTPUT.relative_to(ROOT).as_posix()}')
    print(f'Kernel: {kernel_name} ({display_name})')
    print(f'Cells: {len(executed.cells)}')


if __name__ == '__main__':
    main()
