"""Check packages, register the project kernel, and capture the installed versions."""

import importlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("numpy", "datasets", "tokenizers", "tqdm", "matplotlib", "pandas", "ipykernel", "jsonschema", "safetensors")


def run(args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    print(result.stdout, end="", flush=True)
    print(result.stderr, end="", flush=True)
    if result.returncode:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {args}")
    return result.stdout


if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    raise RuntimeError("Use the project .venv interpreter")
run([sys.executable, "-m", "pip", "check"])
versions = {"torch": importlib.metadata.version("torch")}
for name in PACKAGES:
    importlib.import_module(name)
    versions[name] = importlib.metadata.version(name)
print("Core package imports passed.", flush=True)

from jupyter_core.paths import jupyter_data_dir

kernel_file = Path(jupyter_data_dir()) / "kernels" / "mini-gpt-webcodegen" / "kernel.json"
if kernel_file.exists():
    existing = json.loads(kernel_file.read_text(encoding="utf-8"))
    if Path(existing["argv"][0]).resolve() != Path(sys.executable).resolve():
        raise RuntimeError("The requested kernel name already belongs to another interpreter")
run([sys.executable, "-m", "ipykernel", "install", "--user", "--name", "mini-gpt-webcodegen", "--display-name", "Mini GPT WebCodeGen (Python 3.11 CUDA)"])
kernel = json.loads(kernel_file.read_text(encoding="utf-8"))
if Path(kernel["argv"][0]).resolve() != Path(sys.executable).resolve():
    raise RuntimeError("Registered kernel points to a different interpreter")
run([sys.executable, "-u", str(ROOT / "qa" / "check_gpu_environment.py")])
gpu = json.loads((ROOT / "outputs" / "metrics" / "environment_gpu_check.json").read_text(encoding="utf-8"))
if gpu["status"] != "passed" or any(value is None for value in gpu["packages"].values()):
    raise RuntimeError("GPU or package verification is incomplete")

freeze = run([sys.executable, "-m", "pip", "freeze"])
(ROOT / "configs" / "environment-lock.txt").write_text(freeze, encoding="utf-8")
(ROOT / "requirements.txt").write_text(
    "# Verified project tools, 2026-10-12. Install requirements-gpu.txt first.\n" + "\n".join(f"{name}=={versions[name]}" for name in PACKAGES) + "\n",
    encoding="utf-8",
)
manifest = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed",
    "interpreter": sys.executable,
    "python": sys.version,
    "packages": versions,
    "pip_check": "No broken requirements found",
    "imports": "passed",
    "kernel_file": str(kernel_file),
    "kernel_interpreter": kernel["argv"][0],
    "gpu_check": "outputs/metrics/environment_gpu_check.json",
    "disk_free_bytes": shutil.disk_usage(ROOT).free,
}
(ROOT / "outputs" / "metrics" / "environment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
rows = "\n".join(f"| {name} | {version} |" for name, version in versions.items())
status_text = f"""# Status Environment Proyek

Pemeriksaan akhir: {manifest['checked_at_utc']} UTC. Status: berhasil.

Interpreter: `{sys.executable}`.

Python: 3.11.9, 64-bit. GPU: {gpu['gpu']}, CUDA runtime {gpu['cuda_runtime']}, compute capability 12.0, driver 610.62. Build PyTorch memuat arsitektur sm_120. BF16 didukung.

| Paket utama | Versi |
| --- | --- |
{rows}

Pip check tidak menemukan kebutuhan paket yang rusak. Seluruh paket utama berhasil diimpor. Konversi Tensor dan NumPy berhasil. Perkalian matriks GPU cocok dengan referensi CPU. Causal attention BF16 beserta gradien dan pembaruan parameter AdamW menghasilkan nilai finite.

Kernel notebook: `Mini GPT WebCodeGen (Python 3.11 CUDA)`, nama `mini-gpt-webcodegen`. Interpreter kernel telah diperiksa dan menunjuk ke .venv proyek.

Ruang tersedia di drive proyek sesudah setup: {manifest['disk_free_bytes'] / 1024**3:.2f} GiB.

Bukti teknis: `outputs/metrics/environment_manifest.json`, `outputs/metrics/environment_gpu_check.json`, `configs/environment-lock.txt`, dan `logs/RUN-010_environment_finalize.txt`.

Langkah berikutnya memakai petunjuk pada `docs/PANDUAN_ENVIRONMENT.md`. Kegiatan ini merupakan pemeriksaan lingkungan dengan tensor kecil. Training Mini GPT, ukuran batch maksimum, durasi training, dan kualitas generasi belum diukur.
"""
(ROOT / "reports" / "STATUS_ENVIRONMENT_2026-10-12.md").write_text(status_text, encoding="utf-8")
print("Environment finalized with package, kernel, and CUDA evidence.", flush=True)
