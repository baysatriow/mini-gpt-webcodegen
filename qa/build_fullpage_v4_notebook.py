"""Build and execute a notebook reviewing the frozen v4 training artifacts."""
from pathlib import Path

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks/14_fullpage_v4_process_role_training.ipynb"


def main():
    if OUTPUT.exists():
        raise FileExistsError("Preserve an existing v4 notebook")

    specs = KernelSpecManager().get_all_specs()
    kernel_name = "mini-gpt-webcodegen" if "mini-gpt-webcodegen" in specs else "python3"
    display_name = specs[kernel_name]["spec"]["display_name"] if kernel_name in specs else "Python 3"
    notebook = nbformat.v4.new_notebook()
    notebook.metadata.kernelspec = {"display_name": display_name, "language": "python", "name": kernel_name}
    notebook.metadata.language_info = {"name": "python"}
    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            "# Fullpage v4: training dengan tambahan target process\n\n"
            "Notebook ini membaca data train v3 dan v4, profil GPU, metrik training, dan laporan generation development. "
            "Sel-selnya tidak mengulang training atau evaluasi dan tidak membuka benchmark final.\n\n"
            "Contoh train bersifat sintetis dan belum ditinjau manusia. Target eksperimen adalah sedikitnya 76 dari 80 halaman valid."
        ),
        nbformat.v4.new_markdown_cell(
            "## Alur eksperimen\n\n"
            "1. Menyalin v3 sebagai dasar v4 dan menambahkan 960 target section role process hanya dari keluarga train.\n"
            "2. Mempertahankan file validation dan test serta prompt, renderer, validator, sampler, dan budget output.\n"
            "3. Membekukan konfigurasi 2048 token, probabilitas batch plan 0.7, microbatch 8, akumulasi 6, dan output section 1536 token.\n"
            "4. Melatih dari INIT-2048-001 sampai update 1.800 sebagai TRAIN-022. Resume persis sampai update 3.600 sebagai TRAIN-024.\n"
            "5. Membandingkan dua snapshot pada 80 permintaan development yang sama. TRAIN-023 berhenti pada preflight penyimpanan di update 0 dan tidak memperbarui bobot."
        ),
        nbformat.v4.new_code_cell(
            "import json\n"
            "from collections import Counter\n"
            "from pathlib import Path\n"
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n\n"
            "ROOT = Path.cwd()\n"
            "def read_json(path):\n"
            "    return json.loads(Path(path).read_text(encoding='utf-8'))\n\n"
            "selection = read_json(ROOT / 'reports/training/FULLPAGE-V4_DEVELOPMENT_SELECTION.json')\n"
            "print('Project root:', ROOT)\n"
            "print('Final benchmark opened:', selection['final_opened'])\n"
            "print('Development requests:', selection['development_total'])"
        ),
        nbformat.v4.new_markdown_cell("## Perubahan dan validasi dataset"),
        nbformat.v4.new_code_cell(
            "v3_manifest = read_json(ROOT / 'data/processed/fullpage/v3/manifest.json')\n"
            "v4_manifest = read_json(ROOT / 'data/processed/fullpage/v4/manifest.json')\n"
            "change = selection['data_change']\n"
            "heldout = ('validation.jsonl', 'validation.requests.jsonl', 'test.jsonl', 'test.requests.jsonl')\n"
            "heldout_unchanged = {name: v3_manifest['files'][name]['sha256'] == v4_manifest['files'][name]['sha256'] for name in heldout}\n"
            "assert all(heldout_unchanged.values())\n"
            "display(pd.DataFrame([\n"
            "    {'item': 'baris train v3', 'nilai': change['train_rows_v3']},\n"
            "    {'item': 'baris train v4', 'nilai': change['train_rows_v4']},\n"
            "    {'item': 'target train baru', 'nilai': change['added_rows']},\n"
            "    {'item': 'section process di v3', 'nilai': change['section_process_rows_v3']},\n"
            "    {'item': 'section process di v4', 'nilai': change['section_process_rows_v4']},\n"
            "    {'item': 'contoh ditinjau manusia', 'nilai': v4_manifest['human_reviewed']},\n"
            "    {'item': 'semua file heldout tidak berubah', 'nilai': all(heldout_unchanged.values())},\n"
            "]))"
        ),
        nbformat.v4.new_code_cell(
            "role_frame = pd.DataFrame({\n"
            "    'v3': change['section_role_rows_v3'],\n"
            "    'v4': change['section_role_rows_v4'],\n"
            "}).fillna(0).astype(int).sort_values('v4', ascending=False)\n"
            "display(role_frame)\n"
            "ax = role_frame.plot(kind='bar', figsize=(11, 4), title='Jumlah target train per section role')\n"
            "ax.set_ylabel('Baris target')\n"
            "ax.set_xlabel('Section role')\n"
            "plt.xticks(rotation=35, ha='right')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),
        nbformat.v4.new_markdown_cell(
            "## Profil dan konfigurasi GPU\n\n"
            "Sweep mengukur throughput, memori, dan stabilitas pada RTX 5070. Batch 16 menjadi yang tercepat, sekitar 2.6 persen di atas batch 8. "
            "Eksperimen tetap memakai batch 8 dan akumulasi 6 agar setting yang disepakati tidak berubah di tengah eksperimen."
        ),
        nbformat.v4.new_code_cell(
            "profile = read_json(ROOT / 'reports/training/FULLPAGE-GPU-005.json')\n"
            "profile_rows = [row for row in profile['results'] if row.get('status') == 'stable']\n"
            "profile_frame = pd.DataFrame([{\n"
            "    'batch': row['batch'], 'accumulation': row['accumulation'],\n"
            "    'tokens/sec': round(row['tokens_per_second']),\n"
            "    'VRAM peak GiB': round(row['peak_reserved_bytes'] / 2**30, 2),\n"
            "} for row in profile_rows])\n"
            "display(profile_frame)\n"
            "ax = profile_frame.plot(x='batch', y='tokens/sec', kind='bar', legend=False, figsize=(8, 4), title='Throughput stabil pada RTX 5070')\n"
            "ax.set_ylabel('Token per detik')\n"
            "ax.set_xlabel('Microbatch')\n"
            "plt.tight_layout()\n"
            "plt.show()\n"
            "config = read_json(ROOT / 'configs/fullpage/training-improvement-v4.json')\n"
            "display(pd.DataFrame([{'parameter': key, 'value': config.get(key)} for key in ('batch_size', 'gradient_accumulation', 'max_steps', 'plan_batch_probability', 'warmup_steps', 'validation_interval', 'checkpoint_interval', 'precision', 'device')]))"
        ),
        nbformat.v4.new_markdown_cell("## Training dan validasi cross-entropy"),
        nbformat.v4.new_code_cell(
            "metric_rows = []\n"
            "for run_id in ('TRAIN-022', 'TRAIN-024'):\n"
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
            "axes[1].set_ylabel('Token per detik')\n"
            "for axis in axes: axis.legend()\n"
            "plt.tight_layout()\n"
            "plt.show()\n"
            "for run_id, rows in validation.groupby('run_id'):\n"
            "    plt.plot(rows['step'], rows['loss'], marker='o', label=run_id)\n"
            "plt.title('Cross-entropy validation')\n"
            "plt.xlabel('Update')\n"
            "plt.ylabel('Cross-entropy')\n"
            "plt.legend()\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),
        nbformat.v4.new_markdown_cell("## Hasil generation development"),
        nbformat.v4.new_code_cell(
            "rows = [{\n"
            "    'run': selection['historical_baseline']['run_id'],\n"
            "    'update': selection['historical_baseline']['step'],\n"
            "    'complete': selection['historical_baseline']['complete'],\n"
            "    'total': selection['historical_baseline']['total'],\n"
            "    'CE': selection['historical_baseline']['development_ce'],\n"
            "    'role': 'historical reference',\n"
            "}] + [{\n"
            "    'run': item['run_id'], 'update': item['step'],\n"
            "    'complete': item['development_complete'], 'total': item['development_total'],\n"
            "    'CE': item['development_ce'], 'role': 'v4 candidate',\n"
            "} for item in selection['candidates']]\n"
            "results = pd.DataFrame(rows)\n"
            "results['rate'] = results['complete'] / results['total']\n"
            "display(results)\n"
            "candidates = pd.DataFrame([{\n"
            "    'candidate': item['run_id'], 'step': item['step'],\n"
            "    'complete': item['development_complete'], 'failed': item['development_total'] - item['development_complete'],\n"
            "} for item in selection['candidates']])\n"
            "ax = candidates.set_index('candidate')[['complete', 'failed']].plot(kind='bar', stacked=True, figsize=(7, 4), title='Halaman valid dari 80 prompt')\n"
            "ax.axhline(selection['target']['minimum_complete_pages'], color='red', linestyle='--', label='Ambang 76')\n"
            "ax.set_ylabel('Jumlah halaman')\n"
            "plt.tight_layout()\n"
            "plt.show()\n"
            "print('Best observed:', selection['best_observed_by_complete_pages_then_ce'])\n"
            "print('Promotable:', selection['promotable_candidate'])\n"
            "print('Target met:', selection['model_gate_passed'])"
        ),
        nbformat.v4.new_markdown_cell("## Rincian kelompok prompt dan pola error"),
        nbformat.v4.new_code_cell(
            "group_rows = []\n"
            "for item in selection['candidates']:\n"
            "    for group, stats in item['groups'].items():\n"
            "        group_rows.append({'run': item['run_id'], 'group': group.replace('_', ' '), **stats})\n"
            "group_frame = pd.DataFrame(group_rows)\n"
            "display(group_frame)\n"
            "errors = []\n"
            "for item in selection['candidates']:\n"
            "    for error in item['top_generation_errors'][:6]:\n"
            "        errors.append({'run': item['run_id'], 'task': error['task'], 'stage': error['stage'], 'attempts': error['attempts'], 'pages': error['affected_pages'], 'error': error['error']})\n"
            "display(pd.DataFrame(errors))"
        ),
        nbformat.v4.new_markdown_cell(
            "## Kesimpulan dan batas hasil\n\n"
            "Update 3.600 mendapat hasil tertinggi pada dua kandidat v4, yaitu 68/80 atau 85 persen. Update 1.800 mendapat 64/80 atau 80 persen. "
            "Perbaikan empat halaman terlihat pada suite development yang sama, tetapi target 76/80 belum tercapai dan belum ada candidate yang lolos gate.\n\n"
            "Kegagalan yang tersisa mencakup ketidakcocokan identitas atau gaya pada rancangan, fakta merek pada bagian halaman, dan beberapa ketidakcocokan teks fakta. "
            "Pola ini menunjukkan pekerjaan lanjutan perlu menangani konsistensi perencanaan dan fakta. Perubahan data ini belum membuktikan sebab-akibat karena belum ada eksperimen terkontrol dengan beberapa seed.\n\n"
            "TRAIN-019 dengan 70/80 ditampilkan sebagai referensi historis, bukan sebagai kandidat v4. Data train sintetis belum ditinjau manusia. Tidak ada evaluasi visual di browser dan benchmark final tetap tertutup."
        ),
        nbformat.v4.new_markdown_cell(
            "## Bukti run\n\n"
            "Training utama: RUN-353 untuk update 1.800 dan RUN-367 untuk resume sampai 3.600. Evaluasi: RUN-355 dan RUN-369. Pemilihan: RUN-374. "
            "Preflight penyimpanan yang gagal sebelum weight update tercatat pada RUN-357. Pemulihan checkpoint dengan checksum dan tautan diperiksa pada RUN-361 dan RUN-365, lalu resume diverifikasi pada RUN-366. "
            "Semua eksekusi dan retry dicatat pada logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md dan logs/RUN-*.txt. Laporan pemilihan ada di reports/training/FULLPAGE-V4_DEVELOPMENT_SELECTION.json."
        ),
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    client = NotebookClient(
        notebook,
        timeout=300,
        kernel_name=kernel_name,
        resources={"metadata": {"path": str(ROOT)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbformat.write(executed, OUTPUT)
    print(f"Executed notebook: {OUTPUT.relative_to(ROOT).as_posix()}")
    print(f"Kernel: {kernel_name} ({display_name})")
    print(f"Cells: {len(executed.cells)}")


if __name__ == "__main__":
    main()
