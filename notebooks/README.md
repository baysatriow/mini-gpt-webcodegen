# Notebook Mini GPT WebCodeGen

Buka dengan VS Code/Jupyter dan pilih **Mini GPT WebCodeGen (Python 3.11 CUDA)**. Kernel mengarah ke `.venv` proyek.

## Urutan belajar

1. [Data dan tokenisasi](01_data_dan_tokenisasi.ipynb): source/lisensi, storage, sampel, normalisasi, family split, BPE, label next-token, dan draft SFT.
2. [Model dan training](02_model_dan_training.ipynb): arsitektur, forward kecil, mask SFT, konfigurasi, loss graph, stop/resume, checkpoint, dan smoke pilihan.
3. [Evaluasi dan hasil](03_evaluasi_dan_hasil.ipynb): held-out loss/perplexity, prompt/output asli, JSON/schema, keterbatasan, dan gerbang aplikasi.
4. [Kurasi dan SFT](04_kurasi_dan_sft.ipynb): coverage queue/pilot, prompt Indonesia, PageSpec draft, checklist manusia, checksum/provenance, mask target, dan penolakan draft oleh loader produksi.
5. [SFT pilot dan evaluasi](05_sft_pilot_dan_evaluasi.ipynb): approval 12 kandidat, preparation 4/4/4, coverage train, mask target, smoke/40 update pilot, loss graph dan hasil generasi held-out 0/4 valid.
6. [Pengembangan output PageSpec](06_pengembangan_output_pagespec.ipynb): diagnosis, curriculum v1-v5, raw output, objective nama, final43/48 yang gagal, dan dua contoh website yang diterima per output. Grafik TRAIN-013 memakai weighted train objective dan ordinary validation CE, bukan dua loss yang langsung dibandingkan.
7. [Optimasi GPU dan training](07_optimasi_gpu_dan_training.ipynb): empat sweep nyata, batch yang ditolak, backend CUDA aktual, TRAIN-014 dengan 800 update, throughput/VRAM/daya/suhu, dan development yang belum meningkat. Default membaca laporan; training opt-in melalui RUN logger.

Output tersimpan berasal dari eksekusi nyata. Run All default membaca artifact historis dan menjalankan contoh kecil di memori. `RUN_SMOKE=False`; mengubahnya menjadi True memulai smoke baru melalui pencatat RUN dan TRAIN ID baru.

Raw data, token cache, tokenizer, dan checkpoint tetap lokal. Setelah clone, sel menampilkan petunjuk bila artifact belum tersedia. Manifest, laporan ringkas, dan grafik tersedia di Git. Cuplikan source mempertahankan atribusi asal.

## Eksekusi notebook

Jalankan dari root proyek:

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label notebook_execution -- .\.venv\Scripts\python.exe qa/execute_notebooks.py
```

Hasil disimpan ke `outputs/notebooks/`. Tambahkan `--save-in-place` untuk memperbarui output notebook yang dilacak Git. Runner memeriksa format, syntax sel, dan interpreter kernel.

RUN-070 berhenti pada syntax sel teks notebook 03. Setelah koreksi, RUN-073 menjalankan ketiganya tanpa cell error. Rerun final tercatat pada log eksperimen. Tidak ada training produksi atau perubahan status draft dari notebook.

SFT pilot reviewed sudah dijalankan. Lihat [panduan training](../docs/TRAINING_GUIDE.md). Notebook01-05 menyimpan snapshot fase terdahulu; pengembangan terbaru ada pada06. Run All06 tidak training/generate GPU otomatis. Untuk percobaan sendiri, edit prompt dan flag RUN_GENERATION; mode development dan penolakan output dijelaskan di sel tersebut.

RUN-078 menjalankan versi final: 7 + 10 + 6 = 23 sel kode, tanpa cell error. RUN-079 memeriksa ulang format/syntax/link; RUN-080 suite pipeline 58/58 lulus.

RUN-085 menjalankan keempat notebook: 30 sel kode, tanpa cell error. Notebook 04 menyimpan output review pilot 12 kandidat; belum ada persetujuan manusia atau SFT baru. [Panduan review](../docs/ANNOTATION_REVIEW_GUIDE.md) menjelaskan langkah berikutnya.

AI-009 memperbarui notebook 04 ke pilot v2, menambahkan tabel sebelum/sesudah serta coverage kandidat tambahan. RUN-091 menjalankan empat notebook: 32 sel kode tanpa error. Output v1 terdahulu tersimpan di riwayat Git dan paket lokal v1 tetap tersedia. Semua anotasi masih draft.

AI-010 mencatat persetujuan pengguna pada seluruh 12 kandidat v2, kemudian menjalankan preparation, smoke TRAIN-005 dan pilot TRAIN-006. Notebook 05 membaca hasil aktual tanpa training ulang: validation loss 7,512 ke 3,739, test target loss 3,488, JSON/schema valid 0/4. Teks status draft di notebook sebelumnya adalah catatan historis.

RUN-099 menjalankan kelima notebook: 38 sel kode tanpa cell error. Output historis notebook 01 sampai 04 dipertahankan setelah rerun; notebook 05 menyimpan output aktual SFT pilot. Tidak ada training dari Run All default.

AI-011: RUN-146 enam notebook47sel, lalu RUN-150 versi final48sel (7+10+6+9+6+10) tanpa cell error. Notebook06 menyimpan output aktual, termasuk dua Cakrawala diterima, Senandika ditolak, maskloss16x dan beststep0 TRAIN-013 identik parent. Snapshot output01-05 dipertahankan setelah rerun. Model runtime tetap TRAIN-012 dengan final43/48exact yang belum lulus; contoh development tidak mengubah quality gate.
