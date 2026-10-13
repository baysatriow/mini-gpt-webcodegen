# Environment Mini GPT WebCodeGen

Environment proyek berada di `F:\Generative_AI\Vibe_Coding_Proyek_1\.venv`. Interpreter dasarnya adalah CPython 3.11.9 64-bit dari Python Launcher Windows.

Build GPU yang dipilih pada 12 Oktober 2026 adalah `torch==2.14.1+cu130`, yaitu release stabil terbaru yang tersedia di PyPI dan indeks resmi CUDA 13.0 pada saat pemeriksaan. PyTorch mencantumkan CUDA 13.0+ untuk GPU Blackwell dan minimum driver Windows 580.88. Driver komputer ini adalah 610.62.

CUDA runtime tersedia melalui wheel PyTorch. Menjalankan wheel ini tidak memerlukan pemasangan CUDA Toolkit tersendiri. Toolkit atau compiler tambahan baru perlu dipertimbangkan bila nanti proyek membangun extension CUDA dari source.

## Memakai environment

Jalankan dari folder proyek:

```powershell
Set-Location 'F:\Generative_AI\Vibe_Coding_Proyek_1'
.\.venv\Scripts\Activate.ps1
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Jika aktivasi dibatasi kebijakan PowerShell, interpreter tetap dapat dipakai langsung:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
```

Kernel notebook proyek menggunakan nama `mini-gpt-webcodegen` dan label `Mini GPT WebCodeGen (Python 3.11 CUDA)`. Pilih kernel tersebut ketika mengerjakan notebook. Interpreter Anaconda global masih berbeda dari environment proyek ini.

## Membangun kembali environment

`requirements-gpu.txt` mematok build GPU dari indeks resmi PyTorch. `requirements.txt` menyimpan versi paket pendukung yang dipilih. `configs/environment-lock.txt` merekam seluruh paket terpasang sebagai snapshot audit.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-gpu.txt
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
.\.venv\Scripts\python.exe -m ipykernel install --user --name mini-gpt-webcodegen --display-name 'Mini GPT WebCodeGen (Python 3.11 CUDA)'
.\.venv\Scripts\python.exe qa\check_gpu_environment.py
```

`requirements.in` menyimpan nama paket utama sebelum versi dikunci. Snapshot ini meliputi alat dataset, tokenizer, pencatatan grafik, notebook, dan validasi skema. Pemilihan framework aplikasi serta konfigurasi model dilakukan pada tahap desain berikutnya.

## Bukti kesiapan

`qa/check_gpu_environment.py` memeriksa interpreter proyek, GPU RTX 5070, perkalian matriks CUDA terhadap referensi CPU, causal attention dengan gradien, serta pembaruan parameter AdamW dengan mixed precision. Hasil disimpan di `outputs/metrics/environment_gpu_check.json`. Riwayat pemeriksaan dan instalasi dicatat dalam log RUN.

Pemeriksaan ini menguji operasi lingkungan pada tensor kecil. Ukuran model, throughput, batch maksimum, kualitas generasi, dan durasi training Mini GPT belum diukur.

Catatan sesudah setup: profiling dan baseline telah dijalankan pada TRAIN-001 sampai TRAIN-004. Lihat [hasil training](../reports/PIPELINE_TRAINING_SUMMARY.md) dan [notebook](../notebooks/README.md). nbformat 5.11.1 dan nbclient 0.11.0 ditambahkan pada RUN-069 untuk format/eksekusi notebook; PyTorch tidak diganti.

Environment, dataset mentah, output, dan checkpoint telah dicantumkan pada `.gitignore`.

## Sumber

- Paket stabil: https://pypi.org/project/torch/
- Indeks build CUDA: https://download.pytorch.org/whl/cu130/torch/
- Dukungan Blackwell dan driver: https://pytorch.org/blog/pytorch-2-12-release-blog/
