"""Build the readable, non-executing source-bound full-page training notebook."""
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks/15_fullpage_v5_source_bound_facts.ipynb"


def _markdown(source):
    return nbformat.v4.new_markdown_cell(source.strip())


def _code(source):
    return nbformat.v4.new_code_cell(source.strip(), execution_count=None, outputs=[])


def build_notebook(output_path: Path) -> nbformat.NotebookNode:
    """Create and validate the notebook without executing its inspection or training cells."""
    cells = [
        _markdown("""
# Source-bound Full-page Experiment

Notebook untuk meninjau proses training Mini GPT yang menghasilkan rancangan halaman web melalui kontrak terstruktur. Model memilih susunan section dan referensi fakta. Renderer proyek menyusun halaman HTML, CSS, dan JavaScript yang sudah disediakan oleh aplikasi.

Notebook ini memperlihatkan data, konfigurasi, preflight GPU dan storage, training pada update 1.800, resume tepat sampai update 3.600, serta perbandingan development. Pembuatan notebook tidak menjalankan cell atau memulai training.
"""),
        _markdown("""
## Kontrak dan batas eksperimen

- Kontrak `source-bound-v1` memakai PagePlan dan SectionDraft berbasis ID referensi. Model tidak menulis copy, HTML, CSS, atau JavaScript.
- Dataset V5 diturunkan secara deterministik dari korpus sintetis proyek V4. Data belum ditinjau manusia dan tidak mewakili kesiapan untuk prompt bebas.
- Split keluarga tetap terpisah: 240 keluarga training dan 40 keluarga development. Development berisi 80 request dan 800 target task.
- Warm-start hanya dari bobot TRAIN-024 step 3.600. Optimizer dan scheduler baru dibuat dengan seed eksperimen ini.
- Eksperimen membandingkan checkpoint step 1.800 dan 3.600. Gerbang development memerlukan sedikitnya 76 dari 80 halaman lengkap, model gate lulus, serta referensi fakta, tautan, dan aset valid.
- Benchmark final tetap tertutup. Notebook hanya memeriksa manifest dan hash yang disediakan, tanpa membuka record final.
"""),
        _markdown("## 1. Ringkasan data, lineage, token, dan storage\n\nJalankan cell ini untuk membaca manifest train/development, ringkasan persiapan, konfigurasi beku, hash V4, dan preflight ruang. Hash bagian tertutup ditampilkan tanpa membaca recordnya."),
        _code(r"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = next((path for path in (Path.cwd(), *Path.cwd().parents)
             if (path / "configs/fullpage/training-improvement-v5.json").is_file()), None)
if ROOT is None:
    raise RuntimeError("Jalankan notebook dari folder proyek atau subfoldernya.")

def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

v4_manifest_path = ROOT / "data/processed/fullpage/v4/manifest.json"
v5_manifest_path = ROOT / "data/processed/fullpage/v5/manifest.json"
v5_report = read_json("reports/fullpage/FULLPAGE-V5_DATA_PREPARATION.json")
v5_manifest = read_json("data/processed/fullpage/v5/manifest.json")
training_config = read_json("configs/fullpage/training-improvement-v5.json")
free_bytes = shutil.disk_usage(ROOT).free
reserve_bytes = training_config["reserve_free_bytes"]
checkpoint_preflight_bytes = 834043904
inspection = {
    "v4_parent_manifest_sha256": sha256_file(v4_manifest_path),
    "v5_manifest_sha256": sha256_file(v5_manifest_path),
    "sealed_hashes_before_after_match": v5_manifest["sealed_sha256_before"] == v5_manifest["sealed_sha256_after"],
    "sealed_hash_values": list(v5_manifest["sealed_sha256_after"].values()),
    "family_counts": v5_manifest["family_counts"],
    "request_counts": v5_manifest["request_counts"],
    "task_counts": v5_manifest["task_counts"],
    "block_size": v5_manifest["block_size"],
    "output_budgets": v5_manifest["output_budgets"],
    "maximum_tokens": v5_manifest["maxima"],
    "data_preparation": {key: v5_report.get(key) for key in ("dataset_bytes", "disk_free_before_bytes", "disk_free_after_bytes", "sealed_hashes_unchanged")},
    "warm_start": {"path": training_config["initial_checkpoint"], "sha256": training_config["initial_checkpoint_sha256"]},
    "training": {key: training_config.get(key) for key in ("batch_size", "gradient_accumulation", "plan_batch_probability", "max_steps", "validation_interval", "checkpoint_interval")},
    "config_sha256": sha256_file(ROOT / "configs/fullpage/training-improvement-v5.json"),
    "storage": {"free_bytes": free_bytes, "reserve_bytes": reserve_bytes,
                "checkpoint_preflight_bytes": checkpoint_preflight_bytes,
                "gate_passed": free_bytes >= reserve_bytes + checkpoint_preflight_bytes},
    "human_reviewed": v5_manifest["human_reviewed"],
    "final_opened": v5_manifest["final_opened"],
}
inspection
"""),
        _markdown("## 2. Persiapan data dan konfigurasi\n\nKorpus V5 dan konfigurasi saat ini sudah dibuat serta hash-nya ditampilkan pada cell inspeksi. Cell berikut melewati tahap yang sudah tersedia. Jika dijalankan pada checkout baru, masing-masing tahap memakai CLI proyek dan mempertahankan aturan agar artefak yang sudah ada tidak ditimpa."),
        _code(r"""
import subprocess
import sys

prepared_manifest = ROOT / "data/processed/fullpage/v5/manifest.json"
if prepared_manifest.is_file():
    print("Dataset V5 sudah tersedia. Tahap persiapan dilewati agar data beku tidak ditimpa.")
else:
    subprocess.run([sys.executable, "-m", "qa.prepare_fullpage_v5"], cwd=ROOT, check=True)
"""),
        _code(r"""
config_path = ROOT / "configs/fullpage/training-improvement-v5.json"
if config_path.is_file():
    print("Konfigurasi V5 sudah tersedia dan beku:", sha256_file(config_path))
else:
    subprocess.run([sys.executable, "-m", "qa.configure_fullpage_v5_training"], cwd=ROOT, check=True)
"""),
        _markdown("## 3. Jalankan TRAIN-025 sampai update 1.800\n\nCell ini menggunakan bobot TRAIN-024 saja untuk inisialisasi dan membuat state optimizer baru. Jika folder run sudah ada, hentikan dan periksa log agar checkpoint lama tidak tertimpa."),
        _code(r"""
run_directory = ROOT / "checkpoints/TRAIN-025"
if run_directory.exists():
    raise RuntimeError("TRAIN-025 sudah memiliki artefak. Periksa checkpoint dan log sebelum melanjutkan.")
subprocess.run([
    sys.executable, "-u", "-m", "qa.train_fullpage",
    "--config", "configs/fullpage/training-improvement-v5.json",
    "--run-id", "TRAIN-025", "--stop-after", "1800",
], cwd=ROOT, check=True)
"""),
        _markdown("## 4. Snapshot dan evaluasi development pada update 1.800\n\nDua cell terpisah membuat snapshot bobot saja, lalu menghasilkan laporan pada 80 request development yang sama."),
        _code(r"""
subprocess.run([
    sys.executable, "-m", "qa.snapshot_fullpage_checkpoint",
    "--source", "checkpoints/TRAIN-025/last.pt",
    "--destination", "checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt",
    "--run-id", "TRAIN-025", "--step", "1800",
], cwd=ROOT, check=True)
"""),
        _code(r"""
subprocess.run([
    sys.executable, "-m", "qa.evaluate_fullpage",
    "--scope", "development",
    "--dataset-dir", "data/processed/fullpage/v4",
    "--checkpoint", "checkpoints/FULLPAGE-V5/TRAIN-025-step1800.pt",
    "--output", "outputs/fullpage/TRAIN-025-development-step1800",
    "--report", "reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json",
], cwd=ROOT, check=True)
"""),
        _markdown("## 5. Resume tepat TRAIN-026 sampai update 3.600\n\nResume mengambil optimizer, scheduler, sampler, dan RNG dari `TRAIN-025/last.pt`. Ini meneruskan state eksperimen, bukan inisialisasi ulang dari TRAIN-024."),
        _code(r"""
run_directory = ROOT / "checkpoints/TRAIN-026"
if run_directory.exists():
    raise RuntimeError("TRAIN-026 sudah memiliki artefak. Periksa checkpoint dan log sebelum melanjutkan.")
subprocess.run([
    sys.executable, "-u", "-m", "qa.train_fullpage",
    "--config", "configs/fullpage/training-improvement-v5.json",
    "--run-id", "TRAIN-026", "--resume", "checkpoints/TRAIN-025/last.pt",
], cwd=ROOT, check=True)
"""),
        _markdown("## 6. Snapshot dan evaluasi development pada update 3.600\n\nBuat snapshot terpisah dan evaluasi menggunakan request development yang sama dengan step 1.800."),
        _code(r"""
subprocess.run([
    sys.executable, "-m", "qa.snapshot_fullpage_checkpoint",
    "--source", "checkpoints/TRAIN-026/last.pt",
    "--destination", "checkpoints/FULLPAGE-V5/TRAIN-026-step3600.pt",
    "--run-id", "TRAIN-026", "--step", "3600",
], cwd=ROOT, check=True)
"""),
        _code(r"""
subprocess.run([
    sys.executable, "-m", "qa.evaluate_fullpage",
    "--scope", "development",
    "--dataset-dir", "data/processed/fullpage/v4",
    "--checkpoint", "checkpoints/FULLPAGE-V5/TRAIN-026-step3600.pt",
    "--output", "outputs/fullpage/TRAIN-026-development-step3600",
    "--report", "reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP3600.json",
], cwd=ROOT, check=True)
"""),
        _markdown("## 7. Pilih berdasarkan development saja\n\nPemilihan memprioritaskan jumlah halaman lengkap, memakai cross entropy development sebagai pemecah seri, lalu memilih step lebih awal jika nilai sama. Gerbang meminta 76/80 atau lebih dan validasi referensi yang ketat."),
        _code(r"""
subprocess.run([
    sys.executable, "-m", "qa.select_fullpage_v5",
    "--step1800-report", "reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json",
    "--step1800-training", "reports/training/TRAIN-025.json",
    "--step3600-report", "reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP3600.json",
    "--step3600-training", "reports/training/TRAIN-026.json",
    "--output", "reports/fullpage/FULLPAGE-V5_DEVELOPMENT_SELECTION.json",
], cwd=ROOT, check=True)
"""),
        _markdown("## 8. Hasil yang tersedia\n\nCell ini aman dijalankan sebelum atau sesudah training. Jika laporan belum tersedia, notebook menampilkan status menunggu. Ia hanya membaca dua laporan development, dua ringkasan training, dan laporan seleksi."),
        _code(r"""
from pprint import pprint

steps = {
    1800: ("reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP1800.json", "reports/training/TRAIN-025.json"),
    3600: ("reports/fullpage/FULLPAGE-V5_DEVELOPMENT_STEP3600.json", "reports/training/TRAIN-026.json"),
}
available = True
for step, paths in steps.items():
    if not all((ROOT / path).is_file() for path in paths):
        available = False
        print(f"Step {step}: laporan belum tersedia.")
        continue
    generation = read_json(paths[0])
    training = read_json(paths[1])
    print(f"Step {step}: {generation['complete']}/{generation['total']} halaman, "
          f"first attempt {generation['first_attempt_complete']}, "
          f"after retry {generation['after_retry_complete']}, "
          f"development CE {training['final_validation']['loss']:.6f}")
    pprint(generation["groups"])

selection_path = ROOT / "reports/fullpage/FULLPAGE-V5_DEVELOPMENT_SELECTION.json"
if selection_path.is_file():
    selection = read_json("reports/fullpage/FULLPAGE-V5_DEVELOPMENT_SELECTION.json")
    selected_step = str(selection["selected"]["step"])
    pprint({"model_gate_passed": selection["model_gate_passed"],
            "selected_step": selected_step,
            "selected_run": selection["selected"]["run_id"],
            "selected_checkpoint": selection["candidate_paths"][selected_step],
            "candidates": selection["candidates"], "final_used": False})
elif available:
    print("Laporan kedua tersedia, jalankan cell pemilihan.")
else:
    print("Hasil seleksi akan muncul setelah kedua eksperimen selesai.")
"""),
        _markdown("## Cara membaca hasil\n\n`complete` mengukur halaman yang lolos validator setelah retry. `first_attempt_complete` memperlihatkan keberhasilan percobaan pertama. `after_retry_complete` menunjukkan jumlah yang tetap valid setelah kebijakan retry. `development_ce` mengukur loss token pada split development dan hanya menjadi pemecah seri jika jumlah halaman lengkap sama.\n\nKelulusan gerbang ini adalah bukti development sintetis. Pemeriksaan visual di browser dan penilaian manusia tetap merupakan tahap terpisah."),
    ]
    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Mini GPT WebCodeGen (Python 3.11 CUDA)",
                           "language": "python", "name": "mini-gpt-webcodegen"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )
    nbformat.validate(notebook)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, output_path)
    return notebook


def main():
    notebook = build_notebook(OUTPUT)
    print(f"Created {OUTPUT.relative_to(ROOT)} with {len(notebook.cells)} cells. Training and evaluation cells were not executed.")


if __name__ == "__main__":
    main()
